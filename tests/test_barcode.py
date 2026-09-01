"""Tests for barcode lookup helpers."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from pysainsburys.barcode import (
    OpenFoodFactsProduct,
    build_search_query_from_open_food_facts,
    eans_match,
    fetch_open_food_facts_product,
    filter_products_by_ean,
    lookup_barcode,
    normalize_ean,
    pick_store_product_match,
)
from pysainsburys.exceptions import BarcodeNotFoundError
from pysainsburys.models import PageControls, Product, ProductList
from pysainsburys.models.store import StoreProduct


def test_normalize_ean_strips_leading_zeros() -> None:
    """EAN comparison ignores leading zeros."""
    assert normalize_ean("08002270018213") == normalize_ean("8002270018213")


def test_eans_match() -> None:
    """Equivalent barcodes match after normalization."""
    assert eans_match("8002270018213", "08002270018213")


def test_build_search_query_from_open_food_facts() -> None:
    """Brand and product name combine into a keyword query."""
    query = build_search_query_from_open_food_facts(
        {
            "brands": "San Pellegrino",
            "product_name": "Sparkling Natural Mineral Water",
        }
    )
    assert query == "San Pellegrino Sparkling Natural Mineral Water"


def test_filter_products_by_ean() -> None:
    """Only products listing the barcode are returned."""
    products = [
        Product(product_uid="1", name="A", eans=["8002270018213"]),
        Product(product_uid="2", name="B", eans=["5010037009923"]),
    ]
    matches = filter_products_by_ean(products, "08002270018213")
    assert len(matches) == 1
    assert matches[0].product_uid == "1"


def test_pick_store_product_match_prefers_name() -> None:
    """In-store barcode matching prefers Open Food Facts product names."""
    off = OpenFoodFactsProduct(
        barcode="8002270018213",
        product_name="San Pellegrino Sparkling Natural Mineral Water 1L",
        brands="San Pellegrino",
    )
    products = [
        StoreProduct(product_code="1", name="Milk", stock="IN_STOCK"),
        StoreProduct(
            product_code="2",
            name="San Pellegrino Sparkling Natural Mineral Water 1L",
            stock="IN_STOCK",
        ),
    ]
    match = pick_store_product_match(products, off_product=off)
    assert match is not None
    assert match.product_code == "2"


def test_open_food_facts_product_search_query() -> None:
    """Open Food Facts records expose a search query."""
    off = OpenFoodFactsProduct(
        barcode="8002270018213",
        product_name="Natural mineral water",
        brands="San Pellegrino",
    )
    assert "San Pellegrino" in (off.search_query() or "")


@pytest.mark.asyncio
async def test_lookup_barcode_success() -> None:
    """Barcode lookup searches by OFF name and filters by EAN."""
    session = MagicMock()
    search_products = AsyncMock(
        return_value=ProductList(
            products=[
                Product(
                    product_uid="6731637",
                    name="San Pellegrino 1L",
                    eans=["8002270018213"],
                ),
                Product(product_uid="999", name="Other", eans=["111"]),
            ],
            controls=PageControls(
                total_record_count=2,
                returned_record_count=2,
                active_page=1,
                first_page=1,
                last_page=1,
                page_size=24,
            ),
        )
    )

    async def fake_off(
        _session: object,
        barcode: str,
    ) -> OpenFoodFactsProduct:
        return OpenFoodFactsProduct(
            barcode=barcode,
            product_name="Natural mineral water",
            brands="San Pellegrino",
        )

    import pysainsburys.barcode as barcode_module

    original = barcode_module.fetch_open_food_facts_product
    barcode_module.fetch_open_food_facts_product = fake_off
    try:
        product = await lookup_barcode(
            session=session,
            barcode="8002270018213",
            search_products=search_products,
        )
    finally:
        barcode_module.fetch_open_food_facts_product = original

    assert product.product_uid == "6731637"
    search_products.assert_awaited_once()


@pytest.mark.asyncio
async def test_lookup_barcode_not_on_off() -> None:
    """Missing Open Food Facts data raises BarcodeNotFoundError."""
    session = MagicMock()
    search_products = AsyncMock()

    async def fake_off(_session: object, _barcode: str) -> None:
        return None

    import pysainsburys.barcode as barcode_module

    original = barcode_module.fetch_open_food_facts_product
    barcode_module.fetch_open_food_facts_product = fake_off
    try:
        with pytest.raises(BarcodeNotFoundError, match="Open Food Facts"):
            await lookup_barcode(
                session=session,
                barcode="0000000000000",
                search_products=search_products,
            )
    finally:
        barcode_module.fetch_open_food_facts_product = original

    search_products.assert_not_awaited()


@pytest.mark.asyncio
async def test_lookup_barcode_no_sainsburys_match() -> None:
    """Search results without a matching EAN raise BarcodeNotFoundError."""
    session = MagicMock()
    search_products = AsyncMock(
        return_value=ProductList(
            products=[Product(product_uid="999", name="Other", eans=["111"])],
            controls=PageControls(
                total_record_count=1,
                returned_record_count=1,
                active_page=1,
                first_page=1,
                last_page=1,
                page_size=24,
            ),
        )
    )

    async def fake_off(_session: object, barcode: str) -> OpenFoodFactsProduct:
        return OpenFoodFactsProduct(
            barcode=barcode,
            product_name="Water",
            brands="Brand",
        )

    import pysainsburys.barcode as barcode_module

    original = barcode_module.fetch_open_food_facts_product
    barcode_module.fetch_open_food_facts_product = fake_off
    try:
        with pytest.raises(BarcodeNotFoundError, match="search query"):
            await lookup_barcode(
                session=session,
                barcode="8002270018213",
                search_products=search_products,
            )
    finally:
        barcode_module.fetch_open_food_facts_product = original


@pytest.mark.asyncio
async def test_fetch_open_food_facts_product_not_found() -> None:
    """Open Food Facts 404 responses return None."""
    response = AsyncMock()
    response.status = 404
    response.ok = False
    response.__aenter__ = AsyncMock(return_value=response)
    response.__aexit__ = AsyncMock(return_value=None)

    session = MagicMock()
    session.get = MagicMock(return_value=response)

    result = await fetch_open_food_facts_product(session, "0000000000000")
    assert result is None
