"""Tests for Nectar offers and Your Nectar Prices."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from pysainsburys import Sainsburys
from pysainsburys.auth import GOLAuth
from pysainsburys.models import (
    NectarOffer,
    NectarOffers,
    YourNectarPrices,
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


def test_nectar_offer_from_dict() -> None:
    """Nectar bonus offers parse from API JSON."""
    offer = NectarOffer.from_dict(
        {
            "id": "offer-1",
            "title": "Bonus points on bread",
            "subtitle": "Collect 100 points",
            "points": 100,
            "skus": ["3236048"],
            "expires": "2026-09-01T00:00:00Z",
        }
    )
    assert offer.offer_id == "offer-1"
    assert offer.points == 100
    assert offer.skus == ["3236048"]


def test_your_nectar_prices_from_dict() -> None:
    """Your Nectar Price opt-ins parse from API JSON."""
    prices = YourNectarPrices.from_dict(
        {
            "opted_in": [
                {
                    "offer_id": "ynp-1",
                    "sku": "1133585",
                    "expiry_date": "2026-09-03T22:59:59Z",
                }
            ],
            "not_opted_in": [],
            "ynps_available_until": "2026-09-10T22:28:11Z",
        }
    )
    assert len(prices.opted_in) == 1
    assert prices.opted_in[0].sku == "1133585"
    assert prices.available_until == "2026-09-10T22:28:11Z"


@pytest.mark.asyncio
async def test_customer_nectar_fetch_offers(client: Sainsburys) -> None:
    """Customers fetch Nectar offers through the nectar resource."""
    client.api.send_request = AsyncMock(
        side_effect=[
            {"user_id": "682092082"},
            {
                "account_status": "nectar_linked",
                "offers": [
                    {
                        "id": "offer-1",
                        "title": "Bonus points",
                        "subtitle": "On selected items",
                        "points": 50,
                        "skus": ["3236048"],
                    }
                ],
            },
        ]
    )

    customer = await client.get_customer()
    offers = await customer.nectar.fetch_offers()

    assert isinstance(offers, NectarOffers)
    assert offers.account_status == "nectar_linked"
    assert offers.offers[0].title == "Bonus points"
    client.api.send_request.assert_awaited_with(endpoint="get_nectar_offers")


@pytest.mark.asyncio
async def test_customer_nectar_fetch_prices(client: Sainsburys) -> None:
    """Customers fetch Your Nectar Prices through the nectar resource."""
    client.api.send_request = AsyncMock(
        side_effect=[
            {"user_id": "682092082"},
            {
                "opted_in": [],
                "not_opted_in": [
                    {
                        "offer_id": "ynp-1",
                        "sku": "1133585",
                    }
                ],
            },
        ]
    )

    customer = await client.get_customer()
    prices = await customer.nectar.fetch_your_nectar_prices()

    assert len(prices.not_opted_in) == 1
    client.api.send_request.assert_awaited_with(endpoint="get_ynp_opt_ins")


@pytest.mark.asyncio
async def test_customer_nectar_search_matches_product_name(client: Sainsburys) -> None:
    """Nectar search matches Your Nectar Prices by product name."""
    client.api.send_request = AsyncMock(
        side_effect=[
            {"user_id": "682092082"},
            {"account_status": "nectar_linked", "offers": []},
            {
                "opted_in": [
                    {
                        "offer_id": "ynp-1",
                        "sku": "1133585",
                    }
                ],
                "not_opted_in": [],
            },
            {
                "products": [
                    {
                        "product_uid": "1133585",
                        "name": "Sainsbury's Sliced White Mushrooms 250g",
                        "retail_price": {"price": 1.35, "measure": "ea"},
                    }
                ],
                "controls": {
                    "total_record_count": 1,
                    "returned_record_count": 1,
                    "page": {"active": 1, "first": 1, "last": 1, "size": 50},
                },
            },
        ]
    )

    customer = await client.get_customer()
    results = await customer.nectar.search("mushroom")

    assert len(results.hits) == 1
    assert results.hits[0].kind == "your_nectar_price"
    assert results.hits[0].product is not None
    assert "Mushrooms" in results.hits[0].product.name


@pytest.mark.asyncio
async def test_customer_nectar_unlock_prices(client: Sainsburys) -> None:
    """Customers unlock Your Nectar Prices through the nectar resource."""
    client.api.send_request = AsyncMock(
        side_effect=[
            {"user_id": "682092082"},
            {
                "opted_in": [],
                "not_opted_in": [{"offer_id": "ynp-1", "sku": "1133585"}],
            },
            {"updated_offer_ids": ["ynp-1"], "offer_response_failures": []},
        ]
    )

    customer = await client.get_customer()
    result = await customer.nectar.unlock_your_nectar_prices()

    assert result.updated_offer_ids == ["ynp-1"]
    client.api.send_request.assert_awaited_with(
        endpoint="unlock_ynp_opt_ins",
        body={"offer_id": "ynp-1"},
    )
