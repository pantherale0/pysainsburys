"""Favourites CLI commands."""

from __future__ import annotations

import argparse

from ._args import add_pagination_options
from .output import emit_json, emit_product_list
from .session import with_client


async def cmd_list(args: argparse.Namespace) -> int:
    """Fetch and print favourite products."""
    client = await with_client(args)
    try:
        customer = await client.get_customer()
        favourites = await customer.favourites.fetch(
            page_number=args.page,
            page_size=args.page_size,
        )
        emit_product_list(favourites, as_json=args.json, title="Favourites")
    finally:
        await client.close()
    return 0


async def cmd_add(args: argparse.Namespace) -> int:
    """Add a product to favourites."""
    client = await with_client(args)
    try:
        customer = await client.get_customer()
        await customer.favourites.add(args.product_uid)
    finally:
        await client.close()

    if args.json:
        emit_json({"product_uid": args.product_uid, "added": True})
    else:
        print(f"Added {args.product_uid} to favourites.")
    return 0


async def cmd_remove(args: argparse.Namespace) -> int:
    """Remove a product from favourites."""
    client = await with_client(args)
    try:
        customer = await client.get_customer()
        await customer.favourites.remove(args.product_uid)
    finally:
        await client.close()

    if args.json:
        emit_json({"product_uid": args.product_uid, "removed": True})
    else:
        print(f"Removed {args.product_uid} from favourites.")
    return 0


def register(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    """Register ``favourites`` commands."""
    parser = subparsers.add_parser("favourites", help="Favourite product commands")
    favourites_sub = parser.add_subparsers(dest="favourites_command", required=True)

    list_cmd = favourites_sub.add_parser("list", help="List favourite products")
    add_pagination_options(list_cmd)
    list_cmd.set_defaults(handler=cmd_list)

    add = favourites_sub.add_parser("add", help="Add a product to favourites")
    add.add_argument("product_uid", help="Product UID to add")
    add.set_defaults(handler=cmd_add)

    remove = favourites_sub.add_parser(
        "remove",
        help="Remove a product from favourites",
    )
    remove.add_argument("product_uid", help="Product UID to remove")
    remove.set_defaults(handler=cmd_remove)
