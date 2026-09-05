"""Delivery and collection slot CLI commands."""

from __future__ import annotations

import argparse

from ..enum import SlotType
from ._args import parse_slot_type
from .output import emit_location_context, emit_slot_reservation, emit_slot_week
from .session import with_client


async def cmd_list(args: argparse.Namespace) -> int:
    """List available delivery or collection slots."""
    client = await with_client(args)
    try:
        customer = await client.get_customer()
        slot_type = args.slot_type
        if slot_type is SlotType.DELIVERY:
            week = await customer.slots.list_delivery(
                postcode=args.postcode,
                store_identifier=args.store,
                week_start_date=args.week_start,
                use_location_context=not args.no_context,
            )
        else:
            week = await customer.slots.list_collection(
                store_identifier=args.store,
                location_uid=args.location_uid,
                week_start_date=args.week_start,
                use_location_context=not args.no_context,
            )
        emit_slot_week(week, as_json=args.json)
    finally:
        await client.close()
    return 0


async def cmd_reservation(args: argparse.Namespace) -> int:
    """Show the current slot reservation."""
    client = await with_client(args)
    try:
        customer = await client.get_customer()
        reservation = await customer.slots.fetch_reservation(
            order_uid=args.order_uid,
        )
        emit_slot_reservation(reservation, as_json=args.json)
    finally:
        await client.close()
    return 0


async def cmd_reserve(args: argparse.Namespace) -> int:
    """Reserve a delivery or collection slot."""
    client = await with_client(args)
    try:
        customer = await client.get_customer()
        reservation = await customer.slots.reserve(
            args.slot_uid,
            slot_type=args.slot_type,
            start_time=args.start,
            end_time=args.end,
            postcode=args.postcode,
            store_identifier=args.store,
            location_uid=args.location_uid,
            order_uid=args.order_uid,
            use_location_context=not args.no_context,
        )
        emit_slot_reservation(reservation, as_json=args.json)
    finally:
        await client.close()
    return 0


async def cmd_validate(args: argparse.Namespace) -> int:
    """Validate the current slot reservation."""
    client = await with_client(args)
    try:
        customer = await client.get_customer()
        reservation = await customer.slots.validate(order_uid=args.order_uid)
        emit_slot_reservation(reservation, as_json=args.json)
    finally:
        await client.close()
    return 0


async def cmd_context(args: argparse.Namespace) -> int:
    """Show the location context used for slot operations."""
    client = await with_client(args)
    try:
        customer = await client.get_customer()
        context = await customer.slots.fetch_location_context()
        emit_location_context(context, as_json=args.json)
    finally:
        await client.close()
    return 0


def register(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    """Register ``slots`` commands."""
    parser = subparsers.add_parser(
        "slots", help="Delivery and collection slot commands"
    )
    slots_sub = parser.add_subparsers(dest="slots_command", required=True)

    list_cmd = slots_sub.add_parser("list", help="List available slots")
    list_cmd.add_argument(
        "--type",
        dest="slot_type",
        type=parse_slot_type,
        default=SlotType.DELIVERY,
        help="Slot type to list (delivery or collection)",
    )
    list_cmd.add_argument(
        "--postcode",
        help="Delivery postcode (defaults from location context)",
    )
    list_cmd.add_argument(
        "--store",
        help="Fulfilment store identifier (defaults from location context)",
    )
    list_cmd.add_argument(
        "--location-uid",
        help="Click-and-collect location uid (collection only)",
    )
    list_cmd.add_argument(
        "--week-start",
        help="ISO date for the week to list (defaults to current week Monday)",
    )
    list_cmd.add_argument(
        "--no-context",
        action="store_true",
        help="Do not pre-fill missing values from location context",
    )
    list_cmd.set_defaults(handler=cmd_list)

    reservation = slots_sub.add_parser(
        "reservation",
        help="Show the current slot reservation",
    )
    reservation.add_argument(
        "--order-uid",
        help="Optional order uid when amending an order",
    )
    reservation.set_defaults(handler=cmd_reservation)

    reserve = slots_sub.add_parser(
        "reserve",
        help="Reserve a slot or replace the current reservation",
    )
    reserve.add_argument("slot_uid", help="Slot uid returned by slots list")
    reserve.add_argument(
        "--type",
        dest="slot_type",
        type=parse_slot_type,
        default=SlotType.DELIVERY,
        help="Slot type (delivery or collection)",
    )
    reserve.add_argument("--start", help="Slot start timestamp (ISO-8601)")
    reserve.add_argument("--end", help="Slot end timestamp (ISO-8601)")
    reserve.add_argument("--postcode", help="Delivery postcode")
    reserve.add_argument("--store", help="Fulfilment store identifier")
    reserve.add_argument(
        "--location-uid",
        help="Click-and-collect location uid",
    )
    reserve.add_argument(
        "--order-uid",
        help="Optional order uid when amending an order",
    )
    reserve.add_argument(
        "--no-context",
        action="store_true",
        help="Do not pre-fill missing values from location context",
    )
    reserve.set_defaults(handler=cmd_reserve)

    validate = slots_sub.add_parser(
        "validate",
        help="Validate the current slot reservation",
    )
    validate.add_argument(
        "--order-uid",
        help="Optional order uid when amending an order",
    )
    validate.set_defaults(handler=cmd_validate)

    context = slots_sub.add_parser(
        "context",
        help="Show slot location context",
    )
    context.set_defaults(handler=cmd_context)
