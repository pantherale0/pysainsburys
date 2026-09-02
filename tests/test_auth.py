"""Tests for authentication helpers."""

import json
import urllib.parse
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from pysainsburys.auth import GOLAuth
from pysainsburys.const import AUTH_BASE_URL, AUTH_CLIENT_ID, AUTH_SCOPE
from pysainsburys.exceptions import (
    AuthError,
    BrowserLoginRequiredError,
    ConfirmationRedirectError,
    MFARequiredError,
    SessionRequiredError,
)
from pysainsburys.utils import (
    build_wc_auth_token,
    cookies_to_header,
    parse_cookie_header,
)


def test_build_wc_auth_token() -> None:
    """WCAuthToken values are URL-encoded user_id,trusted_token pairs."""
    token = build_wc_auth_token("682092082", "mcvf-example-token")
    assert token == "682092082%2Cmcvf-example-token"


def test_cookie_header_roundtrip() -> None:
    """Cookie headers can be parsed and serialized."""
    cookies = {"JSESSIONID": "abc123", "WC_AUTHENTICATION_123": "xyz"}
    header = cookies_to_header(cookies)
    assert parse_cookie_header(header) == cookies


def test_from_dict_with_cookie_string() -> None:
    """Session exports accept Cookie header strings."""
    auth = GOLAuth.from_dict(
        {
            "access_token": "oauth-token",
            "wc_auth_token": "682092082%2Ctrusted",
            "cookies": "JSESSIONID=abc; WC_USERACTIVITY_123=def",
        }
    )
    assert auth.access_token == "oauth-token"
    assert auth.cookies["JSESSIONID"] == "abc"
    assert auth.cookies["WC_USERACTIVITY_123"] == "def"


def test_from_dict_builds_wc_auth_token_from_parts() -> None:
    """WCAuthToken is derived from user_id and wc_trusted_token when omitted."""
    auth = GOLAuth.from_dict(
        {
            "user_id": "682092082",
            "wc_trusted_token": "trusted-token",
            "cookies": {},
        }
    )
    assert auth.wc_auth_token == "682092082%2Ctrusted-token"


def test_from_dict_uses_api_wc_trusted_token_directly() -> None:
    """login-access-token returns wc_trusted_token already URL-encoded."""
    auth = GOLAuth.from_dict(
        {
            "user_id": "682092082",
            "wc_trusted_token": "682092082%2Ctrusted-token",
            "cookies": {},
        }
    )
    assert auth.wc_auth_token == "682092082%2Ctrusted-token"


def test_from_dict_repairs_double_encoded_wc_auth_token() -> None:
    """Legacy sessions with double-encoded WCAuthToken values are repaired."""
    auth = GOLAuth.from_dict(
        {
            "user_id": "682092082",
            "wc_trusted_token": "682092082%2Ctrusted-token",
            "wc_auth_token": "682092082%2C682092082%252Ctrusted-token",
            "cookies": {},
        }
    )
    assert auth.wc_auth_token == "682092082%2Ctrusted-token"


def test_from_dict_restores_next_refresh() -> None:
    """Saved refresh schedules are restored from session files."""
    auth = GOLAuth.from_dict(
        {
            "access_token": "oauth-token",
            "cookies": {},
            "next_refresh": "2026-08-30T18:31:20.321332+00:00",
        }
    )
    assert auth.next_refresh is not None
    assert auth.next_refresh.isoformat() == "2026-08-30T18:31:20.321332+00:00"


def test_to_dict_and_iter() -> None:
    """Sessions round-trip through to_dict and dict()."""
    auth = GOLAuth(
        access_token="oauth-token",
        wc_auth_token="682092082%2Ctrusted",
        cookies={"JSESSIONID": "abc"},
    )
    data = auth.to_dict()
    assert data["access_token"] == "oauth-token"
    assert dict(auth)["wc_auth_token"] == "682092082%2Ctrusted"


def test_from_session_file(tmp_path: Path) -> None:
    """Session files can be loaded from disk."""
    path = tmp_path / "session.json"
    path.write_text(
        json.dumps(
            {
                "access_token": "oauth-token",
                "wc_auth_token": "682092082%2Ctrusted",
                "cookies": {"JSESSIONID": "abc"},
            }
        ),
        encoding="utf-8",
    )
    auth = GOLAuth.from_session_file(str(path))
    assert auth.access_token == "oauth-token"


@pytest.mark.asyncio
async def test_auth_context_manager_closes_owned_session() -> None:
    """Owned aiohttp sessions are closed on context manager exit."""
    auth = GOLAuth(
        wc_auth_token="682092082%2Ctrusted",
        cookies={"JSESSIONID": "abc"},
    )
    async with auth:
        assert auth._owns_session is True
        session = auth.session
        assert not session.closed
    assert session.closed


