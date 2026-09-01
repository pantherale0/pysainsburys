"""Catalogue product CLI commands."""

from __future__ import annotations

import argparse

from ._args import add_pagination_options
from .output import emit_product, emit_product_list
from .session import with_public_client


async def cmd_show(args: argparse.Namespace) -> int:
    """Fetch and print a product."""
    client = await with_public_client()
    try:
        product = await client.get_product(args.product_uid)
        emit_product(product, as_json=args.json)
    finally:
        await client.close()
    return 0


async def cmd_search(args: argparse.Namespace) -> int:
    """Search online catalogue products by keyword."""
    client = await with_public_client()
    try:
        products = await client.search_products(
            args.keyword,
            page_number=args.page,
            page_size=args.page_size,
        )
        emit_product_list(
            products,
            as_json=args.json,
            title=f"Search: {args.keyword}",
        )
    finally:
        await client.close()
    return 0


def register(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    """Register ``product`` commands."""
    parser = subparsers.add_parser("product", help="Catalogue product commands")
    product_sub = parser.add_subparsers(dest="product_command", required=True)

    show = product_sub.add_parser("show", help="Show a product by uid")
    show.add_argument("product_uid", help="Product UID")
    show.set_defaults(handler=cmd_show)

    search = product_sub.add_parser("search", help="Search products by keyword")
    search.add_argument("keyword", help="Search keyword")
    add_pagination_options(search)
    search.set_defaults(handler=cmd_search)
