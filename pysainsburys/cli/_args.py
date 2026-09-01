"""Shared argparse helpers."""

from __future__ import annotations

import argparse

from ..enum import AuthChannel


def parse_channel(value: str) -> AuthChannel:
    """Parse an auth channel CLI value."""
    normalized = value.strip().lower()
    if normalized in {"web", "desktop"}:
        return AuthChannel.WEB
    if normalized in {"android", "app", "mobile"}:
        return AuthChannel.ANDROID
    msg = f"Unknown auth channel: {value!r} (expected web or android)"
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