@pytest.mark.asyncio
async def test_fetch_oidc_configuration() -> None:
    """OIDC discovery is fetched with browser-like headers."""
    auth = GOLAuth()
    sample = {
        "issuer": "https://account.sainsburys.co.uk/",
        "authorization_endpoint": "https://account.sainsburys.co.uk/oauth2/auth",
        "token_endpoint": "https://account.sainsburys.co.uk/oauth2/token",
    }

    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.text = AsyncMock(return_value="{}")
    mock_response.json = AsyncMock(return_value=sample)
    mock_response.__aenter__ = AsyncMock(return_value=mock_response)
    mock_response.__aexit__ = AsyncMock(return_value=None)

    with patch.object(auth.session, "get", return_value=mock_response) as mock_get:
        config = await auth.fetch_oidc_configuration()

    mock_get.assert_called_once()
    assert config["token_endpoint"] == sample["token_endpoint"]
    assert auth.oidc_config == sample


def test_build_authorization_url_contains_pkce_params() -> None:
    """Authorization URLs include PKCE and web OAuth parameters."""
    auth = GOLAuth(login_hint="user@example.com")
    auth.oidc_config = {
        "authorization_endpoint": "https://account.sainsburys.co.uk/oauth2/auth",
    }
    url = auth.build_authorization_url()
    assert "code_challenge=" in url
    assert "code_challenge_method=S256" in url
    assert f"client_id={AUTH_CLIENT_ID}" in url
    assert "client_id=gol-android" not in url
    assert (
        "redirect_uri=https%3A%2F%2Fwww.sainsburys.co.uk%2Fgol-ui%2Foauth%2Fredirect"
        in url
    )
    assert urllib.parse.quote(AUTH_SCOPE) in url or AUTH_SCOPE.replace(" ", "+") in url
    assert "missionId=gol" in url
    assert "response_mode=query" in url
    assert "login_hint=user%40example.com" in url
    assert auth._pkce_verifier is not None
    assert auth._oauth_state is not None


def test_from_dict_ignores_legacy_channel() -> None:
    """Session files that stored an OAuth channel still load."""
    auth = GOLAuth.from_dict(
        {
            "access_token": "oauth-token",
            "cookies": {},
            "channel": "android",
        }
    )
    assert auth.access_token == "oauth-token"
    assert "channel" not in auth.to_dict()


@pytest.mark.asyncio
async def test_login_raises_browser_login_required() -> None:
    """Headless login raises with the browser authorization URL."""
    auth = GOLAuth()
    auth.fetch_oidc_configuration = AsyncMock(
        return_value={
            "authorization_endpoint": "https://account.sainsburys.co.uk/oauth2/auth",
        }
    )

    with pytest.raises(BrowserLoginRequiredError) as exc:
        await auth.login()

    assert exc.value.authorization_url is not None
    assert "code_challenge=" in exc.value.authorization_url


@pytest.mark.asyncio
async def test_finish_login_requires_pkce_state() -> None:
    """finish_login validates PKCE setup before token exchange."""
    auth = GOLAuth()
    with pytest.raises(ConfirmationRedirectError, match="PKCE verifier"):
        await auth.finish_login("test-code")


@pytest.mark.asyncio
async def test_request_mfa_code_posts_to_send_mfa_endpoint() -> None:
    """MFA delivery is triggered via the send-mfa endpoint."""
    auth = GOLAuth()
    auth._login_referer = "https://account.sainsburys.co.uk/gol/login/mfa"

    mock_response = AsyncMock()
    mock_response.status = 204
    mock_response.text = AsyncMock(return_value="")
    mock_response.__aenter__ = AsyncMock(return_value=mock_response)
    mock_response.__aexit__ = AsyncMock(return_value=None)

    with patch.object(auth.session, "post", return_value=mock_response) as mock_post:
        await auth.request_mfa_code()

    mock_post.assert_called_once()
    called_url = mock_post.call_args.args[0]
    assert called_url.endswith("/gol/login/send-mfa")
    headers = mock_post.call_args.kwargs["headers"]
    assert headers["Content-Type"] == "application/json"
    assert headers["x-forwarded-from"] == "gol"
    await auth.close()


@pytest.mark.asyncio
async def test_identity_post_sends_form_origin_headers() -> None:
    """Credential POSTs include Origin and form content-type headers."""
    auth = GOLAuth()
    mock_response = AsyncMock()
    mock_response.status = 302
    mock_response.headers = {"Location": "/gol/login/mfa"}
    mock_response.text = AsyncMock(return_value="")
    mock_response.__aenter__ = AsyncMock(return_value=mock_response)
    mock_response.__aexit__ = AsyncMock(return_value=None)

    with patch.object(auth.session, "request", return_value=mock_response) as mock_req:
        await auth._identity_request(
            "POST",
            f"{AUTH_BASE_URL}/gol/login",
            data={"username": "user@example.com", "password": "secret"},
            referer=f"{AUTH_BASE_URL}/login-ui/gol/login",
        )

    headers = mock_req.call_args.kwargs["headers"]
    assert headers["Origin"] == AUTH_BASE_URL
    assert headers["Content-Type"] == "application/x-www-form-urlencoded"
    await auth.close()


