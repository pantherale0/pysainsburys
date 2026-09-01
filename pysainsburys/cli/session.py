"""Session loading and client factories for CLI commands."""

from __future__ import annotations

import argparse
from pathlib import Path

from .. import Sainsburys
from ..auth import GOLAuth
from ..exceptions import SessionRequiredError

DEFAULT_SESSION_PATH = Path.home() / ".config" / "pysainsburys" / "session.json"


def default_session_path() -> Path:
    """Return the default session file path."""
    return DEFAULT_SESSION_PATH


def ensure_session_parent(path: Path) -> None:
    """Create parent directories for a session file when needed."""
    path.parent.mkdir(parents=True, exist_ok=True)


def load_auth(args: argparse.Namespace) -> GOLAuth:
    """Load authentication state from the configured session file."""
    session_path = Path(args.session)
    if not session_path.is_file():
        msg = (
            f"No session at {session_path}. "
            "Run `pysainsburys auth login` or `pysainsburys auth finish` first."
        )
        raise SessionRequiredError(msg)
    return GOLAuth.from_session_file(str(session_path))


async def with_client(args: argparse.Namespace) -> Sainsburys:
    """Create a Sainsburys client from the configured session."""
    return Sainsburys(load_auth(args))


async def with_public_client() -> Sainsburys:
    """Create a client for public endpoints that do not require login."""
    return Sainsburys(GOLAuth())
