"""Customer favourites resource."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .models.product import Product, ProductList, bind_products

if TYPE_CHECKING:
    from .api import API


class Favourites:
    """Add, remove, and list favourite products for a customer."""

    def __init__(self, api: API) -> None:
        self._api = api
        self._cached: ProductList | None = None

    @property
    def cached(self) -> ProductList | None:
        """Return the last fetched favourites list, if any."""
        return self._cached

    async def fetch(
        self,
        *,
        page_number: int = 1,
        page_size: int = 20,
    ) -> ProductList:
        """Fetch a page of favourite products."""
        response = await self._api.send_request(
            endpoint="get_favourites",
            params={
                "page_number": page_number,
                "page_size": page_size,
            },
        )
        if not isinstance(response, dict):
            msg = "Favourites response was not a JSON object."
            raise TypeError(msg)
        favourites = ProductList.from_dict(response)
        bind_products(self._api, favourites.products)
        self._cached = favourites
        return favourites

    async def add(self, product: Product | str) -> None:
        """Add a product to favourites."""
        product_uid = product if isinstance(product, str) else product.product_uid
        await self._api.send_request(
            endpoint="add_favourite",
            body={"item": product_uid},
        )
        if isinstance(product, Product):
            product.is_favourite = True

    async def remove(
        self,
        product: Product | str,
        *,
        source_type: str = "",
    ) -> None:
        """Remove a product from favourites."""
        product_uid = product if isinstance(product, str) else product.product_uid
        await self._api.send_request(
            endpoint="remove_favourite",
            PRODUCT_SKU=product_uid,
            params={"sourceType": source_type},
        )
        if isinstance(product, Product):
            product.is_favourite = False
