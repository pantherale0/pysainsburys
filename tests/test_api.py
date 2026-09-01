"""Tests for the API module."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from pysainsburys.api import API
from pysainsburys.auth import GOLAuth


@pytest.fixture
def mock_auth() -> MagicMock:
    """Fixture for a mocked GOLAuth object."""
    mock = MagicMock(spec=GOLAuth)
    mock.user_id = "682092082"
    mock.next_refresh = None
    mock.authenticated_headers = {"Authorization": "Bearer test_token"}
    mock.send_request = AsyncMock(return_value={"status": "success"})
    mock.send_public_request = AsyncMock(return_value={"products": [], "controls": {}})
    mock.send_refresh_request = AsyncMock(return_value=None)
    mock.exchange_commerce_session = AsyncMock(return_value={"user_id": "682092082"})
    mock.close = AsyncMock(return_value=None)
    mock.session = MagicMock()
    return mock


@pytest.fixture
def api(mock_auth: MagicMock) -> API:
    """Fixture for the API object."""
    return API(auth_obj=mock_auth)


@pytest.mark.asyncio
async def test_send_product_finder_request(api: API, mock_auth: MagicMock) -> None:
    """Product Finder requests use the dedicated base URL."""
    mock_auth.send_public_request.return_value = {"content": []}
    response = await api.send_product_finder_request(
        "/v3/stores",
        params={"lat": 51.5, "lon": -0.12, "page": 1, "size": 5},
    )
    mock_auth.send_public_request.assert_awaited_once()
    call_kwargs = mock_auth.send_public_request.await_args.kwargs
    assert "product-finder/v3/stores" in call_kwargs["url"]
    assert response == {"content": []}


@pytest.mark.asyncio
async def test_send_public_request(api: API, mock_auth: MagicMock) -> None:
    """Public requests bypass commerce session requirements."""
    response = await api.send_public_request(
        endpoint="search_products",
        params={"filter[keyword]": "milk"},
    )
    mock_auth.send_public_request.assert_awaited_once()
    assert response == {"products": [], "controls": {}}


@pytest.mark.asyncio
async def test_send_request_passes_endpoint_headers(api: API, mock_auth: MagicMock) -> None:
    """Endpoint-specific headers are forwarded to the auth layer."""
    await api.send_request(
        endpoint="list_slots",
        body={"slot_type": "delivery"},
    )
    mock_auth.send_request.assert_awaited_once()
    call_kwargs = mock_auth.send_request.await_args.kwargs
    assert call_kwargs["headers"] == {"X-Http-Method-Override": "GET"}
    assert call_kwargs["method"] == "POST"
    assert call_kwargs["url"].endswith("/slot/v2/slots")


@pytest.mark.asyncio
async def test_send_request(api: API, mock_auth: MagicMock) -> None:
    """Test the send_request method."""
    response = await api.send_request(endpoint="customer_profile")
    mock_auth.send_request.assert_awaited_once()
    assert response == {"status": "success"}


@pytest.mark.asyncio
async def test_send_request_unknown_endpoint(api: API) -> None:
    """Unknown endpoints raise ValueError."""
    with pytest.raises(ValueError, match="does not exist"):
        await api.send_request(endpoint="not_real")


@pytest.mark.asyncio
async def test_token_refresh(api: API, mock_auth: MagicMock) -> None:
    """Test the token_refresh method."""
    await api.token_refresh()
    mock_auth.send_refresh_request.assert_awaited_once()


@pytest.mark.asyncio
async def test_exchange_commerce_session(api: API, mock_auth: MagicMock) -> None:
    """Test commerce session exchange."""
    response = await api.exchange_commerce_session()
    mock_auth.exchange_commerce_session.assert_awaited_once()
    assert response["user_id"] == "682092082"


def test_user_id(api: API) -> None:
    """Test the user_id property."""
    assert api.user_id == "682092082"


def test_to_dict(api: API) -> None:
    """Test the to_dict method."""
    result = api.to_dict()
    assert result["user_id"] == "682092082"


def test_iter(api: API) -> None:
    """Test the __iter__ method."""
    api_dict = dict(api)
    assert api_dict["user_id"] == "682092082"
