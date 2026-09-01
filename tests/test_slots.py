"""Tests for delivery and collection slot listing."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from pysainsburys import Sainsburys
from pysainsburys.auth import GOLAuth
from pysainsburys.enum import SlotType
from pysainsburys.slots import Slots, build_list_slots_payload

SAMPLES = Path(__file__).resolve().parents[1] / "docs/reverse-engineering/samples"
SLOT_WEEK_SAMPLE = json.loads(
    (SAMPLES / "slot-week.delivery.excerpt.json").read_text(encoding="utf-8")
)


@pytest.fixture
def mock_auth() -> MagicMock:
    """Fixture for a mocked GOLAuth object."""
    mock = MagicMock(spec=GOLAuth)
    mock.user_id = "682092082"
    mock.next_refresh = None
    mock.send_request = AsyncMock()
    mock.send_refresh_request = AsyncMock(return_value=None)
    mock.close = AsyncMock(return_value=None)
    return mock


@pytest.fixture
def client(mock_auth: MagicMock) -> Sainsburys:
    """Fixture for the Sainsburys client."""
    return Sainsburys(mock_auth)


def test_build_list_slots_payload_normalises_postcode() -> None:
    """Slot list payloads normalise postcodes and include slot type."""
    payload = build_list_slots_payload(
        slot_type=SlotType.DELIVERY,
        store_identifier="0474",
        postcode="sw1a 1aa",
        week_start_date="2026-03-02",
    )
    assert payload == {
        "slot_type": "delivery",
        "store_identifier": "0474",
        "postcode": "SW1A1AA",
        "week_start_date": "2026-03-02",
    }


@pytest.mark.asyncio
async def test_list_delivery_slots_uses_location_context(client: Sainsburys) -> None:
    """Delivery slot listing fills context and sends POST with override header."""
    client.api.send_request = AsyncMock(
        side_effect=[
            {"user_id": "682092082"},
            {
                "slot_type": "delivery",
                "postcode": "SW1A1AA",
                "store_identifier": "0474",
            },
            SLOT_WEEK_SAMPLE,
        ]
    )

    customer = await client.get_customer()
    week = await customer.slots.list_delivery()

    assert week.slot_type is SlotType.DELIVERY
    assert week.store_identifier == "0474"
    assert len(week.available_slots) == 2
    assert week.available_slots[0].slot_uid == "slot-delivery-0630"

    list_call = client.api.send_request.await_args_list[-1]
    assert list_call.kwargs["endpoint"] == "list_slots"
    body = list_call.kwargs["body"]
    assert body["slot_type"] == "delivery"
    assert body["postcode"] == "SW1A1AA"
    assert body["store_identifier"] == "0474"
    assert "week_start_date" in body


@pytest.mark.asyncio
async def test_list_collection_slots_skips_context_when_disabled(
    client: Sainsburys,
) -> None:
    """Collection listing can bypass location context when requested."""
    client.api.send_request = AsyncMock(
        side_effect=[
            {"user_id": "682092082"},
            SLOT_WEEK_SAMPLE,
        ]
    )

    customer = await client.get_customer()
    week = await customer.slots.list_collection(
        store_identifier="0474",
        location_uid="loc-123",
        week_start_date="2026-03-02",
        use_location_context=False,
    )

    assert week.slot_type is SlotType.COLLECTION
    list_call = client.api.send_request.await_args_list[-1]
    body = list_call.kwargs["body"]
    assert body["slot_type"] == "collection"
    assert body["location_uid"] == "loc-123"


@pytest.mark.asyncio
async def test_fetch_reservation(client: Sainsburys) -> None:
    """Slot reservations parse nested slot metadata."""
    client.api.send_request = AsyncMock(
        side_effect=[
            {"user_id": "682092082"},
            {
                "reservation_type": "delivery",
                "postcode": "SW1A1AA",
                "store_identifier": "0474",
                "is_expired": False,
                "slot": {
                    "start_time": "2026-03-07T06:30:00Z",
                    "end_time": "2026-03-07T07:30:00Z",
                    "price": 4.0,
                },
            },
        ]
    )

    customer = await client.get_customer()
    reservation = await customer.slots.fetch_reservation()

    assert reservation.reservation_type == "delivery"
    assert reservation.slot is not None
    assert reservation.slot.price == 4.0
    client.api.send_request.assert_awaited_with(
        endpoint="get_slot_reservation", params=None
    )


@pytest.mark.asyncio
async def test_slots_access_directly(mock_auth: MagicMock) -> None:
    """Slots can be used without going through Customer."""
    from pysainsburys.api import API

    mock_auth.send_request = AsyncMock(return_value=SLOT_WEEK_SAMPLE)
    api = API(mock_auth)
    slots = Slots(api)
    week = await slots.list(
        slot_type=SlotType.DELIVERY,
        store_identifier="0474",
        postcode="SW1A1AA",
        week_start_date="2026-03-02",
        use_location_context=False,
    )
    assert len(week.slots) == 3

    call = mock_auth.send_request.await_args
    assert call.kwargs["method"] == "POST"
    assert call.kwargs["url"].endswith("/slot/v2/slots")
    assert call.kwargs["headers"] == {"X-Http-Method-Override": "GET"}
    assert call.kwargs["body"]["slot_type"] == "delivery"
