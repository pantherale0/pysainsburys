"""
The core Sainsbury's GOL module.

This package provides the :class:`Sainsburys` client, authentication via
:class:`GOLAuth`, and re-exports of all public domain models from
:mod:`pysainsburys.models`.
"""

from __future__ import annotations

import logging
from collections.abc import Callable, Iterator
from typing import Any

from ._version import __version__
from .api import API
from .auth import GOLAuth
from .basket import BasketAccess
from .config import COMM_PROTOCOL, Config
from .enum import SlotType
from .exceptions import (
    BrowserLoginRequiredError,
    MFARequiredError,
    NotBoundError,
)
from .favourites import Favourites
from .models import (
    Basket,
    BasketItem,
    Customer,
    DeliverySlot,
    LocationContext,
    NutrientSummary,
    NutritionInfo,
    NutritionTable,
    NutritionTableRow,
    OrderList,
    OrderStatus,
    OrderSummary,
    Product,
    ProductList,
    SlotDay,
    SlotReservation,
    SlotWeek,
    Store,
    StoreList,
    StoreProduct,
    StoreProductList,
    bind_product,
    bind_products,
    bind_store,
    bind_stores,
)
from .nectar import Nectar
from .orders import OrderHandle, Orders
from .slots import Slots, build_list_slots_payload
from .utils import is_awaitable

__all__ = [
    "API",
    "COMM_PROTOCOL",
    "Basket",
    "BasketAccess",
    "BasketItem",
    "BrowserLoginRequiredError",
    "Config",
    "Customer",
    "DeliverySlot",
    "Favourites",
    "GOLAuth",
    "LocationContext",
    "MFARequiredError",
    "Nectar",
    "NotBoundError",
    "NutrientSummary",
    "NutritionInfo",
    "NutritionTable",
    "NutritionTableRow",
    "OrderHandle",
    "OrderList",
    "OrderStatus",
    "OrderSummary",
    "Orders",
    "PageControls",
    "Price",
    "Product",
    "ProductList",
    "Sainsburys",
    "SlotDay",
    "SlotReservation",
    "SlotType",
    "SlotWeek",
    "Slots",
    "Store",
    "StoreList",
    "StoreProduct",
    "StoreProductList",
    "__version__",
    "bind_product",
    "bind_products",
    "bind_store",
    "bind_stores",
    "build_list_slots_payload",
]

_LOGGER = logging.getLogger(__name__)


