"""High-level client for Sainsburys API."""

from __future__ import annotations

from types import TracebackType

from .adapter import Adapter, create_adapter
from .config import COMM_PROTOCOL, Config


class Client:
    """Talk to the remote system over http.

    Use it as an async context manager when you want connect/disconnect handled
    for you::

        async with Client(config) as client:
            ...  # work with client.adapter
    """

    def __init__(self, config: Config | None = None) -> None:
        self.config = config or Config()
        self._adapter: Adapter = create_adapter(self.config)

    @property
    def adapter(self) -> Adapter:
        """Low-level connection object for this protocol."""
        return self._adapter

    @property
    def protocol(self) -> str:
        """Selected communication protocol (``http``)."""
        return COMM_PROTOCOL

    async def connect(self) -> None:
        """Open the connection."""
        await self._adapter.connect()

    async def disconnect(self) -> None:
        """Close the connection."""
        await self._adapter.disconnect()

    async def __aenter__(self) -> Client:
        await self.connect()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        await self.disconnect()
