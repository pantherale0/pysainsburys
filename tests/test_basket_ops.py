"""Tests for product basket operations and customer basket access."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from pysainsburys import Sainsburys
from pysainsburys.auth import GOLAuth
from pysainsburys.exceptions import NotBoundError
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


def _basket_response() -> dict[str, object]:
    return {
        "basket_id": "b1",
        "item_count": 1,
        "total_price": 2.5,
        "items": [
            {
                "item_uid": "line-1",
                "quantity": 2,
                "name": "Mineral Water",
                "product": {
                    "sku": "6731637",
                    "name": "Mineral Water",
                },
            }
        ],
    }


@pytest.mark.asyncio
async def test_product_add_to_basket(client: Sainsburys) -> None:
    """Products add items via the basket item endpoint."""
    client.api.send_request = AsyncMock(return_value=_basket_response())
    product = bind_product(
        client.api,
        Product(product_uid="6731637", name="Mineral Water"),
    )

    basket = await product.add_to_basket(2)

    assert basket.item_count == 1
    client.api.send_request.assert_awaited_once_with(
        endpoint="add_basket_item",
        body={
            "product_uid": "6731637",
            "quantity": 2,
            "uom": "ea",
        },
    )


@pytest.mark.asyncio
async def test_product_add_to_basket_zero_removes(client: Sainsburys) -> None:
    """Adding zero quantity removes the product from the basket."""
    client.api.send_request = AsyncMock(
        side_effect=[
            _basket_response(),
            _basket_response(),
        ]
    )
    product = bind_product(
        client.api,
        Product(product_uid="6731637", name="Mineral Water"),
    )

    await product.add_to_basket(0)

    assert client.api.send_request.await_count == 2
    client.api.send_request.assert_awaited_with(
        endpoint="update_basket",
        body={
            "items": [
                {
                    "product_uid": "6731637",
                    "quantity": 0,
                    "uom": "ea",
                    "item_uid": "line-1",
                }
            ]
        },
    )


@pytest.mark.asyncio
async def test_product_set_basket_quantity(client: Sainsburys) -> None:
    """Products set absolute quantities via basket update."""
    client.api.send_request = AsyncMock(
        side_effect=[
            _basket_response(),
            _basket_response(),
        ]
    )
    product = bind_product(
        client.api,
        Product.from_dict(
            {
                "product_uid": "6731637",
                "name": "Mineral Water",
                "retail_price": {"price": 1.25, "measure": "ea"},
            },
            api=client.api,
        ),
    )

    await product.set_basket_quantity(3)

    client.api.send_request.assert_awaited_with(
        endpoint="update_basket",
        body={
            "items": [
                {
                    "product_uid": "6731637",
                    "quantity": 3,
                    "uom": "ea",
                    "item_uid": "line-1",
                }
            ]
        },
    )


@pytest.mark.asyncio
async def test_product_set_basket_quantity_zero_removes(client: Sainsburys) -> None:
    """Setting quantity to zero removes the product."""
    client.api.send_request = AsyncMock(
        side_effect=[
            _basket_response(),
            _basket_response(),
        ]
    )
    product = bind_product(
        client.api,
        Product(product_uid="6731637", name="Mineral Water"),
    )

    await product.set_basket_quantity(0)

    client.api.send_request.assert_awaited_with(
        endpoint="update_basket",
        body={
            "items": [
                {
                    "product_uid": "6731637",
                    "quantity": 0,
                    "uom": "ea",
                    "item_uid": "line-1",
                }
            ]
        },
    )


@pytest.mark.asyncio
async def test_product_remove_from_basket(client: Sainsburys) -> None:
    """Products can be removed from the basket."""
    client.api.send_request = AsyncMock(return_value=_basket_response())
    product = bind_product(
        client.api,
        Product(product_uid="6731637", name="Mineral Water"),
    )

    await product.remove_from_basket(item_uid="line-1")

    client.api.send_request.assert_awaited_once_with(
        endpoint="update_basket",
        body={
            "items": [
                {
                    "product_uid": "6731637",
                    "quantity": 0,
                    "uom": "ea",
                    "item_uid": "line-1",
                }
            ]
        },
    )


@pytest.mark.asyncio
async def test_unbound_product_raises(client: Sainsburys) -> None:
    """Basket operations require a bound client."""
    product = Product(product_uid="6731637", name="Mineral Water")
    with pytest.raises(NotBoundError):
        await product.add_to_basket(1)


@pytest.mark.asyncio
async def test_customer_basket_fetch(client: Sainsburys) -> None:
    """Customers fetch baskets through the basket resource."""
    client.api.send_request = AsyncMock(
        side_effect=[
            {"user_id": "682092082"},
            _basket_response(),
        ]
    )

    customer = await client.get_customer()
    basket = await customer.basket.fetch()

    assert basket.basket_id == "b1"
    assert customer.basket.cached is basket


@pytest.mark.asyncio
async def test_customer_basket_add(client: Sainsburys) -> None:
    """Customers add items through the basket resource."""
    client.api.send_request = AsyncMock(
        side_effect=[
            {"user_id": "682092082"},
            _basket_response(),
        ]
    )

    customer = await client.get_customer()
    basket = await customer.basket.add("6731637", 2, uom="ea")

    assert basket.item_count == 1
    client.api.send_request.assert_awaited_with(
        endpoint="add_basket_item",
        body={
            "product_uid": "6731637",
            "quantity": 2,
            "uom": "ea",
        },
    )


@pytest.mark.asyncio
async def test_customer_basket_set_quantity(client: Sainsburys) -> None:
    """Customers set absolute quantities through the basket resource."""
    client.api.send_request = AsyncMock(
        side_effect=[
            {"user_id": "682092082"},
            _basket_response(),
        ]
    )

    customer = await client.get_customer()
    await customer.basket.set_quantity("6731637", 3, item_uid="line-1")

    client.api.send_request.assert_awaited_with(
        endpoint="update_basket",
        body={
            "items": [
                {
                    "product_uid": "6731637",
                    "quantity": 3,
                    "uom": "ea",
                    "item_uid": "line-1",
                }
            ]
        },
    )


@pytest.mark.asyncio
async def test_customer_basket_remove(client: Sainsburys) -> None:
    """Customers remove items through the basket resource."""
    client.api.send_request = AsyncMock(
        side_effect=[
            {"user_id": "682092082"},
            _basket_response(),
        ]
    )

    customer = await client.get_customer()
    await customer.basket.remove("6731637", item_uid="line-1")

    client.api.send_request.assert_awaited_with(
        endpoint="update_basket",
        body={
            "items": [
                {
                    "product_uid": "6731637",
                    "quantity": 0,
                    "uom": "ea",
                    "item_uid": "line-1",
                }
            ]
        },
    )
