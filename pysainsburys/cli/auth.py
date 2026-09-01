"""Authentication CLI commands."""

from __future__ import annotations

import argparse
import getpass
import sys
from collections.abc import Awaitable, Callable
from pathlib import Path

from ..auth import GOLAuth
from ..exceptions import MFARequiredError, SessionRequiredError
from .output import emit_json
from .session import ensure_session_parent, load_auth, with_client

CommandHandler = Callable[[argparse.Namespace], Awaitable[int]]


def pending_login_path(session_path: Path) -> Path:
    """Return the default path for in-progress login state."""
    return session_path.with_name(f"{session_path.stem}.pending.json")


async def cmd_url(args: argparse.Namespace) -> int:
    """Print a browser authorization URL."""
    auth = GOLAuth()
    try:
        url = await auth.send_login_request()
    finally:
        await auth.close()
    if args.json:
        emit_json({"authorization_url": url})
    else:
        print(url)
    return 0


async def cmd_finish(args: argparse.Namespace) -> int:
    """Complete browser login and persist the session."""
    session_path = Path(args.session)
    auth = GOLAuth()
    try:
        await auth.finish_login(args.redirect)
        ensure_session_parent(session_path)
        auth.save_session_file(str(session_path))
    finally:
        await auth.close()
    if args.json:
        emit_json({"session": str(session_path), "user_id": auth.user_id})
    else:
        print(f"Session saved to {session_path}")
    return 0


async def complete_mfa_login(
    auth: GOLAuth,
    args: argparse.Namespace,
    *,
    session_path: Path,
) -> int:
    """Prompt for or accept an MFA code and finish sign-in."""
    if args.mfa_code:
        mfa_code = args.mfa_code
    elif sys.stdin.isatty():
        if not args.json:
            print("Verification code sent. Check your email or phone.")
        mfa_code = input("MFA code: ").strip()
    else:
        pending_path = pending_login_path(session_path)
        ensure_session_parent(pending_path)
        auth.save_pending_login(str(pending_path))
        if args.json:
            emit_json(
                {
                    "mfa_required": True,
                    "pending_login": str(pending_path),
                }
            )
        else:
            print(
                f"Verification code sent. Complete sign-in with:\n"
                f"  pysainsburys auth mfa CODE --pending {pending_path}",
                file=sys.stderr,
            )
        return 2

    await auth.send_mfa_request(mfa_code, exchange_commerce=True)
    ensure_session_parent(session_path)
    auth.save_session_file(str(session_path))
    pending_path = pending_login_path(session_path)
    if pending_path.is_file():
        pending_path.unlink()
    if args.json:
        emit_json({"session": str(session_path), "user_id": auth.user_id})
    else:
        print(f"Signed in. Session saved to {session_path}")
    return 0


async def cmd_login(args: argparse.Namespace) -> int:
    """Sign in with credentials and persist the session."""
    session_path = Path(args.session)
    username = args.username
    password = args.password
    if username is None:
        username = input("Email: ").strip()
    if password is None:
        password = getpass.getpass("Password: ")

    auth = GOLAuth()
    try:
        try:
            await auth.login(username, password, exchange_commerce=True)
        except MFARequiredError:
            return await complete_mfa_login(auth, args, session_path=session_path)
        ensure_session_parent(session_path)
        auth.save_session_file(str(session_path))
    finally:
        await auth.close()

    if args.json:
        emit_json({"session": str(session_path), "user_id": auth.user_id})
    else:
        print(f"Signed in. Session saved to {session_path}")
    return 0


async def cmd_mfa(args: argparse.Namespace) -> int:
    """Complete sign-in with an MFA verification code."""
    session_path = Path(args.session)
    pending_path = (
        Path(args.pending)
        if args.pending is not None
        else pending_login_path(session_path)
    )
    if not pending_path.is_file():
        msg = (
            f"No pending login at {pending_path}. Run `pysainsburys auth login` first."
        )
        raise SessionRequiredError(msg)

    auth = GOLAuth.from_pending_login_file(str(pending_path))
    try:
        await auth.send_mfa_request(args.code, exchange_commerce=True)
        ensure_session_parent(session_path)
        auth.save_session_file(str(session_path))
        pending_path.unlink(missing_ok=True)
    finally:
        await auth.close()

    if args.json:
        emit_json({"session": str(session_path), "user_id": auth.user_id})
    else:
        print(f"Signed in. Session saved to {session_path}")
    return 0


