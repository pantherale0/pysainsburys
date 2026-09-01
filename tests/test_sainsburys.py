"""Tests for the Sainsburys facade."""

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
def sainsburys(mock_auth: MagicMock) -> Sainsburys:
    """Fixture for the Sainsburys object."""
    client = Sainsburys(mock_auth)
    client.api.send_request = AsyncMock(
        side_effect=[
            {"user_id": "682092082", "given_name": "Jordan"},
            {"basket_id": "b1", "item_count": 0, "items": []},
            {"products": [], "controls": {"total_record_count": 0, "page": {}}},
            {
                "orders": [{"order_id": "order-1", "order_uid": "order-1", "total": 0}],
                "controls": {"total_record_count": 1, "page": {}},
            },
            {"order_uid": "order-1", "total": 0},
        ]
    )
    client.api.close = AsyncMock(return_value=None)
    return client


@pytest.mark.asyncio
async def test_context_manager_closes_session(sainsburys: Sainsburys) -> None:
    """The async context manager closes the API session on exit."""
    async with sainsburys:
        pass
    sainsburys.api.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_update_refreshes_cached_data(sainsburys: Sainsburys) -> None:
    """Update loads customer, basket, favourites, orders, and status."""
    await sainsburys.update()
    assert sainsburys.customer is not None
    assert sainsburys.customer.given_name == "Jordan"
    assert sainsburys.customer.basket.cached is not None
    assert sainsburys.customer.favourites.cached is not None
    assert sainsburys.customer.orders.cached is not None
    latest = sainsburys.customer.orders.latest
    assert latest.order_id == "order-1"


@pytest.mark.asyncio
async def test_customer_favourites_fetch(sainsburys: Sainsburys) -> None:
    """Favourites are fetched through the customer resource."""
    sainsburys.api.send_request = AsyncMock(
        side_effect=[
            {"user_id": "682092082", "given_name": "Jordan"},
            {
                "products": [
                    {
                        "product_uid": "6731637",
                        "name": "Mineral Water",
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
    customer = await sainsburys.get_customer()
    favourites = await customer.favourites.fetch(page_number=1, page_size=20)
    assert favourites.controls.total_record_count == 1
    assert favourites.products[0].product_uid == "6731637"


@pytest.mark.asyncio
async def test_get_product_uses_public_request(sainsburys: Sainsburys) -> None:
    """Product lookup does not require a commerce session."""
    sainsburys.api.send_public_request = AsyncMock(
        return_value={
            "product": {
                "product_uid": "3236048",
                "name": "Warburtons Soft Farmhouse Thick Sliced White Bread 800g",
                "retail_price": {"price": 1.65},
                "is_available": True,
            }
        }
    )
    product = await sainsburys.get_product("3236048")
    sainsburys.api.send_public_request.assert_awaited_once_with(
        endpoint="get_product",
        PRODUCT_UID="3236048",
    )
    assert product.product_uid == "3236048"
    assert "Warburtons" in product.name


def test_register_and_remove_callback(sainsburys: Sainsburys) -> None:
    """Callbacks can be registered and removed."""
    callback = MagicMock()
    sainsburys.register_callback(callback)
    assert callback in sainsburys.updated_data_callbacks
    sainsburys.remove_callback(callback)
    assert callback not in sainsburys.updated_data_callbacks
