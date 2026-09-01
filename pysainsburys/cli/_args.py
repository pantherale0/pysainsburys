"""Shared argparse helpers."""

from __future__ import annotations

import argparse

from ..enum import SlotType


def parse_slot_type(value: str) -> SlotType:
    """Parse a slot type CLI value."""
    normalized = value.strip().lower().replace("-", "_")
    if normalized in {"delivery", "home_delivery", "hd"}:
        return SlotType.DELIVERY
    if normalized in {"collection", "click_and_collect", "cnc", "collect"}:
        return SlotType.COLLECTION
    msg = f"Unknown slot type: {value!r} (expected delivery or collection)"
    raise argparse.ArgumentTypeError(msg)


def add_pagination_options(parser: argparse.ArgumentParser) -> None:
    """Add shared pagination flags to a parser."""
    parser.add_argument(
        "--page",
        type=int,
        default=1,
        help="Page number (default: 1)",
    )
    parser.add_argument(
        "--page-size",
        type=int,
        default=20,
        help="Page size (default: 20)",
    )