async def cmd_resend_mfa(args: argparse.Namespace) -> int:
    """Resend the MFA verification code for a pending login."""
    pending_path = (
        Path(args.pending)
        if args.pending is not None
        else pending_login_path(Path(args.session))
    )
    if not pending_path.is_file():
        msg = (
            f"No pending login at {pending_path}. Run `pysainsburys auth login` first."
        )
        raise SessionRequiredError(msg)

    auth = GOLAuth.from_pending_login_file(str(pending_path))
    try:
        await auth.request_mfa_code()
        auth.save_pending_login(str(pending_path))
    finally:
        await auth.close()

    if args.json:
        emit_json({"pending_login": str(pending_path), "mfa_sent": True})
    else:
        print(f"Verification code resent. Pending login: {pending_path}")
    return 0


async def cmd_refresh(args: argparse.Namespace) -> int:
    """Refresh the commerce session using the saved OAuth access token."""
    session_path = Path(args.session)
    auth = load_auth(args)
    try:
        await auth.refresh_commerce_session()
        auth.save_session_file(str(session_path))
    finally:
        await auth.close()

    if args.json:
        emit_json({"session": str(session_path), "user_id": auth.user_id})
    else:
        print(f"Commerce session refreshed. Session saved to {session_path}")
    return 0


async def cmd_logout(args: argparse.Namespace) -> int:
    """End the remote commerce session."""
    client = await with_client(args)
    try:
        await client.api.logout()
    finally:
        await client.close()

    if args.json:
        emit_json({"logged_out": True})
    else:
        print("Logged out.")
    return 0


def register(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    """Register ``auth`` commands."""
    parser = subparsers.add_parser("auth", help="Authentication commands")
    auth_sub = parser.add_subparsers(dest="auth_command", required=True)

    auth_url = auth_sub.add_parser("url", help="Print a browser authorization URL")
    auth_url.set_defaults(handler=cmd_url)

    auth_finish = auth_sub.add_parser(
        "finish",
        help="Complete browser login from a redirect URL or code",
    )
    auth_finish.add_argument(
        "redirect",
        help="Redirect URL or raw authorization code",
    )
    auth_finish.set_defaults(handler=cmd_finish)

    auth_login = auth_sub.add_parser("login", help="Sign in with email and password")
    auth_login.add_argument("-u", "--username", help="Account email address")
    auth_login.add_argument("-p", "--password", help="Account password")
    auth_login.add_argument(
        "-m",
        "--mfa-code",
        help="MFA code (only after a verification code has been sent)",
    )
    auth_login.set_defaults(handler=cmd_login)

    auth_mfa = auth_sub.add_parser(
        "mfa",
        help="Complete sign-in with an MFA code from a pending login",
    )
    auth_mfa.add_argument("code", help="MFA verification code")
    auth_mfa.add_argument(
        "--pending",
        type=Path,
        help="Pending login state file (default: <session>.pending.json)",
    )
    auth_mfa.set_defaults(handler=cmd_mfa)

    auth_resend = auth_sub.add_parser(
        "resend-mfa",
        help="Resend the MFA verification code for a pending login",
    )
    auth_resend.add_argument(
        "--pending",
        type=Path,
        help="Pending login state file (default: <session>.pending.json)",
    )
    auth_resend.set_defaults(handler=cmd_resend_mfa)

    auth_refresh = auth_sub.add_parser(
        "refresh",
        help="Refresh the commerce session from the saved OAuth access token",
    )
    auth_refresh.set_defaults(handler=cmd_refresh)

    auth_logout = auth_sub.add_parser("logout", help="End the remote commerce session")
    auth_logout.set_defaults(handler=cmd_logout)
