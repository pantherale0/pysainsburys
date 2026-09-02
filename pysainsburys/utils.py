"""Shared helpers for Sainsbury's GOL API."""

from __future__ import annotations

import asyncio
import base64
import hashlib
import json
import secrets
import urllib.parse
from collections.abc import Callable
from typing import Any

from .const import AUTH_BASE_URL


def build_wc_auth_token(user_id: str, wc_trusted_token: str) -> str:
    """Build the ``WCAuthToken`` header value from raw token parts."""
    return urllib.parse.quote(f"{user_id},{wc_trusted_token}", safe="")


def normalize_wc_auth_token(
    *,
    user_id: str | None,
    wc_trusted_token: str | None,
    wc_auth_token: str | None = None,
) -> str | None:
    """Return a ``WCAuthToken`` header value from session fields."""
    if wc_auth_token:
        if "%252C" in wc_auth_token and wc_trusted_token:
            wc_auth_token = None
        else:
            return wc_auth_token
    if not wc_trusted_token:
        return None
    if user_id and (
        wc_trusted_token.startswith(f"{user_id}%2C")
        or wc_trusted_token.startswith(f"{user_id},")
    ):
        return wc_trusted_token
    if user_id:
        return build_wc_auth_token(user_id, wc_trusted_token)
    return wc_trusted_token


def cookies_to_header(cookies: dict[str, str]) -> str:
    """Serialize a cookie mapping to a ``Cookie`` header string."""
    return "; ".join(f"{name}={value}" for name, value in cookies.items())


def parse_cookie_header(cookie_header: str) -> dict[str, str]:
    """Parse a ``Cookie`` header string into a mapping."""
    cookies: dict[str, str] = {}
    for part in cookie_header.split(";"):
        part = part.strip()
        if not part or "=" not in part:
            continue
        name, value = part.split("=", 1)
        cookies[name.strip()] = value.strip()
    return cookies


def is_awaitable(value: object) -> bool:
    """Return True when *value* is awaitable."""
    return callable(getattr(value, "__await__", None))


def _read_session_file(path: str) -> dict[str, Any]:
    """Load a session export JSON file from disk."""
    with open(path, encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        msg = "Session file must contain a JSON object."
        raise ValueError(msg)
    return data


def _write_session_file(path: str, data: dict[str, Any]) -> None:
    """Write a session export JSON file to disk."""
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2, sort_keys=True)
        handle.write("\n")


async def load_session_file(path: str) -> dict[str, Any]:
    """Load a session export JSON file without blocking the event loop."""
    return await asyncio.to_thread(_read_session_file, path)


async def save_session_file(path: str, data: dict[str, Any]) -> None:
    """Write a session export JSON file without blocking the event loop."""
    await asyncio.to_thread(_write_session_file, path, data)


def call_or_await(callback: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
    """Invoke *callback*, awaiting it when it returns a coroutine."""
    result = callback(*args, **kwargs)
    if is_awaitable(result):
        return result
    return result


def random_string(min_length: int, max_length: int) -> str:
    """Return a URL-safe random string within the requested length bounds."""
    length = secrets.randbelow(max_length - min_length + 1) + min_length
    return secrets.token_urlsafe(length)[:length]


def build_code_challenge(code_verifier: str) -> str:
    """Build a PKCE S256 code challenge from a verifier."""
    digest = hashlib.sha256(code_verifier.encode("ascii")).digest()
    return base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")


def decode_oauth_redirect(redirect_url: str) -> tuple[str | None, str | None]:
    """Extract authorization ``code`` and ``state`` from a redirect URL."""
    parsed = urllib.parse.urlparse(redirect_url)
    params = urllib.parse.parse_qs(parsed.query, keep_blank_values=True)
    if parsed.fragment:
        params.update(urllib.parse.parse_qs(parsed.fragment, keep_blank_values=True))
    code = params.get("code", [None])[0]
    state = params.get("state", [None])[0]
    return code, state


def parse_authorization_input(value: str) -> tuple[str | None, str | None]:
    """Parse an authorization code or full redirect URL."""
    value = value.strip()
    if "://" in value or value.startswith("?"):
        return decode_oauth_redirect(value)
    return value, None


def parse_query_param(url: str, param: str) -> str | None:
    """Return a single query parameter from a URL."""
    parsed = urllib.parse.urlparse(url)
    values = urllib.parse.parse_qs(parsed.query).get(param)
    if not values:
        if parsed.fragment:
            values = urllib.parse.parse_qs(parsed.fragment).get(param)
    if not values:
        return None
    return values[0]


def resolve_redirect_url(location: str, *, base_url: str = AUTH_BASE_URL) -> str:
    """Resolve a relative redirect location against the identity host."""
    if location.startswith(("http://", "https://")):
        return location
    if location.startswith("/"):
        return f"{base_url.rstrip('/')}{location}"
    return f"{base_url.rstrip('/')}/{location.lstrip('/')}"


def login_challenge_from_url(url: str) -> str | None:
    """Extract a Hydra ``login_challenge`` query parameter."""
    return parse_query_param(url, "login_challenge")


def identity_url_path(url: str) -> str:
    """Return the path of an identity URL without a trailing slash."""
    return urllib.parse.urlparse(url).path.rstrip("/")


def is_identity_mfa_url(url: str) -> bool:
    """Return whether *url* is the identity MFA page, ignoring query strings."""
    return identity_url_path(url).endswith("/gol/login/mfa")


def is_identity_login_url(url: str) -> bool:
    """Return whether *url* is the identity login page, ignoring query strings."""
    path = identity_url_path(url)
    return path.endswith("/gol/login") and not path.endswith("/gol/login/mfa")


def identity_error_code(url: str) -> str | None:
    """Return an identity ``error_code`` query parameter when present."""
    return parse_query_param(url, "error_code")
