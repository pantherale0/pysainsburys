"""Authentication and API handling for Sainsbury's GOL."""

from __future__ import annotations

import logging
from collections.abc import Iterator
from typing import Any

from .auth import GOLAuth
from .const import GOL_BASE_URL, GOL_ENDPOINTS, PRODUCT_FINDER_BASE_URL

_LOGGER = logging.getLogger(__name__)


class API:
    """API handler for Sainsbury's GOL."""

    def __init__(self, auth_obj: GOLAuth) -> None:
        self._auth = auth_obj

    @property
    def user_id(self) -> str | None:
        """Return the commerce user id when known."""
        return self._auth.user_id

    async def send_request(
        self,
        endpoint: str,
        body: dict[str, Any] | list[Any] | None = None,
        *,
        params: dict[str, str | int | float | bool] | None = None,
        **path_params: str,
    ) -> dict[str, Any] | list[Any] | None:
        """Send a request to the API using the authentication handler."""
        if endpoint not in GOL_ENDPOINTS:
            raise ValueError("Provided API endpoint does not exist.")
        _LOGGER.debug(
            "API: sending request to endpoint '%s' with body: %s",
            endpoint,
            body,
        )
        endpoint_map = GOL_ENDPOINTS[endpoint]
        built_url = GOL_BASE_URL + endpoint_map["endpoint"].format(**path_params)
        return await self._auth.send_request(
            method=endpoint_map["method"],
            url=built_url,
            body=body,
            params=params,
        )

    async def send_public_request(
        self,
        endpoint: str,
        *,
        params: dict[str, str | int | float | bool] | None = None,
        **path_params: str,
    ) -> dict[str, Any] | list[Any] | None:
        """Send a request that does not require a commerce session."""
        if endpoint not in GOL_ENDPOINTS:
            raise ValueError("Provided API endpoint does not exist.")
        endpoint_map = GOL_ENDPOINTS[endpoint]
        built_url = GOL_BASE_URL + endpoint_map["endpoint"].format(**path_params)
        return await self._auth.send_public_request(
            method=endpoint_map["method"],
            url=built_url,
            params=params,
        )

    async def send_product_finder_request(
        self,
        path: str,
        *,
        params: dict[str, str | int | float | bool] | None = None,
    ) -> dict[str, Any] | list[Any] | None:
        """Send a public request to the Product Finder API."""
        url = PRODUCT_FINDER_BASE_URL + path
        return await self._auth.send_public_request(
            method="GET",
            url=url,
            params=params,
        )

    async def exchange_commerce_session(
        self,
        *,
        food_profile_create: bool = True,
    ) -> dict[str, Any]:
        """Exchange OAuth tokens for a commerce session."""
        return await self._auth.exchange_commerce_session(
            food_profile_create=food_profile_create,
        )

    async def token_refresh(self) -> None:
        """Force OAuth token refresh."""
        await self._auth.send_refresh_request()

    async def login(self) -> str:
        """Prepare browser login and return the authorization URL."""
        return await self._auth.send_login_request()

    async def finish_login(
        self,
        redirect_or_code: str,
        *,
        exchange_commerce: bool = True,
    ) -> dict[str, Any]:
        """Complete browser login from a redirect URL or authorization code."""
        return await self._auth.finish_login(
            redirect_or_code,
            exchange_commerce=exchange_commerce,
        )

    async def logout(self) -> None:
        """End the remote commerce session."""
        await self.send_request(endpoint="logout")

    async def close(self) -> None:
        """Close the underlying HTTP session."""
        await self._auth.close()

    def to_dict(self) -> dict[str, Any]:
        """Return the API object data as a dictionary."""
        return {
            "user_id": self.user_id,
            "next_refresh": (
                self._auth.next_refresh.isoformat()
                if self._auth.next_refresh is not None
                else None
            ),
        }

    def __iter__(self) -> Iterator[tuple[str, Any]]:
        """Allow ``dict(api)`` conversion."""
        return iter(self.to_dict().items())
