"""Grocery basket models."""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass, field
from typing import Any

from ..common.price import Price


def basket_from_response(response: dict[str, Any] | list[Any] | None) -> Basket:
    """Parse a basket API response into a :class:`Basket`."""
    if not isinstance(response, dict):
        msg = "Basket response was not a JSON object."
        raise TypeError(msg)
    return Basket.from_dict(response)


@dataclass(slots=True)
class BasketItem:
    """
    A single line item in the grocery basket.

    Attributes:
        product_uid: Catalogue identifier for the product.
        quantity: Number of units in the basket.
        name: Display name when returned by the basket endpoint.
        item_uid: Basket line identifier used for updates and removals.
        subtotal: Line total in pounds sterling.
        unit_price: Price per unit when provided by the API.
        product_data: Nested product JSON when included in the basket response.
            Use :meth:`~pysainsburys.models.product.Product.from_basket_nested`
            to parse this into a :class:`~pysainsburys.models.product.Product`.

    """

    product_uid: str
    quantity: float
    name: str | None = None
    item_uid: str | None = None
    subtotal: float | None = None
    unit_price: Price | None = None
    product_data: dict[str, Any] | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> BasketItem:
        """Parse a basket item from grocery API JSON."""
        product_data = data.get("product")
        nested = product_data if isinstance(product_data, dict) else None
        product_uid = str(data.get("product_uid") or data.get("uid") or "")
        name = data.get("name")
        if nested is not None:
            if not product_uid:
                product_uid = str(nested.get("sku") or nested.get("product_uid") or "")
            if name is None:
                name = nested.get("name")
        return cls(
            product_uid=product_uid,
            quantity=float(data.get("quantity", 0)),
            name=name,
            item_uid=data.get("item_uid") or data.get("itemId"),
            subtotal=(
                float(data["subtotal"])
                if data.get("subtotal") is not None
                else (
                    float(data["subtotal_price"])
                    if data.get("subtotal_price") is not None
                    else None
                )
            ),
            unit_price=Price.from_dict(data.get("unit_price")),
            product_data=nested,
        )

    def to_dict(self) -> dict[str, Any]:
        """Serialise the basket item to a plain dictionary."""
        return {
            "product_uid": self.product_uid,
            "quantity": self.quantity,
            "name": self.name,
            "item_uid": self.item_uid,
            "subtotal": self.subtotal,
            "unit_price": self.unit_price.to_dict() if self.unit_price else None,
            "product": self.product_data,
        }


@dataclass(slots=True)
class Basket:
    """
    The authenticated customer's grocery basket.

    Attributes:
        basket_id: Basket identifier assigned by the commerce platform.
        order_id: Associated order id when amending an existing order.
        subtotal_price: Sum of item prices before delivery and savings.
        total_price: Basket total including fees where calculated.
        slot_price: Delivery or collection slot charge when applicable.
        savings: Promotional savings applied to the basket.
        nectar_savings: Nectar-specific savings when applicable.
        item_count: Number of distinct line items.
        minimum_spend: Minimum order value required for checkout.
        delivery_instructions: Customer delivery note when set.
        is_in_amend_mode: Whether the basket is amending a placed order.
        slot_type: Reserved slot type string from the API.
        has_exceeded_minimum_spend: Whether the minimum spend threshold is met.
        items: Line items currently in the basket.

    """

    basket_id: str | None = None
    order_id: str | None = None
    subtotal_price: float = 0.0
    total_price: float = 0.0
    slot_price: float = 0.0
    savings: float = 0.0
    nectar_savings: float = 0.0
    item_count: int = 0
    minimum_spend: int = 0
    delivery_instructions: str | None = None
    is_in_amend_mode: bool = False
    slot_type: str | None = None
    has_exceeded_minimum_spend: bool = False
    items: list[BasketItem] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Basket:
        """Parse a basket from grocery API JSON."""
        return cls(
            basket_id=data.get("basket_id"),
            order_id=data.get("order_id"),
            subtotal_price=float(data.get("subtotal_price", 0)),
            total_price=float(data.get("total_price", 0)),
            slot_price=float(data.get("slot_price", 0)),
            savings=float(data.get("savings", 0)),
            nectar_savings=float(data.get("nectar_savings", 0)),
            item_count=int(data.get("item_count", 0)),
            minimum_spend=int(data.get("minimum_spend", 0)),
            delivery_instructions=data.get("delivery_instructions"),
            is_in_amend_mode=bool(data.get("is_in_amend_mode", False)),
            slot_type=data.get("slot_type"),
            has_exceeded_minimum_spend=bool(
                data.get("has_exceeded_minimum_spend", False)
            ),
            items=[BasketItem.from_dict(item) for item in data.get("items", [])],
        )

    @property
    def is_empty(self) -> bool:
        """Return ``True`` when the basket contains no items."""
        return self.item_count == 0 and not self.items

    def to_dict(self) -> dict[str, Any]:
        """Serialise the basket to a plain dictionary."""
        return {
            "basket_id": self.basket_id,
            "order_id": self.order_id,
            "subtotal_price": self.subtotal_price,
            "total_price": self.total_price,
            "slot_price": self.slot_price,
            "savings": self.savings,
            "nectar_savings": self.nectar_savings,
            "item_count": self.item_count,
            "minimum_spend": self.minimum_spend,
            "delivery_instructions": self.delivery_instructions,
            "is_in_amend_mode": self.is_in_amend_mode,
            "slot_type": self.slot_type,
            "has_exceeded_minimum_spend": self.has_exceeded_minimum_spend,
            "items": [item.to_dict() for item in self.items],
        }

    def __iter__(self) -> Iterator[tuple[str, Any]]:
        """Allow ``dict(basket)`` conversion."""
        return iter(self.to_dict().items())
