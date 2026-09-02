"""Tests for the command-line interface."""

from __future__ import annotations

from pysainsburys.cli import build_parser, default_session_path
from pysainsburys.enum import SlotType


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
