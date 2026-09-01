"""Tests for customer order operations."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from pysainsburys import Sainsburys
from pysainsburys.auth import GOLAuth


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


@pytest.mark.asyncio
async def test_orders_fetch(client: Sainsburys) -> None:
    """Customers list orders through the orders resource."""
    client.api.send_request = AsyncMock(
        side_effect=[
            {"user_id": "682092082"},
            {
                "orders": [
                    {
                        "order_id": "order-1",
                        "order_uid": "order-1",
                        "total": 42.5,
                        "status": "CONFIRMED",
                    }
                ],
                "controls": {
                    "total_record_count": 1,
                    "returned_record_count": 1,
                    "page": {"active": 1, "first": 1, "last": 1, "size": 20},
                },
            },
        ]
    )

    customer = await client.get_customer()
    orders = await customer.orders.fetch(page_number=1, page_size=20)

    assert orders.controls.total_record_count == 1
    assert orders.orders[0].order_id == "order-1"


@pytest.mark.asyncio
async def test_orders_latest(client: Sainsburys) -> None:
    """Latest order is the first item in the cached list."""
    client.api.send_request = AsyncMock(
        side_effect=[
            {"user_id": "682092082"},
            {
                "orders": [
                    {"order_id": "order-latest", "order_uid": "order-latest"},
                    {"order_id": "order-old", "order_uid": "order-old"},
                ],
                "controls": {"total_record_count": 2, "page": {}},
            },
        ]
    )

    customer = await client.get_customer()
    await customer.orders.fetch()

    assert customer.orders.latest.order_id == "order-latest"


@pytest.mark.asyncio
async def test_order_fetch(client: Sainsburys) -> None:
    """Order handles fetch a single order by id."""
    client.api.send_request = AsyncMock(
        side_effect=[
            {"user_id": "682092082"},
            {
                "order_id": "order-1",
                "order_uid": "order-1",
                "total": 10.0,
                "status": "CONFIRMED",
            },
        ]
    )

    customer = await client.get_customer()
    order = await customer.orders["order-1"].fetch()

    assert order.order_id == "order-1"
    assert order.total == 10.0
    client.api.send_request.assert_awaited_with(
        endpoint="get_order",
        ORDER_ID="order-1",
    )


@pytest.mark.asyncio
async def test_order_status_for_active_order(client: Sainsburys) -> None:
    """Order handles fetch live status for the active order."""
    client.api.send_request = AsyncMock(
        side_effect=[
            {"user_id": "682092082"},
            {
                "order_uid": "order-1",
                "is_cutoff": True,
                "total": 42.5,
                "order_type": "delivery",
            },
        ]
    )

    customer = await client.get_customer()
    status = await customer.orders["order-1"].status()

    assert status.order_uid == "order-1"
    assert status.is_cutoff is True
    assert status.total == 42.5


@pytest.mark.asyncio
async def test_order_status_falls_back_for_other_order(client: Sainsburys) -> None:
    """Status for a non-active order falls back to order details."""
    client.api.send_request = AsyncMock(
        side_effect=[
            {"user_id": "682092082"},
            {"order_uid": "order-active", "total": 1.0},
            {
                "order_id": "order-old",
                "order_uid": "order-old",
                "total": 99.0,
                "order_type": "collection",
            },
        ]
    )

    customer = await client.get_customer()
    status = await customer.orders["order-old"].status()

    assert status.order_uid == "order-old"
    assert status.total == 99.0
    assert status.order_type == "collection"


@pytest.mark.asyncio
async def test_orders_latest_requires_cache(client: Sainsburys) -> None:
    """Latest order is unavailable until orders are fetched."""
    client.api.send_request = AsyncMock(return_value={"user_id": "682092082"})
    customer = await client.get_customer()

    with pytest.raises(LookupError):
        _ = customer.orders.latest
