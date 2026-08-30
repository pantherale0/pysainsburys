"""Low-level http connection handling."""

from __future__ import annotations

from abc import ABC, abstractmethod
from types import TracebackType

from .config import Config

_NOT_CONNECTED = "You're not connected yet — call connect() first."
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import aiohttp


class Adapter(ABC):
    """Common connect/disconnect behaviour for HTTP adapters."""

    @abstractmethod
    async def connect(self) -> None: ...

    @abstractmethod
    async def disconnect(self) -> None: ...

    async def __aenter__(self) -> Adapter:
        await self.connect()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        await self.disconnect()


class HttpAdapter(Adapter):
    """Talk to a remote HTTP API through aiohttp."""

    def __init__(self, config: Config) -> None:
        self._config = config
        self._session: aiohttp.ClientSession | None = None

    @property
    def session(self) -> aiohttp.ClientSession:
        """The aiohttp session, available after `connect()`."""
        if self._session is None:
            raise RuntimeError(_NOT_CONNECTED)
        return self._session

    async def connect(self) -> None:
        import aiohttp

        self._session = aiohttp.ClientSession(base_url=self._config.base_url)

    async def disconnect(self) -> None:
        if self._session is not None:
            await self._session.close()
            self._session = None


def create_adapter(config: Config) -> Adapter:
    return HttpAdapter(config)
