"""Order history and status models."""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass, field
from typing import Any

from ..common.pagination import PageControls


@dataclass(slots=True)
class OrderSummary:
    """
    Summary information for a past or active order.

    Attributes:
        order_id: Primary order identifier used in URLs and APIs.
        order_uid: Alternate order uid when returned separately.
        status: Human-readable order status string.
        total: Order total in pounds sterling.
        slot_start_time: Reserved slot start timestamp.
        slot_end_time: Reserved slot end timestamp.
        slot_type: Delivery or collection slot type.

    """

    order_id: str
    order_uid: str | None = None
    status: str | None = None
    total: float | None = None
    slot_start_time: str | None = None
    slot_end_time: str | None = None
    slot_type: str | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> OrderSummary:
        """Parse an order summary from grocery API JSON."""
        return cls(
            order_id=str(data.get("order_id") or data.get("order_uid") or ""),
            order_uid=data.get("order_uid"),
            status=data.get("status"),
            total=float(data["total"]) if data.get("total") is not None else None,
            slot_start_time=data.get("slot_start_time"),
            slot_end_time=data.get("slot_end_time"),
            slot_type=data.get("slot_type") or data.get("order_type"),
        )

    def to_dict(self) -> dict[str, Any]:
        """Serialise the order summary to a plain dictionary."""
        return {
            "order_id": self.order_id,
            "order_uid": self.order_uid,
            "status": self.status,
            "total": self.total,
            "slot_start_time": self.slot_start_time,
            "slot_end_time": self.slot_end_time,
            "slot_type": self.slot_type,
        }


@dataclass(slots=True)
class OrderList:
    """A paginated list of customer orders."""

    orders: list[OrderSummary]
    controls: PageControls

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> OrderList:
        """Parse an order list from grocery API JSON."""
        return cls(
            orders=[OrderSummary.from_dict(item) for item in data.get("orders", [])],
            controls=PageControls.from_dict(data.get("controls")),
        )

    def to_dict(self) -> dict[str, Any]:
        """Serialise the order list to a plain dictionary."""
        return {
            "orders": [order.to_dict() for order in self.orders],
            "controls": self.controls.to_dict(),
        }

    def __iter__(self) -> Iterator[tuple[str, Any]]:
        """Allow ``dict(order_list)`` conversion."""
        return iter(self.to_dict().items())


@dataclass(slots=True)
class OrderStatus:
    """
    Live status for the customer's active order slot.

    Attributes:
        order_uid: Identifier for the active order.
        is_cutoff: Whether the amend cutoff has passed.
        is_in_amend_mode: Whether the order can still be amended.
        cutoff_time: Amend cutoff timestamp when provided.
        slot_end_time: Reserved slot end timestamp.
        slot_start_time: Reserved slot start timestamp.
        order_type: Delivery or collection type string.
        total: Current order total in pounds sterling.
        failed_payments: Payment failure payloads from the API.

    """

    order_uid: str | None = None
    is_cutoff: bool = False
    is_in_amend_mode: bool = False
    cutoff_time: str | None = None
    slot_end_time: str | None = None
    slot_start_time: str | None = None
    order_type: str | None = None
    total: float = 0.0
    failed_payments: list[dict[str, Any]] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> OrderStatus:
        """Parse order status from grocery API JSON."""
        return cls(
            order_uid=data.get("order_uid"),
            is_cutoff=bool(data.get("is_cutoff", False)),
            is_in_amend_mode=bool(data.get("is_in_amend_mode", False)),
            cutoff_time=data.get("cutoff_time"),
            slot_end_time=data.get("slot_end_time"),
            slot_start_time=data.get("slot_start_time"),
            order_type=data.get("order_type"),
            total=float(data.get("total", 0)),
            failed_payments=list(data.get("failed_payments", [])),
        )

    def to_dict(self) -> dict[str, Any]:
        """Serialise order status to a plain dictionary."""
        return {
            "order_uid": self.order_uid,
            "is_cutoff": self.is_cutoff,
            "is_in_amend_mode": self.is_in_amend_mode,
            "cutoff_time": self.cutoff_time,
            "slot_end_time": self.slot_end_time,
            "slot_start_time": self.slot_start_time,
            "order_type": self.order_type,
            "total": self.total,
            "failed_payments": self.failed_payments,
        }

    def __iter__(self) -> Iterator[tuple[str, Any]]:
        """Allow ``dict(order_status)`` conversion."""
        return iter(self.to_dict().items())
