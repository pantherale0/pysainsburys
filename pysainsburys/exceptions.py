"""Exceptions for Sainsbury's GOL API."""

from __future__ import annotations

import json
from typing import Any


def parse_error_response(response: str) -> str | dict[str, Any] | list[Any] | None:
    """Parse an HTTP error body as JSON when possible."""
    text = response.strip()
    if not text:
        return None
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        return text
    if isinstance(parsed, (dict, list)):
        return parsed
    return text


def format_http_error_message(
    status: int,
    response: str,
    *,
    parsed: str | dict[str, Any] | list[Any] | None = None,
) -> str:
    """Format a human-readable HTTP error message."""
    body = parsed if parsed is not None else parse_error_response(response)
    if isinstance(body, dict):
        errors = body.get("errors")
        if isinstance(errors, list) and errors:
            parts: list[str] = []
            for error in errors:
                if not isinstance(error, dict):
                    continue
                code = str(error.get("code") or "").strip()
                detail = str(error.get("detail") or error.get("title") or "").strip()
                if code and detail:
                    parts.append(f"{code}: {detail}")
                elif code:
                    parts.append(code)
                elif detail:
                    parts.append(detail)
            if parts:
                return f"HTTP {status}: {'; '.join(parts)}"
        return f"HTTP {status}: {json.dumps(body)}"
    if isinstance(body, list):
        return f"HTTP {status}: {json.dumps(body)}"
    if body is None:
        return f"HTTP {status}"
    return f"HTTP {status}: {body}"


class AuthError(Exception):
    """General authentication error."""


class HttpException(Exception):
    """General HTTP error storing status and response."""

    def __init__(self, status: int, response: str) -> None:
        self.status = status
        self.response = response
        self.response_json = parse_error_response(response)
        super().__init__(
            format_http_error_message(
                status,
                response,
                parsed=self.response_json,
            )
        )

    @property
    def errors(self) -> list[dict[str, Any]]:
        """Return structured API errors when the body matches GOL error JSON."""
        if isinstance(self.response_json, dict):
            raw_errors = self.response_json.get("errors")
            if isinstance(raw_errors, list):
                return [error for error in raw_errors if isinstance(error, dict)]
        return []


class UnknownEndpointError(HttpException):
    """Unexpected HTTP status from a known endpoint."""


class ExpiredAccessTokenError(AuthError):
    """401 Unauthorized — access token or commerce session expired."""


class InvalidGrantError(AuthError):
    """OAuth grant expired or invalid."""


class InvalidRequestError(AuthError):
    """OAuth request is malformed or missing required parameters."""


class InvalidClientError(AuthError):
    """Client authentication failed."""


class UnauthorizedClientError(AuthError):
    """Client is not authorized for this grant type or flow."""


class UnsupportedGrantTypeError(AuthError):
    """OAuth grant type is not supported."""


class InvalidScopeError(AuthError):
    """Requested OAuth scope is invalid, unknown, or malformed."""


class AccessDeniedError(AuthError):
    """Resource owner or policy denied the request."""


class InteractionRequiredError(AuthError):
    """Interactive user action is required to continue."""


class LoginRequiredError(AuthError):
    """User sign-in is required to continue."""


class SessionRequiredError(AuthError):
    """Commerce session headers or cookies are missing."""


class TokenRequestError(AuthError):
    """Error requesting a token from the token server."""


class CommerceSessionError(AuthError):
    """Error exchanging OAuth tokens for a commerce session."""


class ConfirmationRedirectError(AuthError):
    """Error confirming login with redirect."""


class BrowserLoginRequiredError(InteractionRequiredError):
    """
    Interactive browser login is required to continue.

    When raised, open :attr:`authorization_url` in a desktop browser, sign in,
    then call :meth:`GOLAuth.finish_login` with the redirect URL or code.
    """

    def __init__(
        self,
        message: str = "Browser login required",
        *,
        authorization_url: str | None = None,
    ) -> None:
        super().__init__(message)
        self.authorization_url = authorization_url


class MFARequiredError(InteractionRequiredError):
    """
    MFA is required to complete the login flow.

    Raised after :meth:`GOLAuth.request_mfa_code` has triggered delivery of
    the verification code. Call :meth:`GOLAuth.send_mfa_request` with the
    code received by the user.
    """


class ParseError(Exception):
    """Error parsing an API response into a domain model."""


class NotBoundError(Exception):
    """Domain object is not bound to an authenticated client."""
