"""Order history CLI commands."""

from __future__ import annotations

import argparse

from ._args import add_pagination_options
from .output import emit_order, emit_order_list, emit_order_status
from .session import with_client


async def cmd_list(args: argparse.Namespace) -> int:
    """Fetch and print recent orders."""
    client = await with_client(args)
    try:
        customer = await client.get_customer()
        orders = await customer.orders.fetch(
            page_number=args.page,
            page_size=args.page_size,
        )
        emit_order_list(orders, as_json=args.json)
    finally:
        await client.close()
    return 0


async def cmd_show(args: argparse.Namespace) -> int:
    """Fetch and print a single order."""
    client = await with_client(args)
    try:
        customer = await client.get_customer()
        order = await customer.orders[args.order_id].fetch()
        emit_order(order, as_json=args.json)
    finally:
        await client.close()
    return 0


async def cmd_status(args: argparse.Namespace) -> int:
    """Fetch and print the active order status."""
    client = await with_client(args)
    try:
        customer = await client.get_customer()
        if args.order_id:
            status = await customer.orders[args.order_id].status()
        else:
            await customer.orders.fetch(page_number=1, page_size=1)
            status = await customer.orders.latest.status()
        emit_order_status(status, as_json=args.json)
    finally:
        await client.close()
    return 0


def register(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    """Register ``orders`` commands."""
    parser = subparsers.add_parser("orders", help="Order history commands")
    orders_sub = parser.add_subparsers(dest="orders_command", required=True)

    list_cmd = orders_sub.add_parser("list", help="List recent orders")
    add_pagination_options(list_cmd)
    list_cmd.set_defaults(handler=cmd_list)

    show = orders_sub.add_parser("show", help="Show a single order")
    show.add_argument("order_id", help="Order ID")
    show.set_defaults(handler=cmd_show)

    status = orders_sub.add_parser(
        "status",
        help="Show order status (latest order when no id is given)",
    )
    status.add_argument(
        "order_id",
        nargs="?",
        help="Order ID (defaults to the latest order)",
    )
    status.set_defaults(handler=cmd_status)
