"""Shared fixtures and helpers for all test modules."""
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest
from pydantic_settings import SettingsConfigDict

from attackmate_mcp_server.client import AttackMateAPIClient
from attackmate_mcp_server.config import Settings


class IsolatedSettings(Settings):
    """Settings subclass that ignores the .env file - reads only from environment variables."""

    model_config = SettingsConfigDict(
        env_file=None,
        env_file_encoding='utf-8',
        extra='ignore',
    )


def make_settings(monkeypatch, **overrides):
    """Build an IsolatedSettings with the given env-var overrides (plus required defaults)."""
    env = {'API_USERNAME': 'user', 'API_PASSWORD': 'pass', **overrides}
    for key, value in env.items():
        monkeypatch.setenv(key, str(value))
    return IsolatedSettings()


def make_response(status_code: int = 200, json_data=None, text: str = '') -> MagicMock:
    """Build a mock httpx.Response."""
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = status_code
    resp.json.return_value = json_data if json_data is not None else {'ok': True}
    resp.text = text
    if status_code >= 400:
        resp.raise_for_status.side_effect = httpx.HTTPStatusError(
            'error', request=MagicMock(), response=resp
        )
    else:
        resp.raise_for_status.return_value = None
    return resp


# ---------------------------------------------------------------------------
# Client fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def client():
    return AttackMateAPIClient()


@pytest.fixture
async def mock_http(client):
    """Replace the internal httpx transport with async mocks, closing the real client on teardown."""
    real_http = client._http
    mock = MagicMock()
    mock.post = AsyncMock()
    mock.request = AsyncMock()
    mock.aclose = AsyncMock()
    client._http = mock
    yield mock
    await real_http.aclose()


@pytest.fixture
def authed_client(client, mock_http):
    """Client with a pre-set token and fully mocked HTTP transport."""
    client._token = 'valid-token'
    return client, mock_http


# ---------------------------------------------------------------------------
# Server fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_api_client(monkeypatch):
    """Patch _get_client() to return an AsyncMock with canned return values."""
    mock = AsyncMock()
    mock.execute_command.return_value = {'result': 'ok'}
    mock.run_playbook.return_value = {'success': True}
    mock.get_variable_store.return_value = {'vars': {}}
    monkeypatch.setattr('attackmate_mcp_server.server._get_client', lambda: mock)
    return mock
