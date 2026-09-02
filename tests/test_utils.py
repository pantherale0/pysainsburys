"""Tests for PKCE and OAuth redirect helpers."""

from pathlib import Path

import pytest

from pysainsburys.utils import (
    build_code_challenge,
    decode_oauth_redirect,
    identity_error_code,
    is_identity_login_url,
    is_identity_mfa_url,
    load_session_file,
    login_challenge_from_url,
    normalize_wc_auth_token,
    parse_authorization_input,
    random_string,
    resolve_redirect_url,
    save_session_file,
)


def test_build_code_challenge_is_urlsafe() -> None:
    """PKCE challenges are URL-safe base64 without padding."""
    verifier = random_string(43, 128)
    challenge = build_code_challenge(verifier)
    assert "=" not in challenge
    assert "+" not in challenge
    assert "/" not in challenge


def test_decode_oauth_redirect_from_query() -> None:
    """Authorization codes are parsed from query redirects."""
    code, state = decode_oauth_redirect(
        "https://www.sainsburys.co.uk/gol-ui/oauth/redirect?code=abc123&state=xyz"
    )
    assert code == "abc123"
    assert state == "xyz"


def test_parse_authorization_input_accepts_raw_code() -> None:
    """Raw authorization codes can be passed directly."""
    code, state = parse_authorization_input("abc123")
    assert code == "abc123"
    assert state is None


def test_login_challenge_from_url() -> None:
    """Hydra login challenges are parsed from login URLs."""
    url = (
        "https://account.sainsburys.co.uk/gol/login?"
        "login_challenge=378e6e59b38748b78f9c3d307420a67e"
    )
    assert login_challenge_from_url(url) == "378e6e59b38748b78f9c3d307420a67e"


def test_resolve_redirect_url() -> None:
    """Relative identity redirects resolve against the account host."""
    assert (
        resolve_redirect_url("/gol/login/mfa")
        == "https://account.sainsburys.co.uk/gol/login/mfa"
    )


def test_identity_login_and_mfa_urls_ignore_query_and_ui_prefix() -> None:
    """Login-ui paths with query strings are still recognised."""
    login = (
        "https://account.sainsburys.co.uk/login-ui/gol/login"
        "?login_challenge=abc&error_code=6053"
    )
    mfa = "https://account.sainsburys.co.uk/login-ui/gol/login/mfa?login_challenge=abc"
    assert is_identity_login_url(login) is True
    assert is_identity_mfa_url(login) is False
    assert identity_error_code(login) == "6053"
    assert is_identity_mfa_url(mfa) is True
    assert is_identity_login_url(mfa) is False
    assert is_identity_mfa_url("https://account.sainsburys.co.uk/gol/login/mfa")


def test_normalize_wc_auth_token_from_api_response() -> None:
    """API wc_trusted_token values are used directly as WCAuthToken headers."""
    token = normalize_wc_auth_token(
        user_id="682092082",
        wc_trusted_token="682092082%2Cabc123",
    )
    assert token == "682092082%2Cabc123"


@pytest.mark.asyncio
async def test_session_file_roundtrip(tmp_path: Path) -> None:
    """Session files round-trip through async load and save."""
    path = tmp_path / "session.json"
    payload = {"access_token": "oauth-token", "cookies": {"JSESSIONID": "abc"}}
    await save_session_file(str(path), payload)
    assert await load_session_file(str(path)) == payload


@pytest.mark.asyncio
async def test_load_session_file_requires_object(tmp_path: Path) -> None:
    """Session files must contain a JSON object."""
    path = tmp_path / "session.json"
    path.write_text("[]", encoding="utf-8")
    with pytest.raises(ValueError, match="JSON object"):
        await load_session_file(str(path))
