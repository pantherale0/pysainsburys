"""Store and in-store product CLI commands."""

from __future__ import annotations

import argparse

from ._args import add_pagination_options
from .output import (
    emit_store,
    emit_store_list,
    emit_store_product_list,
)
from .session import with_public_client


async def cmd_near(args: argparse.Namespace) -> int:
    """List stores near a latitude and longitude."""
    client = await with_public_client()
    try:
        stores = await client.find_stores(
            args.lat,
            args.lon,
            page=args.page,
            page_size=args.page_size,
        )
        emit_store_list(stores, as_json=args.json, title="Nearby stores")
    finally:
        await client.close()
    return 0


async def cmd_postcode(args: argparse.Namespace) -> int:
    """List click-and-collect stores near a postcode."""
    client = await with_public_client()
    try:
        stores = await client.find_stores_by_postcode(
            args.postcode,
            page_number=args.page,
        )
        emit_store_list(
            stores,
            as_json=args.json,
            title=f"Stores near {args.postcode}",
        )
    finally:
        await client.close()
    return 0


async def cmd_show(args: argparse.Namespace) -> int:
    """Show a single store."""
    client = await with_public_client()
    try:
        store = await client.get_store(args.store_id)
        emit_store(store, as_json=args.json)
    finally:
        await client.close()
    return 0


async def cmd_search(args: argparse.Namespace) -> int:
    """Search in-store products with aisle and stock."""
    client = await with_public_client()
    try:
        store = await client.get_store(args.store_id)
        products = await store.search_products(
            args.keyword,
            page=args.page,
            page_size=args.page_size,
        )
        emit_store_product_list(
            products,
            as_json=args.json,
            title=f"Store {args.store_id}: {args.keyword}",
        )
    finally:
        await client.close()
    return 0


def register(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    """Register ``store`` commands."""
    parser = subparsers.add_parser("store", help="Store lookup commands")
    store_sub = parser.add_subparsers(dest="store_command", required=True)

    near = store_sub.add_parser(
        "near",
        help="Find stores near a latitude and longitude",
    )
    near.add_argument("--lat", type=float, required=True, help="Latitude")
    near.add_argument("--lon", type=float, required=True, help="Longitude")
    add_pagination_options(near)
    near.set_defaults(handler=cmd_near)

    postcode = store_sub.add_parser(
        "postcode",
        help="Find click-and-collect stores near a postcode",
    )
    postcode.add_argument("postcode", help="UK postcode")
    postcode.add_argument(
        "--page",
        type=int,
        default=1,
        help="Page number (default: 1)",
    )
    postcode.set_defaults(handler=cmd_postcode)

    show = store_sub.add_parser("show", help="Show a store by id")
    show.add_argument("store_id", help="Product Finder store id")
    show.set_defaults(handler=cmd_show)

    search = store_sub.add_parser(
        "search",
        help="Search in-store products with aisle and stock",
    )
    search.add_argument("store_id", help="Product Finder store id")
    search.add_argument("keyword", help="Search keyword")
    add_pagination_options(search)
    search.set_defaults(handler=cmd_search)
