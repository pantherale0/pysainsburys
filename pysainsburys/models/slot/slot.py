"""Delivery and collection slot models."""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass, field
from typing import Any

from ...enum import SlotType


def _optional_float(value: object) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _slot_available(data: dict[str, Any]) -> bool:
    if "is_available" in data:
        return bool(data["is_available"])
    if "available" in data:
        return bool(data["available"])
    status = data.get("status")
    if isinstance(status, str):
        return status.upper() in {"AVAILABLE", "OPEN", "BOOKABLE"}
    return True


@dataclass(slots=True)
class DeliverySlot:
    """
    A single bookable delivery or collection time window.

    Attributes:
        slot_uid: Stable slot identifier from the API when provided.
        start_time: Slot start timestamp (ISO-8601).
        end_time: Slot end timestamp (ISO-8601).
        price: Customer-facing slot price in pounds sterling.
        unqualified_price: List price before delivery-pass or promotions.
        is_available: Whether the slot can be booked.
        status: Raw availability status string from the API.
        slot_type: Delivery or collection type when returned per slot.

    """

    slot_uid: str | None = None
    start_time: str | None = None
    end_time: str | None = None
    price: float | None = None
    unqualified_price: float | None = None
    is_available: bool = True
    status: str | None = None
    slot_type: str | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DeliverySlot:
        """Parse a slot entry from grocery API JSON."""
        return cls(
            slot_uid=(
                data.get("slot_uid")
                or data.get("slot_id")
                or data.get("uid")
                or data.get("id")
            ),
            start_time=data.get("start_time") or data.get("slot_start_time"),
            end_time=data.get("end_time") or data.get("slot_end_time"),
            price=_optional_float(data.get("price") or data.get("slot_price")),
            unqualified_price=_optional_float(
                data.get("unqualified_price") or data.get("list_price")
            ),
            is_available=_slot_available(data),
            status=data.get("status"),
            slot_type=data.get("slot_type") or data.get("order_type"),
        )

    def to_dict(self) -> dict[str, Any]:
        """Serialise the slot to a plain dictionary."""
        return {
            "slot_uid": self.slot_uid,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "price": self.price,
            "unqualified_price": self.unqualified_price,
            "is_available": self.is_available,
            "status": self.status,
            "slot_type": self.slot_type,
        }

    def __iter__(self) -> Iterator[tuple[str, Any]]:
        """Allow ``dict(slot)`` conversion."""
        return iter(self.to_dict().items())


@dataclass(slots=True)
class SlotDay:
    """Slots grouped for a single calendar day."""

    date: str | None = None
    day_label: str | None = None
    slots: list[DeliverySlot] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SlotDay:
        """Parse a day entry from grocery API JSON."""
        raw_slots = data.get("slots") or data.get("available_slots") or []
        return cls(
            date=data.get("date") or data.get("day_date"),
            day_label=data.get("day_label") or data.get("label") or data.get("day_name"),
            slots=[DeliverySlot.from_dict(item) for item in raw_slots if isinstance(item, dict)],
        )

    @property
    def available_slots(self) -> list[DeliverySlot]:
        """Return only slots marked as available."""
        return [slot for slot in self.slots if slot.is_available]

    def to_dict(self) -> dict[str, Any]:
        """Serialise the day to a plain dictionary."""
        return {
            "date": self.date,
            "day_label": self.day_label,
            "slots": [slot.to_dict() for slot in self.slots],
        }

    def __iter__(self) -> Iterator[tuple[str, Any]]:
        """Allow ``dict(day)`` conversion."""
        return iter(self.to_dict().items())


