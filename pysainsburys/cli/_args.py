"""Shared argparse helpers."""

from __future__ import annotations

import argparse


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
