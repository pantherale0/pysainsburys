"""Authentication and session handling for Sainsbury's GOL API."""

from __future__ import annotations

import json
import logging
import secrets
import urllib.parse
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from typing import Any

import aiohttp
from yarl import URL

from .const import (
    AUTH_AUTHORIZE_URL,
    AUTH_BASE_URL,
    AUTH_CLIENT_ID,
    AUTH_CODE_CHALLENGE_METHOD,
    AUTH_DISCOVERY_URL,
    AUTH_EXTRA_PARAMS,
    AUTH_LOGIN_URL,
    AUTH_MFA_URL,
    AUTH_REDIRECT_URI,
    AUTH_SCOPE,
    AUTH_SEND_MFA_URL,
    AUTH_TOKEN_URL,
    BROWSER_HEADERS,
    GOL_APP_USER_AGENT,
    GOL_BASE_URL,
    GOL_ENDPOINTS,
)
from .exceptions import (
    AccessDeniedError,
    AuthError,
    BrowserLoginRequiredError,
    CommerceSessionError,
    ConfirmationRedirectError,
    ExpiredAccessTokenError,
    InvalidClientError,
    InvalidGrantError,
    InvalidRequestError,
    InvalidScopeError,
    MFARequiredError,
    SessionRequiredError,
    TokenRequestError,
    UnauthorizedClientError,
    UnknownEndpointError,
    UnsupportedGrantTypeError,
)
from .utils import (
    build_code_challenge,
    cookies_to_header,
    decode_oauth_redirect,
    identity_error_code,
    is_identity_login_url,
    is_identity_mfa_url,
    load_session_file,
    login_challenge_from_url,
    normalize_wc_auth_token,
    parse_authorization_input,
    parse_cookie_header,
    random_string,
    resolve_redirect_url,
    save_session_file,
)

_LOGGER = logging.getLogger(__name__)

_SESSION_EXPIRED_MESSAGE = (
    "Session expired. Run `pysainsburys auth login` or "
    "`pysainsburys auth finish` to sign in again."
)

OAUTH_ERROR_EXCEPTION_MAP = {
    "invalid_grant": InvalidGrantError,
    "invalid_request": InvalidRequestError,
    "invalid_client": InvalidClientError,
    "unauthorized_client": UnauthorizedClientError,
    "unsupported_grant_type": UnsupportedGrantTypeError,
    "invalid_scope": InvalidScopeError,
    "access_denied": AccessDeniedError,
}


