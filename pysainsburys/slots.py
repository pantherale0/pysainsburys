"""Delivery and collection slot listing."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any

from .enum import SlotType
from .models.slot import LocationContext, SlotReservation, SlotWeek

if TYPE_CHECKING:
    from .api import API

__all__ = ["Slots", "build_list_slots_payload"]


def build_list_slots_payload(
    *,
    slot_type: SlotType,
    store_identifier: str | None = None,
    postcode: str | None = None,
    location_uid: str | None = None,
    week_start_date: str | None = None,
    order_uid: str | None = None,
) -> dict[str, Any]:
    """
    Build the conservative ``SlotPayload`` body for slot week listing.

    Field names follow static analysis of the GOL Android app (v3.65.0). The
    live slot list endpoint was not captured in Phase 1; callers may need to
    supply ``store_identifier`` and ``postcode`` (delivery) or
    ``location_uid`` (collection) explicitly when location-context is empty.
    """
    payload: dict[str, Any] = {"slot_type": slot_type.value}
    if store_identifier is not None:
        payload["store_identifier"] = store_identifier
    if postcode is not None:
        payload["postcode"] = postcode.replace(" ", "").upper()
    if location_uid is not None:
        payload["location_uid"] = location_uid
    if week_start_date is not None:
        payload["week_start_date"] = week_start_date
    if order_uid is not None:
        payload["order_uid"] = order_uid
    return payload


def _default_week_start_date() -> str:
    """Return Monday of the current week as an ISO date string."""
    today = datetime.now(UTC).date()
    monday = today - timedelta(days=today.weekday())
    return monday.isoformat()


class Slots:
    """List delivery and collection slots for a customer."""

    def __init__(self, api: API) -> None:
        self._api = api
        self._reservation_cache: SlotReservation | None = None
        self._location_context_cache: LocationContext | None = None
        self._week_cache: SlotWeek | None = None

    @property
    def cached(self) -> SlotWeek | None:
        """Return the last fetched slot week, if any."""
        return self._week_cache

    @property
    def cached_reservation(self) -> SlotReservation | None:
        """Return the last fetched slot reservation, if any."""
        return self._reservation_cache

    async def fetch_reservation(
        self, *, order_uid: str | None = None
    ) -> SlotReservation:
        """Fetch the customer's current slot reservation state."""
        params: dict[str, str | int | float | bool] | None = (
            {"order_uid": order_uid} if order_uid else None
        )
        response = await self._api.send_request(
            endpoint="get_slot_reservation",
            params=params,
        )
        if not isinstance(response, dict):
            msg = "Slot reservation response was not a JSON object."
            raise TypeError(msg)
        reservation = SlotReservation.from_dict(response)
        self._reservation_cache = reservation
        return reservation

    async def fetch_location_context(self) -> LocationContext:
        """Fetch location context used when choosing delivery or collection."""
        response = await self._api.send_request(endpoint="get_slot_location_context")
        if not isinstance(response, dict):
            msg = "Slot location context response was not a JSON object."
            raise TypeError(msg)
        context = LocationContext.from_dict(response)
        self._location_context_cache = context
        return context

    async def list(
        self,
        *,
        slot_type: SlotType,
        store_identifier: str | None = None,
        postcode: str | None = None,
        location_uid: str | None = None,
        week_start_date: str | None = None,
        order_uid: str | None = None,
        use_location_context: bool = True,
    ) -> SlotWeek:
        """
        List available slots for delivery or click-and-collect.

        When ``use_location_context`` is true (default), missing
        ``store_identifier``, ``postcode``, or ``location_uid`` values are
        filled from :meth:`fetch_location_context` when available.
        """
        if use_location_context and (
            store_identifier is None or postcode is None or location_uid is None
        ):
            context = await self.fetch_location_context()
            store_identifier = store_identifier or context.store_identifier
            postcode = postcode or context.postcode
            location_uid = location_uid or context.location_uid
            order_uid = order_uid or context.order_uid

        if week_start_date is None:
            week_start_date = _default_week_start_date()

        body = build_list_slots_payload(
            slot_type=slot_type,
            store_identifier=store_identifier,
            postcode=postcode,
            location_uid=location_uid,
            week_start_date=week_start_date,
            order_uid=order_uid,
        )
        response = await self._api.send_request(endpoint="list_slots", body=body)
        if not isinstance(response, dict):
            msg = "Slot week response was not a JSON object."
            raise TypeError(msg)
        week = SlotWeek.from_dict(
            response,
            slot_type=slot_type,
            store_identifier=store_identifier,
            postcode=postcode,
            location_uid=location_uid,
        )
        self._week_cache = week
        return week

    async def list_delivery(
        self,
        *,
        postcode: str | None = None,
        store_identifier: str | None = None,
        week_start_date: str | None = None,
        order_uid: str | None = None,
        use_location_context: bool = True,
    ) -> SlotWeek:
        """List home-delivery slots."""
        return await self.list(
            slot_type=SlotType.DELIVERY,
            postcode=postcode,
            store_identifier=store_identifier,
            week_start_date=week_start_date,
            order_uid=order_uid,
            use_location_context=use_location_context,
        )

    async def list_collection(
        self,
        *,
        store_identifier: str | None = None,
        location_uid: str | None = None,
        week_start_date: str | None = None,
        order_uid: str | None = None,
        use_location_context: bool = True,
    ) -> SlotWeek:
        """List click-and-collect slots."""
        return await self.list(
            slot_type=SlotType.COLLECTION,
            store_identifier=store_identifier,
            location_uid=location_uid,
            week_start_date=week_start_date,
            order_uid=order_uid,
            use_location_context=use_location_context,
        )