@dataclass(slots=True)
class SlotWeek:
    """
    Week view of delivery or collection slots.

    Attributes:
        slot_type: Requested slot type (``delivery`` or ``collection``).
        week_start_date: First day of the returned week when provided.
        store_identifier: Fulfilment store number used for the query.
        postcode: Delivery postcode context when applicable.
        location_uid: Click-and-collect location uid when applicable.
        days: Day groupings with nested slot windows.

    """

    slot_type: SlotType | None = None
    week_start_date: str | None = None
    store_identifier: str | None = None
    postcode: str | None = None
    location_uid: str | None = None
    days: list[SlotDay] = field(default_factory=list)

    @classmethod
    def from_dict(
        cls,
        data: dict[str, Any],
        *,
        slot_type: SlotType | None = None,
        store_identifier: str | None = None,
        postcode: str | None = None,
        location_uid: str | None = None,
    ) -> SlotWeek:
        """Parse a slot week from grocery API JSON."""
        days_data = data.get("days") or data.get("slot_days")
        if days_data is None:
            weeks = data.get("weeks") or data.get("slot_weeks")
            if isinstance(weeks, list):
                days_data = []
                for week in weeks:
                    if isinstance(week, dict):
                        days_data.extend(week.get("days", []))
        days = [
            SlotDay.from_dict(item)
            for item in (days_data or [])
            if isinstance(item, dict)
        ]
        return cls(
            slot_type=slot_type,
            week_start_date=data.get("week_start_date") or data.get("start_date"),
            store_identifier=store_identifier or data.get("store_identifier"),
            postcode=postcode or data.get("postcode"),
            location_uid=location_uid or data.get("location_uid"),
            days=days,
        )

    @property
    def slots(self) -> list[DeliverySlot]:
        """Flatten all slots across days."""
        return [slot for day in self.days for slot in day.slots]

    @property
    def available_slots(self) -> list[DeliverySlot]:
        """Flatten only available slots across days."""
        return [slot for slot in self.slots if slot.is_available]

    def to_dict(self) -> dict[str, Any]:
        """Serialise the slot week to a plain dictionary."""
        return {
            "slot_type": self.slot_type.value if self.slot_type else None,
            "week_start_date": self.week_start_date,
            "store_identifier": self.store_identifier,
            "postcode": self.postcode,
            "location_uid": self.location_uid,
            "days": [day.to_dict() for day in self.days],
        }

    def __iter__(self) -> Iterator[tuple[str, Any]]:
        """Allow ``dict(slot_week)`` conversion."""
        return iter(self.to_dict().items())


@dataclass(slots=True)
class SlotReservation:
    """Current slot reservation state for the customer."""

    reservation_type: str | None = None
    postcode: str | None = None
    region: str | None = None
    store_identifier: str | None = None
    location_uid: str | None = None
    is_expired: bool = False
    reserved_until: str | None = None
    is_alcohol_restricted_store: bool = False
    flexi_stores: list[str] = field(default_factory=list)
    slot: DeliverySlot | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SlotReservation:
        """Parse slot reservation JSON."""
        slot_data = data.get("slot")
        slot = (
            DeliverySlot.from_dict(slot_data)
            if isinstance(slot_data, dict)
            else None
        )
        flexi = data.get("flexi_stores") or []
        return cls(
            reservation_type=data.get("reservation_type"),
            postcode=data.get("postcode"),
            region=data.get("region"),
            store_identifier=data.get("store_identifier"),
            location_uid=data.get("location_uid"),
            is_expired=bool(data.get("is_expired", False)),
            reserved_until=data.get("reserved_until"),
            is_alcohol_restricted_store=bool(
                data.get("is_alcohol_restricted_store", False)
            ),
            flexi_stores=[str(value) for value in flexi],
            slot=slot,
        )

    def to_dict(self) -> dict[str, Any]:
        """Serialise the reservation to a plain dictionary."""
        return {
            "reservation_type": self.reservation_type,
            "postcode": self.postcode,
            "region": self.region,
            "store_identifier": self.store_identifier,
            "location_uid": self.location_uid,
            "is_expired": self.is_expired,
            "reserved_until": self.reserved_until,
            "is_alcohol_restricted_store": self.is_alcohol_restricted_store,
            "flexi_stores": list(self.flexi_stores),
            "slot": self.slot.to_dict() if self.slot else None,
        }

    def __iter__(self) -> Iterator[tuple[str, Any]]:
        """Allow ``dict(reservation)`` conversion."""
        return iter(self.to_dict().items())


@dataclass(slots=True)
class LocationContext:
    """Location context used when listing slots."""

    slot_type: str | None = None
    postcode: str | None = None
    store_identifier: str | None = None
    location_uid: str | None = None
    region: str | None = None
    order_uid: str | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> LocationContext:
        """Parse location context JSON."""
        return cls(
            slot_type=data.get("slot_type") or data.get("reservation_type"),
            postcode=data.get("postcode"),
            store_identifier=data.get("store_identifier"),
            location_uid=data.get("location_uid"),
            region=data.get("region"),
            order_uid=data.get("order_uid"),
        )

    def to_dict(self) -> dict[str, Any]:
        """Serialise location context to a plain dictionary."""
        return {
            "slot_type": self.slot_type,
            "postcode": self.postcode,
            "store_identifier": self.store_identifier,
            "location_uid": self.location_uid,
            "region": self.region,
            "order_uid": self.order_uid,
        }

    def __iter__(self) -> Iterator[tuple[str, Any]]:
        """Allow ``dict(location_context)`` conversion."""
        return iter(self.to_dict().items())
