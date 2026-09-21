"""Tests for catalogue promotions and Nectar prices on products."""

from __future__ import annotations

from pysainsburys.models import NectarPrice, Product, Promotion


def test_product_from_dict_keeps_promotion_and_nectar_price() -> None:
    """Promotions and nectar_price survive parsing and dict conversion."""
    product = Product.from_dict(
        {
            "product_uid": "7895763",
            "name": "Comfort Heavenly Nectar",
            "retail_price": {"price": 3.0, "measure": "unit"},
            "promotions": [
                {
                    "promotion_uid": "10759408",
                    "strap_line": "Buy 1 for 3",
                    "start_date": "2026-08-30T23:00:00Z",
                    "end_date": "2026-09-21T23:00:00Z",
                    "original_price": 5,
                    "promo_mechanic_id": "99",
                    "is_nectar": True,
                    "promo_type": "SIMPLE_FIXED_PRICE",
                    "promo_group": "simple",
                    "link": "/gol-ui/promo-lister/10759408",
                    "icon": "",
                }
            ],
            "nectar_price": {
                "retail_price": 3,
                "unit_price": 3.45,
                "measure": "unit",
                "url": "https://www.sainsburys.co.uk/shop/gb/groceries/nectar-prices",
                "category_seo_url": "gb/groceries/nectar-prices",
            },
        }
    )
    assert len(product.promotions) == 1
    promotion = product.promotions[0]
    assert isinstance(promotion, Promotion)
    assert promotion.strap_line == "Buy 1 for 3"
    assert promotion.original_price == 5.0
    assert promotion.is_nectar is True
    assert promotion.icon is None
    assert isinstance(product.nectar_price, NectarPrice)
    assert product.nectar_price.retail_price == 3.0
    assert product.nectar_price.unit_price == 3.45
    payload = product.to_dict()
    assert payload["promotions"][0]["promotion_uid"] == "10759408"
    assert payload["nectar_price"]["measure"] == "unit"


def test_product_without_offers() -> None:
    """Products with no offer payload keep an empty promotion list."""
    product = Product.from_dict({"product_uid": "1", "name": "Milk"})
    assert product.promotions == []
    assert product.nectar_price is None
    assert product.to_dict()["promotions"] == []
    assert product.to_dict()["nectar_price"] is None
