"""Authenticated basket operations."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from .models.basket import Basket, basket_from_response

if TYPE_CHECKING:
    from .api import API

__all__ = ["BasketAccess", "resolve_basket_item_uid"]


async def resolve_basket_item_uid(
    api: API,
    product_uid: str,
    item_uid: str | None = None,
) -> str:
    """Resolve a basket line uid for updates and removals."""
    if item_uid is not None:
        return item_uid

    response = await api.send_request(
        endpoint="get_basket",
        params={
            "calculate": str(False).lower(),
            "slot_booked": "false",
        },
    )
    basket = basket_from_response(response)
    matches = [
        item.item_uid
        for item in basket.items
        if item.product_uid == product_uid and item.item_uid
    ]
    if not matches:
        msg = f"Product {product_uid} is not in the basket."
        raise ValueError(msg)
    if len(matches) > 1:
        msg = (
            f"Product {product_uid} appears on multiple basket lines; "
            "pass item_uid from `basket show`."
        )
        raise ValueError(msg)
    return matches[0]


class BasketAccess:
    """Fetch and manipulate the authenticated customer's grocery basket."""

    def __init__(self, api: API) -> None:
        self._api = api
        self._cached: Basket | None = None

    @property
    def cached(self) -> Basket | None:
        """Return the last fetched basket, if any."""
        return self._cached

    def _store(self, basket: Basket) -> Basket:
        self._cached = basket
        return basket

    async def fetch(self, *, calculate: bool = True) -> Basket:
        """Fetch the current basket."""
        response = await self._api.send_request(
            endpoint="get_basket",
            params={
                "calculate": str(calculate).lower(),
                "slot_booked": "false",
            },
        )
        return self._store(basket_from_response(response))

    async def add(
        self,
        product_uid: str,
        quantity: float = 1.0,
        *,
        uom: str = "ea",
        selected_catchweight: str | None = None,
    ) -> Basket:
        """Add a product to the basket (POST increment)."""
        if quantity <= 0:
            return await self.remove(product_uid)
        body: dict[str, Any] = {
            "product_uid": product_uid,
            "quantity": quantity,
            "uom": uom,
        }
        if selected_catchweight is not None:
            body["selected_catchweight"] = selected_catchweight
        response = await self._api.send_request(endpoint="add_basket_item", body=body)
        return self._store(basket_from_response(response))

    async def set_quantity(
        self,
        product_uid: str,
        quantity: float,
        *,
        item_uid: str | None = None,
        uom: str = "ea",
        selected_catchweight: str | None = None,
    ) -> Basket:
        """Set the absolute basket quantity for a product."""
        if quantity <= 0:
            return await self.remove(product_uid, item_uid=item_uid)
        resolved_item_uid = await resolve_basket_item_uid(
            self._api,
            product_uid,
            item_uid,
        )
        item: dict[str, Any] = {
            "product_uid": product_uid,
            "quantity": quantity,
            "uom": uom,
            "item_uid": resolved_item_uid,
        }
        if selected_catchweight is not None:
            item["selected_catchweight"] = selected_catchweight
        response = await self._api.send_request(
            endpoint="update_basket",
            body={"items": [item]},
        )
        return self._store(basket_from_response(response))

    async def remove(
        self,
        product_uid: str,
        *,
        item_uid: str | None = None,
        force_delete: bool = False,
    ) -> Basket:
        """Remove a product from the basket."""
        del force_delete  # DELETE /items is unreliable; updates always clear the line.
        resolved_item_uid = await resolve_basket_item_uid(
            self._api,
            product_uid,
            item_uid,
        )
        response = await self._api.send_request(
            endpoint="update_basket",
            body={
                "items": [
                    {
                        "product_uid": product_uid,
                        "quantity": 0,
                        "uom": "ea",
                        "item_uid": resolved_item_uid,
                    }
                ]
            },
        )
        return self._store(basket_from_response(response))

    async def clear(self) -> None:
        """Remove all items from the basket."""
        await self._api.send_request(endpoint="clear_basket")
        self._cached = None
