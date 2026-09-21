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

_GLOBAL_FLAGS = frozenset({"--json", "--raw", "-v", "--verbose"})
_GLOBAL_VALUE_FLAGS = frozenset({"--session"})

__all__ = [
    "build_parser",
    "default_session_path",
    "main",
    "parse_args",
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
    output = parser.add_mutually_exclusive_group()
    output.add_argument(
        "--json",
        action="store_true",
        help="Emit machine-readable JSON output",
    )
    output.add_argument(
        "--raw",
        action="store_true",
        help=(
            "Dump records to stdout as a JSON array, including every public attribute"
        ),
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


def normalize_argv(argv: list[str]) -> list[str]:
    """Move global flags in front of the subcommand so they parse in either position."""
    hoisted: list[str] = []
    rest: list[str] = []
    index = 0
    while index < len(argv):
        arg = argv[index]
        name, separator, _value = arg.partition("=")
        if arg in _GLOBAL_FLAGS:
            hoisted.append(arg)
        elif arg in _GLOBAL_VALUE_FLAGS:
            hoisted.append(arg)
            if index + 1 < len(argv):
                index += 1
                hoisted.append(argv[index])
        elif separator and name in _GLOBAL_VALUE_FLAGS:
            hoisted.append(arg)
        else:
            rest.append(arg)
        index += 1
    return [*hoisted, *rest]


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse CLI arguments, accepting global flags before or after the command."""
    if argv is None:
        argv = sys.argv[1:]
    return build_parser().parse_args(normalize_argv(argv))


async def run_command(args: argparse.Namespace) -> int:
    """Dispatch a parsed command."""
    handler = getattr(args, "handler", None)
    if handler is None:
        print("No command handler configured.", file=sys.stderr)
        return 1
    return await handler(args)


def main(argv: list[str] | None = None) -> int:
    """Run the CLI."""
    args = parse_args(argv)

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
