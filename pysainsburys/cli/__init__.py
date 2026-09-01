"""
Command-line interface for pysainsburys.

Command groups mirror the library layout:

* :mod:`pysainsburys.cli.auth` — authentication
* :mod:`pysainsburys.cli.customer` — customer profile
* :mod:`pysainsburys.cli.basket` — basket operations
* :mod:`pysainsburys.cli.favourites` — favourite products
* :mod:`pysainsburys.cli.orders` — order history and status
* :mod:`pysainsburys.cli.slots` — delivery and collection slots
* :mod:`pysainsburys.cli.nectar` — Nectar offers and Your Nectar Prices
* :mod:`pysainsburys.cli.product` — catalogue search and lookup
* :mod:`pysainsburys.cli.store` — stores and in-store product search
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from collections.abc import Awaitable, Callable
from pathlib import Path

from .._version import __version__
from ..exceptions import (
    AuthError,
    BrowserLoginRequiredError,
    HttpException,
    SessionRequiredError,
)
from . import auth, basket, customer, favourites, nectar, orders, product, slots, store
from .session import DEFAULT_SESSION_PATH, default_session_path

CommandHandler = Callable[[argparse.Namespace], Awaitable[int]]

__all__ = [
    "build_parser",
    "default_session_path",
    "main",
    "run_command",
]


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser."""
    parser = argparse.ArgumentParser(
        prog="pysainsburys",
        description="Sainsbury's Groceries Online command-line client.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    parser.add_argument(
        "--session",
        type=Path,
        default=default_session_path(),
        help=f"Session file path (default: {DEFAULT_SESSION_PATH})",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit machine-readable JSON output",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable debug logging",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    auth.register(subparsers)
    customer.register(subparsers)
    basket.register(subparsers)
    favourites.register(subparsers)
    orders.register(subparsers)
    slots.register(subparsers)
    nectar.register(subparsers)
    product.register(subparsers)
    store.register(subparsers)

    return parser


async def run_command(args: argparse.Namespace) -> int:
    """Dispatch a parsed command."""
    handler = getattr(args, "handler", None)
    if handler is None:
        print("No command handler configured.", file=sys.stderr)
        return 1
    return await handler(args)


def main(argv: list[str] | None = None) -> int:
    """Run the CLI."""
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.WARNING)

    try:
        return asyncio.run(run_command(args))
    except (
        AuthError,
        BrowserLoginRequiredError,
        HttpException,
        SessionRequiredError,
        ValueError,
        TypeError,
    ) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("Interrupted.", file=sys.stderr)
        return 130
