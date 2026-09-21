"""Tests for the command-line interface."""

from __future__ import annotations

import json

import pytest

from pysainsburys.cli import build_parser, default_session_path, parse_args
from pysainsburys.cli.output import emit_product, emit_product_list, emit_slot_week
from pysainsburys.enum import SlotType
from pysainsburys.models.common.pagination import PageControls
from pysainsburys.models.common.price import Price
from pysainsburys.models.product.product import Product, ProductList, ProductReviews
from pysainsburys.models.slot.slot import DeliverySlot, SlotDay, SlotWeek


def test_default_session_path() -> None:
    """The default session path lives under the user config directory."""
    path = default_session_path()
    assert path.name == "session.json"
    assert path.parent.name == "pysainsburys"


def test_parser_auth_url_command() -> None:
    """Auth URL command is parsed with defaults."""
    args = build_parser().parse_args(["auth", "url"])
    assert args.command == "auth"
    assert args.auth_command == "url"
    assert args.json is False


def test_parser_auth_login_command() -> None:
    """Credential login flags are parsed."""
    args = build_parser().parse_args(
        [
            "auth",
            "login",
            "-u",
            "user@example.com",
            "-p",
            "secret",
            "-m",
            "123456",
        ]
    )
    assert args.auth_command == "login"
    assert args.username == "user@example.com"
    assert args.password == "secret"
    assert args.mfa_code == "123456"


def test_parser_customer_show_command() -> None:
    """Customer show command is parsed."""
    args = build_parser().parse_args(["customer", "show"])
    assert args.command == "customer"
    assert args.customer_command == "show"


def test_parser_basket_add_command() -> None:
    """Basket add command parses product uid and quantity."""
    args = build_parser().parse_args(["basket", "add", "12345", "--quantity", "2.5"])
    assert args.command == "basket"
    assert args.basket_command == "add"
    assert args.product_uid == "12345"
    assert args.quantity == 2.5


def test_parser_basket_set_command() -> None:
    """Basket set command parses target quantity."""
    args = build_parser().parse_args(["basket", "set", "12345", "3"])
    assert args.basket_command == "set"
    assert args.quantity == 3.0


def test_parser_basket_clear_command() -> None:
    """Basket clear command is parsed."""
    args = build_parser().parse_args(["basket", "clear"])
    assert args.basket_command == "clear"


def test_parser_favourites_add_command() -> None:
    """Favourites add command parses the product uid."""
    args = build_parser().parse_args(["favourites", "add", "6731637"])
    assert args.favourites_command == "add"
    assert args.product_uid == "6731637"


def test_parser_orders_show_command() -> None:
    """Orders show command parses the order id."""
    args = build_parser().parse_args(["orders", "show", "order-1"])
    assert args.orders_command == "show"
    assert args.order_id == "order-1"


def test_parser_orders_status_command() -> None:
    """Orders status command accepts an optional order id."""
    args = build_parser().parse_args(["orders", "status"])
    assert args.orders_command == "status"
    assert args.order_id is None


def test_parser_product_show_command() -> None:
    """Product show command parses the product uid."""
    args = build_parser().parse_args(["product", "show", "abc-123"])
    assert args.command == "product"
    assert args.product_command == "show"
    assert args.product_uid == "abc-123"


def test_parser_product_search_command() -> None:
    """Product search command parses keyword and pagination."""
    args = build_parser().parse_args(
        ["product", "search", "semi skimmed milk", "--page", "2"]
    )
    assert args.product_command == "search"
    assert args.keyword == "semi skimmed milk"
    assert args.page == 2


def test_parser_store_near_command() -> None:
    """Store near command parses coordinates."""
    args = build_parser().parse_args(
        ["store", "near", "--lat", "51.5", "--lon", "-0.12"]
    )
    assert args.command == "store"
    assert args.store_command == "near"
    assert args.lat == 51.5
    assert args.lon == -0.12


def test_parser_store_search_command() -> None:
    """Store search command parses store id and keyword."""
    args = build_parser().parse_args(["store", "search", "2665", "milk"])
    assert args.store_command == "search"
    assert args.store_id == "2665"
    assert args.keyword == "milk"


def test_parser_slots_list_delivery_command() -> None:
    """Slots list command parses delivery options."""
    args = build_parser().parse_args(
        ["slots", "list", "--type", "delivery", "--postcode", "SW1A1AA"]
    )
    assert args.command == "slots"
    assert args.slots_command == "list"
    assert args.slot_type is SlotType.DELIVERY
    assert args.postcode == "SW1A1AA"
    assert args.slot_type.api_value == "DELIVERY"


