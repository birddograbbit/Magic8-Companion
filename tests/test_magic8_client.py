import pytest
import json
import aiohttp # Required for type hinting if not already there
import aiofiles # Required for type hinting
from unittest.mock import patch, mock_open, AsyncMock
from magic8_companion.modules.magic8_client import get_latest_magic8_data, fetch_from_file, fetch_from_http
from magic8_companion.config import settings

@pytest.mark.asyncio
async def test_fetch_from_file_success():
    mock_data = {"key": "value"}
    mock_content = json.dumps(mock_data)

    async_file_mock = AsyncMock()
    async_file_mock.read.return_value = mock_content

    async_context_manager_mock = AsyncMock()
    async_context_manager_mock.__aenter__.return_value = async_file_mock

    with patch('aiofiles.open', return_value=async_context_manager_mock) as mock_aio_open:
        result = await fetch_from_file("dummy/path.json")
        mock_aio_open.assert_called_once_with("dummy/path.json", 'r')
        assert result == mock_data

@pytest.mark.asyncio
async def test_fetch_from_file_not_found():
    with patch('aiofiles.open', side_effect=FileNotFoundError) as mock_aio_open:
        result = await fetch_from_file("dummy/nonexistent.json")
        mock_aio_open.assert_called_once_with("dummy/nonexistent.json", 'r')
        assert result is None

@pytest.mark.asyncio
async def test_fetch_from_http_success():
    mock_data = {"key": "http_value"}

    mock_resp = AsyncMock()
    mock_resp.status = 200
    mock_resp.json.return_value = mock_data

    async_get_context_manager = AsyncMock()
    async_get_context_manager.__aenter__.return_value = mock_resp

    mock_session = AsyncMock()
    mock_session.get.return_value = async_get_context_manager

    async_session_context_manager = AsyncMock()
    async_session_context_manager.__aenter__.return_value = mock_session

    with patch('aiohttp.ClientSession', return_value=async_session_context_manager) as mock_client_session:
        result = await fetch_from_http("http://dummyurl.com")
        mock_client_session.assert_called_once()
        mock_session.get.assert_called_once_with("http://dummyurl.com")
        assert result == mock_data

@pytest.mark.asyncio
async def test_fetch_from_http_failure():
    mock_resp = AsyncMock()
    mock_resp.status = 404

    async_get_context_manager = AsyncMock()
    async_get_context_manager.__aenter__.return_value = mock_resp

    mock_session = AsyncMock()
    mock_session.get.return_value = async_get_context_manager

    async_session_context_manager = AsyncMock()
    async_session_context_manager.__aenter__.return_value = mock_session

    with patch('aiohttp.ClientSession', return_value=async_session_context_manager) as mock_client_session:
        result = await fetch_from_http("http://dummyurl.com/fail")
        assert result is None

@pytest.mark.asyncio
async def test_get_latest_magic8_data_file_mode(monkeypatch):
    monkeypatch.setattr(settings, 'magic8_source', 'file')
    monkeypatch.setattr(settings, 'magic8_file_path', 'fake/path.json')

    expected_data = {"source": "file_data"}
    with patch('magic8_companion.modules.magic8_client.fetch_from_file', new_callable=AsyncMock) as mock_fetch_file:
        mock_fetch_file.return_value = expected_data
        result = await get_latest_magic8_data()
        mock_fetch_file.assert_called_once_with('fake/path.json')
        assert result == expected_data

@pytest.mark.asyncio
async def test_get_latest_magic8_data_http_mode(monkeypatch):
    monkeypatch.setattr(settings, 'magic8_source', 'http')
    monkeypatch.setattr(settings, 'magic8_url', 'http://fakeurl.com')

    expected_data = {"source": "http_data"}
    with patch('magic8_companion.modules.magic8_client.fetch_from_http', new_callable=AsyncMock) as mock_fetch_http:
        mock_fetch_http.return_value = expected_data
        result = await get_latest_magic8_data()
        mock_fetch_http.assert_called_once_with('http://fakeurl.com')
        assert result == expected_data

@pytest.mark.asyncio
async def test_get_latest_magic8_data_unknown_mode(monkeypatch):
    monkeypatch.setattr(settings, 'magic8_source', 'unknown')
    result = await get_latest_magic8_data()
    assert result is None
