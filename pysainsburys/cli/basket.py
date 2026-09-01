"""Basket CLI commands."""

from __future__ import annotations

import argparse

from .output import emit_basket, emit_json
from .session import with_client


async def cmd_show(args: argparse.Namespace) -> int:
    """Fetch and print the current basket."""
    client = await with_client(args)
    try:
        customer = await client.get_customer()
        basket = await customer.basket.fetch()
        emit_basket(basket, as_json=args.json)
    finally:
        await client.close()
    return 0


async def cmd_add(args: argparse.Namespace) -> int:
    """Add an item to the basket."""
    client = await with_client(args)
    try:
        customer = await client.get_customer()
        basket = await customer.basket.add(
            args.product_uid,
            args.quantity,
            uom=args.uom,
            selected_catchweight=args.catchweight,
        )
        emit_basket(basket, as_json=args.json)
    finally:
        await client.close()
    return 0


async def cmd_set(args: argparse.Namespace) -> int:
    """Set the absolute quantity for a basket line."""
    client = await with_client(args)
    try:
        customer = await client.get_customer()
        basket = await customer.basket.set_quantity(
            args.product_uid,
            args.quantity,
            item_uid=args.item_uid,
            uom=args.uom,
            selected_catchweight=args.catchweight,
        )
        emit_basket(basket, as_json=args.json)
    finally:
        await client.close()
    return 0


async def cmd_remove(args: argparse.Namespace) -> int:
    """Remove a product from the basket."""
    client = await with_client(args)
    try:
        customer = await client.get_customer()
        basket = await customer.basket.remove(
            args.product_uid,
            item_uid=args.item_uid,
            force_delete=args.force,
        )
        emit_basket(basket, as_json=args.json)
    finally:
        await client.close()
    return 0


async def cmd_clear(args: argparse.Namespace) -> int:
    """Remove all items from the basket."""
    client = await with_client(args)
    try:
        customer = await client.get_customer()
        await customer.basket.clear()
    finally:
        await client.close()

    if args.json:
        emit_json({"cleared": True})
    else:
        print("Basket cleared.")
    return 0


def _add_basket_item_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--uom",
        default="ea",
        help="Unit of measure sent to the API (default: ea)",
    )
    parser.add_argument(
        "--catchweight",
        metavar="UID",
        help="Catchweight option uid for variable-weight products",
    )


def register(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    """Register ``basket`` commands."""
    parser = subparsers.add_parser("basket", help="Basket commands")
    basket_sub = parser.add_subparsers(dest="basket_command", required=True)

    show = basket_sub.add_parser("show", help="Show the current basket")
    show.set_defaults(handler=cmd_show)

    add = basket_sub.add_parser("add", help="Add a product to the basket")
    add.add_argument("product_uid", help="Product UID to add")
    add.add_argument(
        "--quantity",
        type=float,
        default=1.0,
        help="Quantity to add (default: 1)",
    )
    _add_basket_item_options(add)
    add.set_defaults(handler=cmd_add)

    set_qty = basket_sub.add_parser(
        "set",
        help="Set the absolute basket quantity for a product",
    )
    set_qty.add_argument("product_uid", help="Product UID")
    set_qty.add_argument("quantity", type=float, help="Target quantity (0 to remove)")
    set_qty.add_argument(
        "--item-uid",
        help="Basket line item uid from `basket show`",
    )
    _add_basket_item_options(set_qty)
    set_qty.set_defaults(handler=cmd_set)

    remove = basket_sub.add_parser("remove", help="Remove a product from the basket")
    remove.add_argument("product_uid", help="Product UID to remove")
    remove.add_argument(
        "--item-uid",
        help="Basket line item uid from `basket show`",
    )
    remove.add_argument(
        "--force",
        action="store_true",
        help="Accepted for compatibility; removals use basket update",
    )
    remove.set_defaults(handler=cmd_remove)

    delete = basket_sub.add_parser(
        "del",
        help="Alias for remove",
        aliases=["delete"],
    )
    delete.add_argument("product_uid", help="Product UID to remove")
    delete.add_argument(
        "--item-uid",
        help="Basket line item uid from `basket show`",
    )
    delete.add_argument(
        "--force",
        action="store_true",
        help="Accepted for compatibility; removals use basket update",
    )
    delete.set_defaults(handler=cmd_remove)

    clear = basket_sub.add_parser("clear", help="Remove all items from the basket")
    clear.set_defaults(handler=cmd_clear)
