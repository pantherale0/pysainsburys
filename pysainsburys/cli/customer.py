"""Customer profile CLI commands."""

from __future__ import annotations

import argparse

from .output import emit_customer
from .session import with_client


async def cmd_show(args: argparse.Namespace) -> int:
    """Fetch and print the customer profile."""
    client = await with_client(args)
    try:
        customer = await client.get_customer()
        emit_customer(customer, as_json=args.json)
    finally:
        await client.close()
    return 0


def register(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    """Register ``customer`` commands."""
    parser = subparsers.add_parser("customer", help="Customer profile commands")
    customer_sub = parser.add_subparsers(dest="customer_command", required=True)

    show = customer_sub.add_parser("show", help="Show the customer profile")
    show.set_defaults(handler=cmd_show)