def test_parser_slots_list_collection_aliases() -> None:
    """Collection CLI aliases map to the click-and-collect API slot type."""
    args = build_parser().parse_args(["slots", "list", "--type", "click-and-collect"])
    assert args.slot_type is SlotType.COLLECTION
    assert args.slot_type.api_value == "CLICK_AND_COLLECT"


def test_parser_slots_reservation_command() -> None:
    """Slots reservation command is parsed."""
    args = build_parser().parse_args(["slots", "reservation"])
    assert args.slots_command == "reservation"


def test_parser_slots_reserve_command() -> None:
    """Slots reserve command parses slot and collection context."""
    args = build_parser().parse_args(
        [
            "slots",
            "reserve",
            "slot-123",
            "--type",
            "collection",
            "--location-uid",
            "location-123",
            "--no-context",
        ]
    )
    assert args.slots_command == "reserve"
    assert args.slot_uid == "slot-123"
    assert args.slot_type is SlotType.COLLECTION
    assert args.location_uid == "location-123"
    assert args.no_context is True


def test_parser_slots_validate_and_context_commands() -> None:
    """Slots validate and context commands are registered."""
    validate = build_parser().parse_args(
        ["slots", "validate", "--order-uid", "order-123"]
    )
    context = build_parser().parse_args(["slots", "context"])
    assert validate.slots_command == "validate"
    assert validate.order_uid == "order-123"
    assert context.slots_command == "context"


def test_parser_raw_option() -> None:
    """The raw flag selects JSON-array output and excludes --json."""
    args = parse_args(["product", "show", "abc-123", "--raw"])
    assert args.raw is True
    assert args.json is False
    with pytest.raises(SystemExit):
        parse_args(["--json", "--raw", "product", "show", "abc-123"])


def test_emit_product_raw_preserves_attributes(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Raw product output is a one-element array of every public attribute."""
    product = Product(
        product_uid="123",
        name="Milk",
        is_alcoholic=True,
        image_url="https://example.test/milk.jpg",
        retail_price=Price(price=1.25, measure="ea", measure_amount=1),
        reviews=ProductReviews(
            is_enabled=True,
            product_uid="123",
            total=4,
            average_rating=4.5,
        ),
    )
    emit_product(product, as_json=False, raw=True)
    payload = json.loads(capsys.readouterr().out)
    expected = product.to_dict()
    expected.pop("brand")
    assert payload == [expected]
    assert payload[0]["is_alcoholic"] is True
    assert payload[0]["retail_price"]["price"] == 1.25
    assert payload[0]["promotions"] == []
    assert "_api" not in payload[0]


def test_emit_product_list_raw_is_an_array(capsys: pytest.CaptureFixture[str]) -> None:
    """Raw list output is the product records, without pagination metadata."""
    products = ProductList(
        products=[
            Product(product_uid="1", name="Bread"),
            Product(product_uid="2", name="Milk"),
        ],
        controls=PageControls(
            total_record_count=2,
            returned_record_count=2,
            active_page=1,
            first_page=1,
            last_page=1,
            page_size=20,
        ),
    )
    emit_product_list(products, as_json=False, raw=True, title="Search")
    payload = json.loads(capsys.readouterr().out)
    assert [item["product_uid"] for item in payload] == ["1", "2"]
    assert "controls" not in payload[0]
    assert payload[0]["eans"] == []


def test_emit_slot_week_raw_keeps_slot_and_day_attributes(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Raw slot output is an array of slots with the day they belong to."""
    week = SlotWeek(
        slot_type=SlotType.DELIVERY,
        days=[
            SlotDay(
                date="2026-09-21",
                day_label="Monday",
                slots=[
                    DeliverySlot(
                        slot_uid="slot-1",
                        start_time="09:00",
                        end_time="10:00",
                        price=0.5,
                        unqualified_price=1.0,
                        is_available=True,
                        status="AVAILABLE",
                        slot_type="delivery",
                    )
                ],
            )
        ],
    )
    emit_slot_week(week, as_json=False, raw=True)
    payload = json.loads(capsys.readouterr().out)
    assert payload == [
        {
            "slot_uid": "slot-1",
            "start_time": "09:00",
            "end_time": "10:00",
            "price": 0.5,
            "unqualified_price": 1.0,
            "is_available": True,
            "status": "AVAILABLE",
            "slot_type": "delivery",
            "date": "2026-09-21",
            "day_label": "Monday",
        }
    ]