class Sainsburys:
    """
    Async client for Sainsbury's Groceries Online.

    Wrap an authenticated :class:`~pysainsburys.GOLAuth` session to access
    customer resources, or use the public catalogue methods without signing in.

    Example:
        Authenticated session::

            auth = await GOLAuth.from_session_file(
                "~/.config/pysainsburys/session.json"
            )
            async with Sainsburys(auth) as client:
                customer = await client.get_customer()
                basket = await customer.basket.fetch()

        Public catalogue lookup (no login required)::

            async with Sainsburys(GOLAuth()) as client:
                products = await client.search_products("bread")
                product = await client.get_product("3236048")

    """

    def __init__(self, authenticator: GOLAuth) -> None:
        """Initialize with an authenticated session."""
        self.api = API(authenticator)
        self.customer: Customer | None = None
        self.updated_data_callbacks: list[Callable[[], Any]] = []
        self._first_update = True

    async def close(self) -> None:
        """Close the underlying HTTP session."""
        await self.api.close()

    async def __aenter__(self) -> Sainsburys:
        """Enter async context manager."""
        return self

    async def __aexit__(self, *_args: object) -> None:
        """Close the client on context exit."""
        await self.close()

    async def get_customer(self) -> Customer:
        """Fetch and cache the authenticated customer profile."""
        response = await self.api.send_request(endpoint="customer_profile")
        if not isinstance(response, dict):
            msg = "Customer profile response was not a JSON object."
            raise TypeError(msg)
        self.customer = Customer.from_dict(response, api=self.api)
        return self.customer

    async def get_product(self, product_uid: str) -> Product:
        """Fetch a single product by uid (no login required)."""
        response = await self.api.send_public_request(
            endpoint="get_product",
            PRODUCT_UID=product_uid,
        )
        if not isinstance(response, dict):
            msg = "Product response was not a JSON object."
            raise TypeError(msg)
        product_data = response.get("product", response)
        if not isinstance(product_data, dict):
            msg = "Product payload was not a JSON object."
            raise TypeError(msg)
        return bind_product(self.api, Product.from_dict(product_data))

    async def search_products(
        self,
        keyword: str,
        *,
        page_number: int = 1,
        page_size: int = 24,
    ) -> ProductList:
        """Search products by keyword (no login required)."""
        response = await self.api.send_public_request(
            endpoint="search_products",
            params={
                "page_number": page_number,
                "page_size": page_size,
                "filter[keyword]": keyword,
            },
        )
        if not isinstance(response, dict):
            msg = "Product search response was not a JSON object."
            raise TypeError(msg)
        product_list = ProductList.from_dict(response)
        bind_products(self.api, product_list.products)
        return product_list

    async def find_stores(
        self,
        latitude: float,
        longitude: float,
        *,
        page: int = 1,
        page_size: int = 20,
    ) -> StoreList:
        """Find stores near a latitude and longitude (no login required)."""
        response = await self.api.send_product_finder_request(
            "/v3/stores",
            params={
                "lat": latitude,
                "lon": longitude,
                "page": page,
                "size": page_size,
            },
        )
        if not isinstance(response, dict):
            msg = "Store search response was not a JSON object."
            raise TypeError(msg)
        store_list = StoreList.from_dict(response, api=self.api)
        bind_stores(self.api, store_list.stores)
        return store_list

    async def get_store(self, store_id: str) -> Store:
        """Fetch a single store by Product Finder store id."""
        response = await self.api.send_product_finder_request(
            f"/v3/stores/{store_id}",
        )
        if not isinstance(response, dict):
            msg = "Store response was not a JSON object."
            raise TypeError(msg)
        return bind_store(self.api, Store.from_dict(response))

    async def find_stores_by_postcode(
        self,
        postcode: str,
        *,
        page_number: int = 1,
    ) -> StoreList:
        """Find stores near a UK postcode with click-and-collect availability."""
        response = await self.api.send_public_request(
            endpoint="click_and_collect",
            params={
                "postcode": postcode.replace(" ", "").upper(),
                "page_number": page_number,
            },
        )
        if not isinstance(response, dict):
            msg = "Store search response was not a JSON object."
            raise TypeError(msg)
        store_list = StoreList.from_dict(response, api=self.api)
        bind_stores(self.api, store_list.stores)
        return store_list

    async def update(self) -> None:
        """Refresh commonly used cached data."""
        if self._first_update:
            await self.get_customer()
            self._first_update = False
        if self.customer is not None:
            await self.customer.basket.fetch()
            await self.customer.favourites.fetch()
            order_list = await self.customer.orders.fetch()
            if order_list.orders:
                await self.customer.orders.latest.status()
        for callback in self.updated_data_callbacks:
            if is_awaitable(callback):
                await callback()
            else:
                callback()

    def register_callback(self, callback: Callable[[], Any]) -> None:
        """Register a callback to be called when data is updated."""
        if not callable(callback):
            raise TypeError("Callback must be callable")
        self.updated_data_callbacks.append(callback)

    def remove_callback(self, callback: Callable[[], Any]) -> None:
        """Remove a registered callback."""
        if callback in self.updated_data_callbacks:
            self.updated_data_callbacks.remove(callback)

    def to_dict(self) -> dict[str, Any]:
        """Return the Sainsburys object data as a dictionary."""
        basket = self.customer.basket.cached if self.customer is not None else None
        favourites = (
            self.customer.favourites.cached if self.customer is not None else None
        )
        orders = self.customer.orders.cached if self.customer is not None else None
        return {
            "api": self.api.to_dict(),
            "customer": self.customer.to_dict() if self.customer else None,
            "basket": basket.to_dict() if basket else None,
            "favourites": favourites.to_dict() if favourites else None,
            "orders": orders.to_dict() if orders else None,
        }

    def __iter__(self) -> Iterator[tuple[str, Any]]:
        """Allow ``dict(sainsburys)`` conversion."""
        return iter(self.to_dict().items())
