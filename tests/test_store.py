"""Tests for store models and lookups."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from pysainsburys import Sainsburys
from pysainsburys.auth import GOLAuth
from pysainsburys.models.store import Store, StoreList, StoreProduct


def test_store_from_dict() -> None:
    """Stores parse from Product Finder JSON."""
    store = Store.from_dict(
        {
            "id": "2665",
            "name": "Nine Elms",
            "address1": "62 Wandsworth Road",
            "city": "London",
            "postCode": "SW8 2LF",
            "distance": "1.80",
            "latitude": 51.48139,
            "longitude": -0.12808,
            "isAvailable": True,
            "isOpen": False,
        }
    )
    assert store.store_id == "2665"
    assert store.distance == 1.8
    assert store.is_open is False


def test_store_list_from_dict() -> None:
    """Store lists parse pagination metadata."""
    data = {
        "content": [
            {"id": "1", "name": "A", "address1": "x", "city": "y", "postCode": "z"}
        ],
        "page": {"size": 1, "number": 1, "totalElements": 1, "totalPages": 1},
    }
    stores = StoreList.from_dict(data)
    assert len(stores.stores) == 1
    assert stores.page.total_elements == 1


def test_store_from_collect_dict() -> None:
    """Click-and-collect locations parse into Store objects."""
    store = Store.from_collect_dict(
        {
            "location_uid": "106",
            "name": "Fulham Wharf Store",
            "store_number": "2658",
            "postcode": "SW6 2SY",
            "address1": "27 Townmead Road",
            "city": "London",
            "distance": 3,
            "is_available": True,
        }
    )
    assert store.store_number == "2658"
    assert store.location_uid == "106"
    assert store.post_code == "SW6 2SY"
    assert store.distance == 3.0
    assert store.store_id == ""
    assert store.click_and_collect_available is True


def test_store_from_dict_sets_click_and_collect() -> None:
    """Product Finder stores expose click-and-collect availability."""
    store = Store.from_dict(
        {
            "id": "2665",
            "name": "Nine Elms",
            "address1": "62 Wandsworth Road",
            "city": "London",
            "postCode": "SW8 2LF",
            "isAvailable": True,
        }
    )
    assert store.click_and_collect_available is True


def test_store_list_from_collect_dict() -> None:
    """Click-and-collect responses parse into StoreList objects."""
    stores = StoreList.from_dict(
        {
            "locations": [
                {
                    "location_uid": "106",
                    "name": "Fulham",
                    "store_number": "2658",
                    "postcode": "SW6 2SY",
                    "address1": "Road",
                    "city": "London",
                    "is_available": True,
                }
            ],
            "controls": {
                "total_record_count": 1,
                "returned_record_count": 1,
                "page": {"active": 1, "first": 1, "last": 1, "size": 10},
            },
        }
    )
    assert len(stores.stores) == 1
    assert stores.stores[0].store_number == "2658"
    assert stores.controls is not None
    assert stores.page is None


def test_store_product_from_dict() -> None:
    """In-store products include aisle and stock."""
    product = StoreProduct.from_dict(
        {
            "productCode": "357937",
            "productName": "Semi Skimmed Milk",
            "retail": {"price": "1.75", "pricePerUnit": "0.77"},
            "stock": "IN_STOCK",
            "aisle": "30",
        }
    )
    assert product.product_code == "357937"
    assert product.price == 1.75
    assert product.aisle == "30"


@pytest.fixture
def client() -> Sainsburys:
    """Sainsburys client with mocked API."""
    auth = MagicMock(spec=GOLAuth)
    auth.session = MagicMock()
    auth.close = AsyncMock()
    sainsburys = Sainsburys(auth)
    sainsburys.api.send_product_finder_request = AsyncMock()
    sainsburys.api.send_public_request = AsyncMock()
    return sainsburys


@pytest.mark.asyncio
async def test_find_stores_binds_api(client: Sainsburys) -> None:
    """find_stores binds stores for in-store product lookups."""
    client.api.send_product_finder_request.return_value = {
        "content": [
            {
                "id": "2665",
                "name": "Nine Elms",
                "address1": "62 Wandsworth Road",
                "city": "London",
                "postCode": "SW8 2LF",
                "isAvailable": True,
            }
        ],
        "page": {"size": 1, "number": 1, "totalElements": 1, "totalPages": 1},
    }
    stores = await client.find_stores(51.5, -0.12)
    assert len(stores.stores) == 1
    assert stores.stores[0]._api is client.api
    client.api.send_product_finder_request.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_store_binds_api(client: Sainsburys) -> None:
    """get_store returns a store bound to the client API."""
    client.api.send_product_finder_request.return_value = {
        "id": "2665",
        "name": "Nine Elms",
        "address1": "62 Wandsworth Road",
        "city": "London",
        "postCode": "SW8 2LF",
        "isAvailable": True,
    }
    store = await client.get_store("2665")
    assert store.store_id == "2665"
    assert store._api is client.api


@pytest.mark.asyncio
async def test_store_search_products(client: Sainsburys) -> None:
    """Stores search in-store products via Product Finder."""
    client.api.send_product_finder_request = AsyncMock(
        side_effect=[
            {
                "id": "2665",
                "name": "Nine Elms",
                "address1": "62 Wandsworth Road",
                "city": "London",
                "postCode": "SW8 2LF",
                "isAvailable": True,
            },
            {
                "content": [
                    {
                        "productCode": "1",
                        "productName": "Milk",
                        "retail": {"price": "1"},
                        "stock": "IN_STOCK",
                    }
                ],
                "page": {"size": 1, "number": 1, "totalElements": 1, "totalPages": 1},
            },
        ]
    )
    store = await client.get_store("2665")
    products = await store.search_products("milk")
    assert products.products[0].name == "Milk"
    client.api.send_product_finder_request.assert_awaited_with(
        "/v2/products",
        params={
            "storeId": "2665",
            "keyword": "milk",
            "page": 1,
            "size": 20,
        },
    )


@pytest.mark.asyncio
async def test_find_stores_by_postcode(client: Sainsburys) -> None:
    """Postcode store search returns click-and-collect stores."""
    client.api.send_public_request = AsyncMock(
        return_value={
            "locations": [
                {
                    "location_uid": "106",
                    "name": "Fulham",
                    "store_number": "2658",
                    "postcode": "SW6 2SY",
                    "address1": "Road",
                    "city": "London",
                    "is_available": True,
                }
            ],
            "controls": {
                "total_record_count": 1,
                "returned_record_count": 1,
                "page": {"active": 1, "first": 1, "last": 1, "size": 10},
            },
        }
    )
    stores = await client.find_stores_by_postcode("SW1A1AA")
    assert len(stores.stores) == 1
    assert stores.stores[0].click_and_collect_available is True
    assert stores.stores[0]._api is client.api
    client.api.send_public_request.assert_awaited_once()
