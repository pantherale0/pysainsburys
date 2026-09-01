"""Tests for API endpoint constants."""

from pysainsburys.const import GOL_BASE_URL, GOL_ENDPOINTS


def test_basket_endpoint_matches_live_capture_path() -> None:
    """Basket URLs match paths observed in live traffic captures."""
    basket_url = GOL_BASE_URL + GOL_ENDPOINTS["get_basket"]["endpoint"]
    assert basket_url.endswith("/groceries-api/gol-services/basket/v2/basket")
    assert not basket_url.endswith("/basket/basket")

    add_url = GOL_BASE_URL + GOL_ENDPOINTS["add_basket_item"]["endpoint"]
    assert add_url.endswith("/groceries-api/gol-services/basket/v2/basket/item")
