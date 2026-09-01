"""Barcode lookup via Open Food Facts and product keyword search."""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

import aiohttp

from .const import OPEN_FOOD_FACTS_BASE_URL, OPEN_FOOD_FACTS_USER_AGENT
from .exceptions import BarcodeNotFoundError
from .models.product import Product, ProductList
from .models.store import StoreProduct, StoreProductList

_LOGGER = logging.getLogger(__name__)

SearchProductsFn = Callable[..., Awaitable[ProductList]]
SearchStoreProductsFn = Callable[..., Awaitable[StoreProductList]]


def normalize_ean(ean: str) -> str:
    """Return a barcode string with leading zeros stripped for comparison."""
    return ean.strip().lstrip("0")


def eans_match(left: str, right: str) -> bool:
    """Return whether two barcode strings refer to the same EAN."""
    return normalize_ean(left) == normalize_ean(right)


def product_matches_ean(product: Product, barcode: str) -> bool:
    """Return whether a product lists the given barcode in ``eans``."""
    return any(eans_match(ean, barcode) for ean in product.eans)


def filter_products_by_ean(products: list[Product], barcode: str) -> list[Product]:
    """Return products whose ``eans`` include the given barcode."""
    return [product for product in products if product_matches_ean(product, barcode)]


def pick_store_product_match(
    products: list[StoreProduct],
    *,
    off_product: OpenFoodFactsProduct | None,
) -> StoreProduct | None:
    """Return the best in-store product match for an Open Food Facts record."""
    if not products:
        return None
    if len(products) == 1:
        return products[0]
    if off_product and off_product.product_name:
        name_lower = off_product.product_name.lower()
        for product in products:
            product_name = product.name.lower()
            if product_name in name_lower or name_lower in product_name:
                return product
    return None


def build_search_query_from_open_food_facts(data: dict[str, Any]) -> str | None:
    """Build a Sainsbury's keyword query from an Open Food Facts product record."""
    brand = str(data.get("brands") or "").strip()
    name = str(data.get("product_name") or data.get("product_name_en") or "").strip()
    query = " ".join(part for part in (brand, name) if part).strip()
    return query or None


@dataclass(slots=True)
class OpenFoodFactsProduct:
    """Minimal product metadata from Open Food Facts."""

    barcode: str
    product_name: str | None
    brands: str | None

    @classmethod
    def from_dict(cls, barcode: str, data: dict[str, Any]) -> OpenFoodFactsProduct:
        """Parse Open Food Facts product JSON."""
        return cls(
            barcode=barcode,
            product_name=data.get("product_name") or data.get("product_name_en"),
            brands=data.get("brands"),
        )

    def search_query(self) -> str | None:
        """Return a keyword query suitable for Sainsbury's product search."""
        return build_search_query_from_open_food_facts(
            {
                "brands": self.brands,
                "product_name": self.product_name,
            }
        )


async def fetch_open_food_facts_product(
    session: aiohttp.ClientSession,
    barcode: str,
) -> OpenFoodFactsProduct | None:
    """Look up a barcode on Open Food Facts."""
    url = f"{OPEN_FOOD_FACTS_BASE_URL}/api/v2/product/{barcode}.json"
    headers = {
        "Accept": "application/json",
        "User-Agent": OPEN_FOOD_FACTS_USER_AGENT,
    }
    async with session.get(url, headers=headers) as response:
        if response.status == 404:
            return None
        if not response.ok:
            text = await response.text()
            _LOGGER.warning(
                "Open Food Facts lookup failed for %s: HTTP %s %s",
                barcode,
                response.status,
                text[:200],
            )
            return None
        payload = await response.json()
    if payload.get("status") != 1:
        return None
    product_data = payload.get("product")
    if not isinstance(product_data, dict):
        return None
    return OpenFoodFactsProduct.from_dict(barcode, product_data)


async def lookup_barcode(
    *,
    session: aiohttp.ClientSession,
    barcode: str,
    search_products: SearchProductsFn,
    page_size: int = 24,
) -> Product:
    """
    Resolve a barcode to a Sainsbury's product.

    Uses Open Food Facts for the product name, searches Sainsbury's by keyword,
    then filters results by matching ``eans``.
    """
    barcode = barcode.strip()
    off_product = await fetch_open_food_facts_product(session, barcode)
    search_query = off_product.search_query() if off_product else None
    if not search_query:
        raise BarcodeNotFoundError(
            barcode,
            message="Barcode not found on Open Food Facts",
        )

    results = await search_products(search_query, page_number=1, page_size=page_size)
    matches = filter_products_by_ean(results.products, barcode)
    if not matches:
        raise BarcodeNotFoundError(barcode, search_query=search_query)
    if len(matches) > 1:
        _LOGGER.debug(
            "Multiple EAN matches for %s; returning first of %d",
            barcode,
            len(matches),
        )
    return matches[0]


async def lookup_store_barcode(
    *,
    session: aiohttp.ClientSession,
    barcode: str,
    search_products: SearchStoreProductsFn,
    page_size: int = 24,
) -> StoreProduct:
    """
    Resolve a barcode to an in-store product for a specific store.

    Uses Open Food Facts for the product name, searches the store catalogue by
    keyword, then picks the best name match.
    """
    barcode = barcode.strip()
    off_product = await fetch_open_food_facts_product(session, barcode)
    search_query = off_product.search_query() if off_product else None
    if not search_query:
        raise BarcodeNotFoundError(
            barcode,
            message="Barcode not found on Open Food Facts",
        )

    results = await search_products(search_query, page=1, page_size=page_size)
    match = pick_store_product_match(results.products, off_product=off_product)
    if match is None:
        raise BarcodeNotFoundError(barcode, search_query=search_query)
    return match