@pytest.mark.asyncio
async def test_send_credentials_detects_mfa_login_ui_query_string() -> None:
    """MFA redirects from login-ui include a challenge query string."""
    auth = GOLAuth()
    auth._login_challenge = "abc123"
    auth._login_referer = f"{AUTH_BASE_URL}/login-ui/gol/login?login_challenge=abc123"
    auth.request_mfa_code = AsyncMock()
    mfa_url = f"{AUTH_BASE_URL}/login-ui/gol/login/mfa?login_challenge=abc123"
    auth._identity_request = AsyncMock(return_value=(302, "", mfa_url))

    with pytest.raises(MFARequiredError):
        await auth.send_credentials("user@example.com", "password")

    auth.request_mfa_code.assert_awaited_once()
    assert auth._login_referer == mfa_url
    await auth.close()


@pytest.mark.asyncio
async def test_send_credentials_raises_identity_error_code() -> None:
    """Identity error_code redirects are reported instead of an OAuth timeout."""
    auth = GOLAuth()
    auth._login_challenge = "abc123"
    auth._login_referer = f"{AUTH_BASE_URL}/login-ui/gol/login?login_challenge=abc123"
    error_url = (
        f"{AUTH_BASE_URL}/login-ui/gol/login?login_challenge=abc123&error_code=6053"
    )
    auth._identity_request = AsyncMock(return_value=(302, "", error_url))

    with pytest.raises(AuthError, match="error_code=6053"):
        await auth.send_credentials("user@example.com", "password")
    await auth.close()


def test_oauth_access_token_expired() -> None:
    """Expired access tokens are detected from the refresh schedule."""
    from datetime import UTC, datetime, timedelta

    auth = GOLAuth(access_token="token", cookies={})
    auth.next_refresh = datetime.now(UTC) + timedelta(hours=1)
    assert auth._oauth_access_token_expired() is False

    auth.next_refresh = datetime.now(UTC) - timedelta(seconds=1)
    assert auth._oauth_access_token_expired() is True

    auth.next_refresh = None
    assert auth._oauth_access_token_expired() is False


@pytest.mark.asyncio
async def test_send_refresh_request_raises_when_refresh_token_rejected() -> None:
    """Rejected refresh tokens require a new login instead of continuing."""
    from datetime import UTC, datetime, timedelta

    auth = GOLAuth(
        access_token="expired-token",
        refresh_token="stale-refresh",
        cookies={},
    )
    auth.next_refresh = datetime.now(UTC) - timedelta(hours=1)

    mock_response = AsyncMock()
    mock_response.status = 400
    mock_response.text = AsyncMock(
        return_value='{"error":"invalid_grant","error_description":"expired"}'
    )
    mock_response.__aenter__ = AsyncMock(return_value=mock_response)
    mock_response.__aexit__ = AsyncMock(return_value=None)

    with patch.object(auth.session, "post", return_value=mock_response):
        with pytest.raises(SessionRequiredError, match="Session expired"):
            await auth.send_refresh_request()

    assert auth.refresh_token is None
    await auth.close()


@pytest.mark.asyncio
async def test_send_request_raises_when_refresh_token_rejected() -> None:
    """Authenticated requests fail fast when refresh is rejected."""
    from datetime import UTC, datetime, timedelta

    auth = GOLAuth(
        access_token="expired-token",
        refresh_token="stale-refresh",
        wc_auth_token="682092082%2Ctrusted",
        cookies={},
    )
    auth.next_refresh = datetime.now(UTC) - timedelta(hours=1)

    mock_response = AsyncMock()
    mock_response.status = 400
    mock_response.text = AsyncMock(
        return_value='{"error":"invalid_grant","error_description":"expired"}'
    )
    mock_response.__aenter__ = AsyncMock(return_value=mock_response)
    mock_response.__aexit__ = AsyncMock(return_value=None)

    with patch.object(auth.session, "post", return_value=mock_response):
        with pytest.raises(SessionRequiredError, match="Session expired"):
            await auth.send_request("GET", "https://example.com/test")

    await auth.close()


def test_pending_login_roundtrip() -> None:
    """In-progress login state can be serialized and restored."""
    auth = GOLAuth(
        cookies={"session": "abc"},
    )
    auth._pkce_verifier = "verifier"
    auth._oauth_state = "state"
    auth.authorization_url = "https://account.sainsburys.co.uk/oauth2/auth?state=state"
    auth._login_referer = "https://account.sainsburys.co.uk/gol/login/mfa"
    auth._login_challenge = "challenge"

    payload = auth.pending_login_to_dict()
    restored = GOLAuth.from_pending_login_dict(payload)
    assert restored._pkce_verifier == "verifier"
    assert restored._oauth_state == "state"
    assert restored._login_referer == auth._login_referer
    assert restored.cookies["session"] == "abc"
