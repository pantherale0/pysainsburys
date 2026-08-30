from unittest.mock import AsyncMock

import pytest

from pysainsburys.client import Client
from pysainsburys.config import COMM_PROTOCOL, Config


@pytest.mark.asyncio
async def test_client_connect_and_disconnect() -> None:
    """The client delegates connect/disconnect to the adapter."""
    client = Client()
    client._adapter.connect = AsyncMock()
    client._adapter.disconnect = AsyncMock()

    await client.connect()
    await client.disconnect()

    client._adapter.connect.assert_awaited_once()
    client._adapter.disconnect.assert_awaited_once()


@pytest.mark.asyncio
async def test_client_context_manager() -> None:
    """The async context manager connects on enter and disconnects on exit."""
    client = Client()
    client._adapter.connect = AsyncMock()
    client._adapter.disconnect = AsyncMock()

    async with client:
        client._adapter.connect.assert_awaited_once()

    client._adapter.disconnect.assert_awaited_once()


def test_protocol_constant() -> None:
    """The generated protocol matches the template selection."""
    assert COMM_PROTOCOL == "http"


def test_config_defaults() -> None:
    """Config can be constructed with defaults."""
    config = Config()
    assert config is not None
