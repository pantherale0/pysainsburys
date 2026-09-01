"""Tests for customer favourites operations."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from pysainsburys import Sainsburys
from pysainsburys.auth import GOLAuth
from pysainsburys.models import Product, bind_product


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
async def test_favourites_fetch(client: Sainsburys) -> None:
    """Customers list favourites through the favourites resource."""
    client.api.send_request = AsyncMock(
        side_effect=[
            {"user_id": "682092082"},
            {
                "products": [{"product_uid": "6731637", "name": "Mineral Water"}],
                "controls": {
                    "total_record_count": 1,
                    "returned_record_count": 1,
                    "page": {"active": 1, "first": 1, "last": 1, "size": 20},
                },
            },
        ]
    )

    customer = await client.get_customer()
    favourites = await customer.favourites.fetch(page_number=1, page_size=20)

    assert favourites.controls.total_record_count == 1
    assert favourites.products[0].product_uid == "6731637"
    assert favourites.products[0]._api is client.api


@pytest.mark.asyncio
async def test_favourites_add(client: Sainsburys) -> None:
    """Customers can add products to favourites."""
    client.api.send_request = AsyncMock(side_effect=[{"user_id": "682092082"}, None])
    customer = await client.get_customer()
    product = bind_product(
        client.api,
        Product(product_uid="6731637", name="Mineral Water"),
    )

    await customer.favourites.add(product)

    assert product.is_favourite is True
    client.api.send_request.assert_awaited_with(
        endpoint="add_favourite",
        body={"item": "6731637"},
    )


@pytest.mark.asyncio
async def test_favourites_remove(client: Sainsburys) -> None:
    """Customers can remove products from favourites."""
    client.api.send_request = AsyncMock(side_effect=[{"user_id": "682092082"}, None])
    customer = await client.get_customer()
    product = bind_product(
        client.api,
        Product(product_uid="6731637", name="Mineral Water", is_favourite=True),
    )

    await customer.favourites.remove(product, source_type="MANUAL")

    assert product.is_favourite is False
    client.api.send_request.assert_awaited_with(
        endpoint="remove_favourite",
        PRODUCT_SKU="6731637",
        params={"sourceType": "MANUAL"},
    )