class GOLAuth:
    """Represent an authenticated Sainsbury's GOL session."""

    def __init__(
        self,
        *,
        access_token: str | None = None,
        refresh_token: str | None = None,
        wc_auth_token: str | None = None,
        user_id: str | None = None,
        wc_trusted_token: str | None = None,
        cookies: dict[str, str] | None = None,
        app_version: str | None = None,
        login_hint: str | None = None,
        session: aiohttp.ClientSession | None = None,
    ) -> None:
        self._auth_session = session
        self._owns_session = session is None
        self.access_token = access_token
        self._refresh_token = refresh_token
        self.wc_auth_token = wc_auth_token
        self.user_id = user_id
        self.wc_trusted_token = wc_trusted_token
        self.cookies = dict(cookies or {})
        default_version = GOL_APP_USER_AGENT.removeprefix("GOLAppAndroid/")
        self.app_version = app_version or default_version
        self.login_hint = login_hint
        self.next_refresh: datetime | None = None
        self.personalization_id: str | None = None
        self.oidc_config: dict[str, Any] | None = None
        self.authorization_url: str | None = None
        self._pkce_verifier: str | None = None
        self._oauth_state: str | None = None
        self._login_challenge: str | None = None
        self._login_referer: str | None = None

        if self.wc_auth_token is None:
            self.wc_auth_token = normalize_wc_auth_token(
                user_id=self.user_id,
                wc_trusted_token=self.wc_trusted_token,
            )

    @property
    def session(self) -> aiohttp.ClientSession:
        """Return the aiohttp session, creating one when needed."""
        if self._auth_session is None:
            cookie_jar = aiohttp.CookieJar(unsafe=True)
            self._auth_session = aiohttp.ClientSession(cookie_jar=cookie_jar)
            if self.cookies:
                cookie_jar.update_cookies(
                    self.cookies,
                    response_url=URL(AUTH_BASE_URL),
                )
        return self._auth_session

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> GOLAuth:
        """Create an auth object from a serialized session mapping."""
        cookies = data.get("cookies")
        if isinstance(cookies, str):
            cookies = parse_cookie_header(cookies)
        elif cookies is None:
            cookies = {}
        elif not isinstance(cookies, dict):
            msg = "Session cookies must be a mapping or Cookie header string."
            raise ValueError(msg)

        auth = cls(
            access_token=data.get("access_token"),
            refresh_token=data.get("refresh_token"),
            wc_auth_token=data.get("wc_auth_token"),
            user_id=data.get("user_id"),
            wc_trusted_token=data.get("wc_trusted_token"),
            cookies={str(k): str(v) for k, v in cookies.items()},
            app_version=data.get("app_version"),
            login_hint=data.get("login_hint"),
        )
        return cls._apply_session_metadata(auth, data)

    @classmethod
    def _apply_session_metadata(cls, auth: GOLAuth, data: dict[str, Any]) -> GOLAuth:
        """Apply optional session metadata after constructing auth state."""
        auth.personalization_id = data.get("personalization_id")
        next_refresh = data.get("next_refresh")
        if isinstance(next_refresh, str):
            auth.next_refresh = datetime.fromisoformat(next_refresh)
        auth.wc_auth_token = normalize_wc_auth_token(
            user_id=auth.user_id,
            wc_trusted_token=auth.wc_trusted_token,
            wc_auth_token=auth.wc_auth_token or data.get("wc_auth_token"),
        )
        return auth

    @classmethod
    async def from_session_file(cls, path: str) -> GOLAuth:
        """Load a session export created by tooling or a previous ``to_dict()``."""
        return cls.from_dict(await load_session_file(path))

    @property
    def refresh_token(self) -> str | None:
        """Return the OAuth refresh token."""
        return self._refresh_token

    @property
    def token_endpoint(self) -> str:
        """Return the OAuth token endpoint URL."""
        if self.oidc_config:
            endpoint = self.oidc_config.get("token_endpoint")
            if isinstance(endpoint, str):
                return endpoint
        return AUTH_TOKEN_URL

    @property
    def authorization_endpoint(self) -> str:
        """Return the OAuth authorization endpoint URL."""
        if self.oidc_config:
            endpoint = self.oidc_config.get("authorization_endpoint")
            if isinstance(endpoint, str):
                return endpoint
        return AUTH_AUTHORIZE_URL

    @property
    def authenticated_headers(self) -> dict[str, str]:
        """Return authenticated headers for grocery API calls."""
        headers = {
            "Accept": "application/json",
            "User-Agent": f"GOLAppAndroid/{self.app_version}",
        }
        if self.access_token:
            headers["Authorization"] = f"Bearer {self.access_token}"
        if self.wc_auth_token:
            headers["WCAuthToken"] = self.wc_auth_token
        if self.cookies:
            headers["Cookie"] = cookies_to_header(self.cookies)
        return headers

    def _browser_headers(self, *, referer: str | None = None) -> dict[str, str]:
        """Return browser-like headers for identity provider requests."""
        headers = dict(BROWSER_HEADERS)
        if referer is not None:
            headers["Referer"] = referer
            headers["sec-fetch-site"] = "same-origin"
        return headers

    def _oauth_access_token_expired(self) -> bool:
        """Return whether the OAuth access token is past its refresh schedule."""
        if not self.access_token:
            return True
        if self.next_refresh is None:
            return False
        return self.next_refresh <= datetime.now(UTC)

    def to_dict(self) -> dict[str, Any]:
        """Return the session as a JSON-serializable mapping."""
        return {
            "access_token": self.access_token,
            "refresh_token": self.refresh_token,
            "wc_auth_token": self.wc_auth_token,
            "user_id": self.user_id,
            "wc_trusted_token": self.wc_trusted_token,
            "cookies": self.cookies,
            "app_version": self.app_version,
            "login_hint": self.login_hint,
            "personalization_id": self.personalization_id,
            "next_refresh": (
                self.next_refresh.isoformat() if self.next_refresh is not None else None
            ),
        }

    async def save_session_file(self, path: str) -> None:
        """Persist the current session to disk."""
        self._sync_session_cookies()
        await save_session_file(path, self.to_dict())

    def pending_login_to_dict(self) -> dict[str, Any]:
        """Return in-progress login state for MFA completion."""
        return {
            **self.to_dict(),
            "pkce_verifier": self._pkce_verifier,
            "oauth_state": self._oauth_state,
            "authorization_url": self.authorization_url,
            "login_referer": self._login_referer,
            "login_challenge": self._login_challenge,
        }

    @classmethod
    def from_pending_login_dict(cls, data: dict[str, Any]) -> GOLAuth:
        """Restore in-progress login state from a mapping."""
        payload = dict(data)
        pending_fields = (
            "pkce_verifier",
            "oauth_state",
            "authorization_url",
            "login_referer",
            "login_challenge",
        )
        pending = {field: payload.pop(field, None) for field in pending_fields}
        auth = cls.from_dict(payload)
        auth._pkce_verifier = pending["pkce_verifier"]
        auth._oauth_state = pending["oauth_state"]
        auth.authorization_url = pending["authorization_url"]
        auth._login_referer = pending["login_referer"]
        auth._login_challenge = pending["login_challenge"]
        return auth

    async def save_pending_login(self, path: str) -> None:
        """Persist in-progress login state awaiting MFA verification."""
        await save_session_file(path, self.pending_login_to_dict())

    @classmethod
    async def from_pending_login_file(cls, path: str) -> GOLAuth:
        """Load in-progress login state from disk."""
        return cls.from_pending_login_dict(await load_session_file(path))

    def _sync_session_cookies(self) -> None:
        """Copy cookies from the aiohttp jar into the session mapping."""
        for cookie in self.session.cookie_jar:
            self.cookies[cookie.key] = cookie.value

    def __iter__(self) -> Iterator[tuple[str, Any]]:
        """Allow ``dict(auth)`` conversion."""
        return iter(self.to_dict().items())

    async def close(self) -> None:
        """Close the underlying HTTP session when owned by this object."""
        if (
            self._owns_session
            and self._auth_session is not None
            and not self._auth_session.closed
        ):
            await self._auth_session.close()
            self._auth_session = None

    async def __aenter__(self) -> GOLAuth:
        """Enter async context manager."""
        return self

    async def __aexit__(self, *_args: object) -> None:
        """Close the auth session on context exit."""
        await self.close()

    def _raise_mapped_token_error(self, status: int, response_text: str) -> None:
        """Raise a mapped exception for known OAuth token errors."""
        try:
            error_data = json.loads(response_text)
            if not isinstance(error_data, dict):
                error_data = {}
            error_code = str(error_data.get("error", "unknown")).lower()
            error_message = error_data.get("error_description") or response_text
        except json.JSONDecodeError:
            error_code = "unknown"
            error_message = response_text

        exception_class = OAUTH_ERROR_EXCEPTION_MAP.get(error_code)
        if exception_class is not None:
            raise exception_class(error_message)
        if status != 200:
            raise TokenRequestError(error_message)

    async def fetch_oidc_configuration(self) -> dict[str, Any]:
        """Fetch OIDC discovery metadata using browser-like headers."""
        _LOGGER.debug("GOL Auth: fetching OIDC discovery document")
        async with self.session.get(
            AUTH_DISCOVERY_URL,
            headers=self._browser_headers(),
        ) as response:
            text = await response.text()
            if response.status != 200:
                raise TokenRequestError(
                    f"OIDC discovery failed ({response.status}): {text}"
                )
            data = await response.json()
            if not isinstance(data, dict):
                msg = "OIDC discovery response was not a JSON object."
                raise TokenRequestError(msg)
            self.oidc_config = data
            return data

    def _form_post_headers(
        self, *, referer: str, origin: str = AUTH_BASE_URL
    ) -> dict[str, str]:
        """Return browser headers for identity form submissions."""
        headers = self._browser_headers(referer=referer)
        headers["Content-Type"] = "application/x-www-form-urlencoded"
        headers["Origin"] = origin
        headers["sec-fetch-mode"] = "navigate"
        headers["sec-fetch-user"] = "?1"
        return headers

    async def _identity_request(
        self,
        method: str,
        url: str,
        *,
        data: dict[str, str] | None = None,
        referer: str | None = None,
    ) -> tuple[int, str, str | None]:
        """Send an identity request without auto-following redirects."""
        if data is not None:
            headers = self._form_post_headers(referer=referer or url)
        else:
            headers = self._browser_headers(referer=referer)
        async with self.session.request(
            method=method,
            url=url,
            headers=headers,
            data=data,
            allow_redirects=False,
        ) as response:
            location = response.headers.get("Location")
            text = await response.text()
            return response.status, text, location

    async def _follow_identity_redirects(
        self,
        start_url: str,
        *,
        referer: str | None = None,
        max_redirects: int = 10,
    ) -> str:
        """Follow identity redirects until a terminal URL is reached."""
        url = start_url
        current_referer = referer
        for _ in range(max_redirects):
            status, _text, location = await self._identity_request(
                "GET",
                url,
                referer=current_referer,
            )
            if status in {301, 302, 303, 307, 308} and location:
                next_url = resolve_redirect_url(location)
                current_referer = url
                url = next_url
                continue
            if status == 200:
                return url
            raise AuthError(f"Unexpected identity response ({status}) for {url}")
        raise AuthError("Too many identity redirects.")

    def _authorization_code_from_url(self, url: str) -> str | None:
        """Return an authorization code when the URL matches the OAuth redirect."""
        code, _state = decode_oauth_redirect(url)
        if code is None:
            return None
        parsed = urllib.parse.urlparse(url)
        redirect = urllib.parse.urlparse(AUTH_REDIRECT_URI)
        if parsed.netloc == redirect.netloc and parsed.path == redirect.path:
            return code
        return None

    def _raise_if_identity_error(self, url: str) -> None:
        """Raise when an identity redirect indicates a failed login."""
        error_code = identity_error_code(url)
        if error_code is not None:
            raise AuthError(f"Identity login failed (error_code={error_code}): {url}")
        if is_identity_login_url(url):
            raise AuthError(f"Login was not accepted: {url}")

    async def _raise_mfa_required(self, url: str) -> None:
        """Request an MFA code for *url* and raise ``MFARequiredError``."""
        self._login_referer = url
        challenge = login_challenge_from_url(url)
        if challenge is not None:
            self._login_challenge = challenge
        await self.request_mfa_code()
        raise MFARequiredError(
            "Multi-factor authentication required. A verification code has "
            "been sent; call send_mfa_request() with the code."
        )

    async def _follow_until_authorization_code(
        self,
        start_url: str,
        *,
        referer: str | None = None,
        max_redirects: int = 15,
    ) -> str:
        """Follow redirects until the OAuth authorization code is available."""
        url = resolve_redirect_url(start_url, base_url=AUTH_BASE_URL)
        if url.startswith(("http://", "https://")) and AUTH_BASE_URL not in url:
            code = self._authorization_code_from_url(url)
            if code is not None:
                return code

        current_referer = referer
        for _ in range(max_redirects):
            code = self._authorization_code_from_url(url)
            if code is not None:
                return code

            self._raise_if_identity_error(url)
            if is_identity_mfa_url(url):
                await self._raise_mfa_required(url)

            status, _text, location = await self._identity_request(
                "GET",
                url,
                referer=current_referer,
            )
            if status in {301, 302, 303, 307, 308} and location:
                next_url = resolve_redirect_url(location, base_url=AUTH_BASE_URL)
                if next_url.startswith("/"):
                    next_url = resolve_redirect_url(next_url, base_url=AUTH_BASE_URL)
                elif not next_url.startswith(("http://", "https://")):
                    next_url = resolve_redirect_url(next_url, base_url=AUTH_BASE_URL)
                current_referer = url
                url = next_url
                continue
            raise AuthError(
                "OAuth redirect chain ended without authorization code "
                f"({status}): {url}"
            )
        raise AuthError(
            "Too many OAuth redirects while waiting for authorization code."
        )

    async def _ensure_login_challenge(self) -> str:
        """Start the OAuth login flow and capture the Hydra login challenge."""
        if self._login_challenge is not None:
            return self._login_challenge

        if self.authorization_url is None:
            await self.send_login_request()

        if self.authorization_url is None:
            raise AuthError("Authorization URL was not produced by the login request.")
        url = await self._follow_identity_redirects(self.authorization_url)
        challenge = login_challenge_from_url(url)
        if challenge is None and "/gol/login" in url:
            challenge = login_challenge_from_url(url)
        if challenge is None:
            raise AuthError("login_challenge not found in identity login redirect.")
        self._login_challenge = challenge
        self._login_referer = url
        return challenge

    def build_authorization_url(self) -> str:
        """Build a PKCE authorization URL for browser-based login."""
        self._pkce_verifier = random_string(43, 128)
        code_challenge = build_code_challenge(self._pkce_verifier)
        self._oauth_state = secrets.token_urlsafe(32)
        params: dict[str, str] = {
            "client_id": AUTH_CLIENT_ID,
            "response_type": "code",
            "redirect_uri": AUTH_REDIRECT_URI,
            "scope": AUTH_SCOPE,
            "code_challenge": code_challenge,
            "code_challenge_method": AUTH_CODE_CHALLENGE_METHOD,
            "state": self._oauth_state,
            **AUTH_EXTRA_PARAMS,
        }
        if self.login_hint:
            params["login_hint"] = self.login_hint
        authorization_url = (
            f"{self.authorization_endpoint}?{urllib.parse.urlencode(params)}"
        )
        self.authorization_url = authorization_url
        return authorization_url

    async def send_login_request(self) -> str:
        """Prepare browser login and return the authorization URL."""
        await self.fetch_oidc_configuration()
        return self.build_authorization_url()

    async def exchange_authorization_code(self, code: str) -> dict[str, Any]:
        """Exchange an authorization code for OAuth tokens."""
        if self._pkce_verifier is None:
            raise ConfirmationRedirectError(
                "Missing PKCE verifier. Call send_login_request() first."
            )

        async with self.session.post(
            self.token_endpoint,
            data=urllib.parse.urlencode(
                {
                    "grant_type": "authorization_code",
                    "client_id": AUTH_CLIENT_ID,
                    "redirect_uri": AUTH_REDIRECT_URI,
                    "code": code,
                    "code_verifier": self._pkce_verifier,
                }
            ),
            headers={
                **self._browser_headers(
                    referer=self.authorization_url or self.authorization_endpoint
                ),
                "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            },
        ) as response:
            text = await response.text()
            if response.status != 200:
                self._raise_mapped_token_error(response.status, text)
            token_data = await response.json()

        self.access_token = token_data.get("access_token")
        if token_data.get("refresh_token"):
            self._refresh_token = token_data["refresh_token"]
        try:
            expires_in = int(token_data.get("expires_in", 3600))
        except (TypeError, ValueError):
            expires_in = 3600
        self.next_refresh = datetime.now(UTC) + timedelta(seconds=expires_in)
        return token_data

    async def finish_login(
        self,
        redirect_or_code: str,
        *,
        expected_state: str | None = None,
        exchange_commerce: bool = True,
    ) -> dict[str, Any]:
        """Complete browser login from a redirect URL or raw authorization code."""
        code, state = parse_authorization_input(redirect_or_code)
        if code is None:
            raise ConfirmationRedirectError("Authorization code not found.")
        if (
            expected_state is None
            and self._oauth_state is not None
            and state is not None
            and state != self._oauth_state
        ):
            raise ConfirmationRedirectError("OAuth state mismatch.")
        if expected_state is not None and state != expected_state:
            raise ConfirmationRedirectError("OAuth state mismatch.")

        token_data = await self.exchange_authorization_code(code)
        if exchange_commerce:
            await self.exchange_commerce_session()
        return token_data

    async def send_credentials(
        self,
        username: str,
        password: str,
        *,
        io_black_box: str | None = None,
    ) -> None:
        """Submit username and password to the web identity login form."""
        login_challenge = await self._ensure_login_challenge()

        referer = self._login_referer or (
            f"{AUTH_LOGIN_URL}?login_challenge={login_challenge}"
        )
        form: dict[str, str] = {
            "web_authn_device": "0",
            "login_challenge": login_challenge,
            "username": username,
            "password": password,
        }
        if io_black_box is not None:
            form["ioBlackBox"] = io_black_box

        status, _text, location = await self._identity_request(
            "POST",
            AUTH_LOGIN_URL,
            data=form,
            referer=referer,
        )
        if status not in {301, 302, 303, 307, 308} or not location:
            raise AuthError(f"Login failed ({status}).")

        code = await self._follow_until_authorization_code(
            resolve_redirect_url(location),
            referer=AUTH_LOGIN_URL,
        )
        await self.exchange_authorization_code(code)

    async def request_mfa_code(self) -> None:
        """Request delivery of an MFA verification code."""
        referer = self._login_referer or AUTH_MFA_URL
        headers = self._browser_headers(referer=referer)
        headers["Accept"] = "*/*"
        headers["Content-Type"] = "application/json"
        headers["x-forwarded-from"] = "gol"
        headers["sec-fetch-dest"] = "empty"
        headers["sec-fetch-mode"] = "cors"
        headers.pop("sec-fetch-user", None)

        async with self.session.post(
            AUTH_SEND_MFA_URL,
            headers=headers,
            allow_redirects=False,
        ) as response:
            text = await response.text()
            if response.status not in {200, 204}:
                raise AuthError(
                    f"Failed to send MFA verification code ({response.status}): {text}"
                )

    async def send_mfa_request(
        self,
        code: str,
        *,
        io_black_box: str | None = None,
        exchange_commerce: bool = True,
    ) -> dict[str, Any]:
        """Submit an MFA verification code and complete OAuth token exchange."""
        referer = self._login_referer or AUTH_MFA_URL
        form: dict[str, str] = {"code": code}
        if io_black_box is not None:
            form["ioBlackBox"] = io_black_box

        status, _text, location = await self._identity_request(
            "POST",
            AUTH_MFA_URL,
            data=form,
            referer=referer,
        )
        if status not in {301, 302, 303, 307, 308} or not location:
            raise AuthError(f"MFA verification failed ({status}).")

        auth_code = await self._follow_until_authorization_code(
            resolve_redirect_url(location),
            referer=AUTH_MFA_URL,
        )
        token_data = await self.exchange_authorization_code(auth_code)
        if exchange_commerce:
            await self.exchange_commerce_session()
        return token_data

    async def login(
        self,
        username: str | None = None,
        password: str | None = None,
        *,
        mfa_code: str | None = None,
        io_black_box: str | None = None,
        exchange_commerce: bool = True,
    ) -> dict[str, Any] | None:
        """Sign in via web credentials or start interactive browser login."""
        if username is not None and password is not None:
            await self.send_login_request()
            try:
                await self.send_credentials(
                    username,
                    password,
                    io_black_box=io_black_box,
                )
            except MFARequiredError:
                if mfa_code is None:
                    raise
                return await self.send_mfa_request(
                    mfa_code,
                    io_black_box=io_black_box,
                    exchange_commerce=exchange_commerce,
                )
            if exchange_commerce:
                await self.exchange_commerce_session()
            return None

        authorization_url = await self.send_login_request()
        raise BrowserLoginRequiredError(
            "Open the authorization URL in a desktop browser, sign in, then "
            "call finish_login() with the redirect URL or authorization code.",
            authorization_url=authorization_url,
        )

    async def send_refresh_request(self) -> None:
        """Refresh the OAuth access token when a refresh token is available."""
        if self.refresh_token is None:
            return
        if self.next_refresh is not None and self.next_refresh > datetime.now(UTC):
            return

        if self.oidc_config is None:
            try:
                await self.fetch_oidc_configuration()
            except TokenRequestError:
                _LOGGER.debug(
                    "GOL Auth: OIDC discovery unavailable during refresh; "
                    "using static token endpoint"
                )

        _LOGGER.debug("GOL Auth: refreshing access token")
        try:
            async with self.session.post(
                self.token_endpoint,
                data=urllib.parse.urlencode(
                    {
                        "grant_type": "refresh_token",
                        "client_id": AUTH_CLIENT_ID,
                        "refresh_token": self.refresh_token,
                    }
                ),
                headers={
                    **self._browser_headers(),
                    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
                },
            ) as response:
                text = await response.text()
                if response.status != 200:
                    self._raise_mapped_token_error(response.status, text)

                token_data = await response.json()
        except InvalidGrantError:
            _LOGGER.warning("GOL Auth: refresh token rejected")
            self._refresh_token = None
            raise SessionRequiredError(_SESSION_EXPIRED_MESSAGE) from None

        self.access_token = token_data.get("access_token")
        if token_data.get("refresh_token"):
            self._refresh_token = token_data["refresh_token"]
        try:
            expires_in = int(token_data.get("expires_in", 3600))
        except (TypeError, ValueError):
            expires_in = 3600
        self.next_refresh = datetime.now(UTC) + timedelta(seconds=expires_in)
        self._sync_session_cookies()

    async def exchange_commerce_session(
        self,
        *,
        food_profile_create: bool = True,
    ) -> dict[str, Any]:
        """Exchange the OAuth access token for WC commerce session tokens."""
        if self.access_token is None:
            raise SessionRequiredError("Access token required for commerce exchange.")

        endpoint = GOL_ENDPOINTS["login_access_token"]
        url = GOL_BASE_URL + endpoint["endpoint"]
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": f"GOLAppAndroid/{self.app_version}",
            "Authorization": f"Bearer {self.access_token}",
        }
        body = {
            "access_token": self.access_token,
            "food_profile_create": food_profile_create,
        }

        async with self.session.request(
            method=endpoint["method"],
            url=url,
            headers=headers,
            json=body,
        ) as response:
            text = await response.text()
            if response.status != 200:
                if response.status == 400 and "INVALID_TOKEN" in text:
                    raise SessionRequiredError(_SESSION_EXPIRED_MESSAGE)
                raise CommerceSessionError(
                    f"Commerce session exchange failed ({response.status}): {text}"
                )
            data = await response.json()
            for cookie in response.cookies.values():
                self.cookies[cookie.key] = cookie.value

        self.user_id = data.get("user_id")
        self.wc_trusted_token = data.get("wc_trusted_token")
        self.personalization_id = data.get("personalization_id")
        self.wc_auth_token = normalize_wc_auth_token(
            user_id=self.user_id,
            wc_trusted_token=self.wc_trusted_token,
        )

        return data

    async def refresh_commerce_session(
        self,
        *,
        food_profile_create: bool = True,
    ) -> dict[str, Any]:
        """Re-exchange OAuth tokens for a fresh commerce session."""
        return await self.exchange_commerce_session(
            food_profile_create=food_profile_create,
        )

    async def send_request(
        self,
        method: str,
        url: str,
        body: dict[str, Any] | list[Any] | None = None,
        *,
        headers: dict[str, str] | None = None,
        params: dict[str, str | int | float | bool] | None = None,
    ) -> dict[str, Any] | list[Any] | None:
        """Send a request to the API and return the JSON response."""
        await self.send_refresh_request()
        if self.wc_auth_token is None and not self.cookies:
            raise SessionRequiredError(
                "Commerce session required. Provide WCAuthToken/cookies or call "
                "exchange_commerce_session()."
            )

        return await self._send_authenticated_request(
            method=method,
            url=url,
            body=body,
            headers=headers,
            params=params,
            retry_commerce=True,
        )

    async def _send_authenticated_request(
        self,
        method: str,
        url: str,
        body: dict[str, Any] | list[Any] | None = None,
        *,
        headers: dict[str, str] | None = None,
        params: dict[str, str | int | float | bool] | None = None,
        retry_commerce: bool = False,
    ) -> dict[str, Any] | list[Any] | None:
        """Send an authenticated grocery API request."""
        request_headers = self.authenticated_headers
        if headers:
            request_headers = {**request_headers, **headers}

        async with self.session.request(
            method=method,
            url=url,
            headers=request_headers,
            json=body,
            params=params,
        ) as response:
            _LOGGER.debug(
                "Request to %s returned with status %s",
                url,
                response.status,
            )
            if response.status == 401 and retry_commerce:
                await response.release()
                if self._oauth_access_token_expired():
                    raise SessionRequiredError(_SESSION_EXPIRED_MESSAGE)
                if self.access_token:
                    _LOGGER.debug("GOL Auth: refreshing commerce session after 401")
                    await self.exchange_commerce_session()
                    return await self._send_authenticated_request(
                        method=method,
                        url=url,
                        body=body,
                        headers=headers,
                        params=params,
                        retry_commerce=False,
                    )
            if response.status == 401:
                raise ExpiredAccessTokenError(_SESSION_EXPIRED_MESSAGE)
            if response.ok:
                if response.content_length == 0:
                    return None
                content_type = response.headers.get("Content-Type", "")
                if "application/json" in content_type:
                    return await response.json()
                text = await response.text()
                if not text:
                    return None
                return json.loads(text)
            raise UnknownEndpointError(response.status, await response.text())

    @property
    def public_headers(self) -> dict[str, str]:
        """Return headers for unauthenticated grocery API requests."""
        return {
            "Accept": "application/json",
            "User-Agent": f"GOLAppAndroid/{self.app_version}",
        }

    async def send_public_request(
        self,
        method: str,
        url: str,
        *,
        headers: dict[str, str] | None = None,
        params: dict[str, str | int | float | bool] | None = None,
    ) -> dict[str, Any] | list[Any] | None:
        """Send a request that does not require a commerce session."""
        request_headers = self.public_headers
        if headers:
            request_headers = {**request_headers, **headers}

        async with self.session.request(
            method=method,
            url=url,
            headers=request_headers,
            params=params,
        ) as response:
            _LOGGER.debug(
                "Public request to %s returned with status %s",
                url,
                response.status,
            )
            if response.ok:
                if response.content_length == 0:
                    return None
                content_type = response.headers.get("Content-Type", "")
                if "application/json" in content_type:
                    return await response.json()
                text = await response.text()
                if not text:
                    return None
                return json.loads(text)
            raise UnknownEndpointError(response.status, await response.text())
