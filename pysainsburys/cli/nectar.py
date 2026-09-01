"""Nectar offers CLI commands."""

from __future__ import annotations

import argparse

from .output import (
    emit_json,
    emit_nectar_offers,
    emit_nectar_search,
    emit_your_nectar_prices,
)
from .session import with_client


async def cmd_offers(args: argparse.Namespace) -> int:
    """Fetch and print Nectar bonus-point offers."""
    client = await with_client(args)
    try:
        customer = await client.get_customer()
        offers = await customer.nectar.fetch_offers()
        emit_nectar_offers(offers, as_json=args.json)
    finally:
        await client.close()
    return 0


async def cmd_prices(args: argparse.Namespace) -> int:
    """Fetch and print Your Nectar Price offers."""
    client = await with_client(args)
    try:
        customer = await client.get_customer()
        nectar = customer.nectar
        if args.unlock:
            result = await nectar.unlock_your_nectar_prices(
                offer_id=args.offer_id,
            )
            if args.json:
                emit_json(result.to_dict())
            else:
                print(f"Unlocked {len(result.updated_offer_ids)} offer(s).")
        prices = await nectar.enrich_your_nectar_prices()
        emit_your_nectar_prices(prices, as_json=args.json)
    finally:
        await client.close()
    return 0


async def cmd_search(args: argparse.Namespace) -> int:
    """Search Nectar offers and Your Nectar Prices."""
    client = await with_client(args)
    try:
        customer = await client.get_customer()
        results = await customer.nectar.search(args.query)
        emit_nectar_search(results, as_json=args.json)
    finally:
        await client.close()
    return 0


def register(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    """Register ``nectar`` commands."""
    parser = subparsers.add_parser("nectar", help="Nectar offers and prices")
    nectar_sub = parser.add_subparsers(dest="nectar_command", required=True)

    offers = nectar_sub.add_parser("offers", help="List Nectar bonus-point offers")
    offers.set_defaults(handler=cmd_offers)

    prices = nectar_sub.add_parser(
        "prices",
        help="List Your Nectar Price offers",
    )
    prices.add_argument(
        "--unlock",
        action="store_true",
        help="Unlock locked offers before listing",
    )
    prices.add_argument(
        "--offer-id",
        help="Specific offer id to unlock with --unlock",
    )
    prices.set_defaults(handler=cmd_prices)

    search = nectar_sub.add_parser(
        "search",
        help="Search offers and Your Nectar Prices by keyword",
    )
    search.add_argument("query", help="Search keyword")
    search.set_defaults(handler=cmd_search)
