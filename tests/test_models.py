"""Tests for domain models."""

import json
from pathlib import Path

from pysainsburys.models import (
    Basket,
    Customer,
    OrderList,
    OrderStatus,
    Product,
    ProductList,
)

SAMPLES = Path(__file__).resolve().parents[1] / "docs/reverse-engineering/samples"


def test_product_from_favourites_sample() -> None:
    """Products parse from the Phase 1 favourites excerpt."""
    data = json.loads((SAMPLES / "favourites-product.excerpt.json").read_text())
    product_list = ProductList.from_dict(data)
    assert product_list.controls.total_record_count == 15
    assert len(product_list.products) == 1
    product = product_list.products[0]
    assert product.product_uid == "6731637"
    assert product.name.startswith("San Pellegrino")
    assert product.retail_price is not None
    assert product.retail_price.price == 1.25


def test_order_list_from_empty_sample() -> None:
    """Empty order lists parse correctly."""
    data = json.loads((SAMPLES / "order-list.empty.json").read_text())
    order_list = OrderList.from_dict(data)
    assert order_list.orders == []
    assert order_list.controls.total_record_count == 0


def test_basket_from_dict() -> None:
    """Baskets parse nested items and totals."""
    basket = Basket.from_dict(
        {
            "basket_id": "123",
            "item_count": 1,
            "total_price": 2.5,
            "items": [
                {
                    "product_uid": "6731637",
                    "quantity": 2,
                    "name": "Mineral Water",
                }
            ],
        }
    )
    assert basket.basket_id == "123"
    assert basket.item_count == 1
    assert basket.items[0].quantity == 2
    assert basket.is_empty is False


def test_basket_item_reads_nested_product_sku() -> None:
    """Basket lines expose product sku from nested product payloads."""
    basket = Basket.from_dict(
        {
            "item_count": 1,
            "items": [
                {
                    "item_uid": "29625759812",
                    "quantity": 4,
                    "subtotal_price": 6.6,
                    "product": {
                        "sku": "3236048",
                        "name": "Warburtons Bread",
                    },
                }
            ],
        }
    )
    assert basket.items[0].product_uid == "3236048"
    assert basket.items[0].name == "Warburtons Bread"
    assert basket.items[0].item_uid == "29625759812"
    assert basket.items[0].product_data == {
        "sku": "3236048",
        "name": "Warburtons Bread",
    }


def test_basket_item_nested_product_parses_to_product() -> None:
    """Nested basket product JSON can be parsed into a catalogue Product."""
    from pysainsburys.models import Basket, Product

    basket = Basket.from_dict(
        {
            "items": [
                {
                    "quantity": 1,
                    "product": {"sku": "3236048", "name": "Warburtons Bread"},
                }
            ],
        }
    )
    product = Product.from_basket_nested(basket.items[0].product_data or {})
    assert product.product_uid == "3236048"
    assert product.name == "Warburtons Bread"


def test_customer_display_name() -> None:
    """Customer display names prefer given and family names."""
    customer = Customer.from_dict(
        {
            "user_id": "682092082",
            "given_name": "Jordan",
            "family_name": "Harvey",
            "email": "user@example.com",
        }
    )
    assert customer.display_name == "Jordan Harvey"


def test_order_status_from_dict() -> None:
    """Order status fields map from API JSON keys."""
    status = OrderStatus.from_dict(
        {
            "order_uid": "order-1",
            "is_cutoff": True,
            "total": 42.5,
            "order_type": "delivery",
        }
    )
    assert status.order_uid == "order-1"
    assert status.is_cutoff is True
    assert status.total == 42.5
    assert status.order_type == "delivery"


def test_product_to_dict_roundtrip() -> None:
    """Product models support dict conversion."""
    product = Product.from_dict(
        {
            "product_uid": "6731637",
            "name": "Mineral Water",
            "retail_price": {"price": 1.25, "measure": "ea"},
        }
    )
    data = dict(product)
    assert data["product_uid"] == "6731637"
    assert data["retail_price"]["price"] == 1.25
