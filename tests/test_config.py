"""Tests for config.py - Settings loading and _to_timeout helper."""

import pytest
from pydantic import ValidationError

from attackmate_mcp_server.client import _to_timeout
from attackmate_mcp_server.config import _load_settings
from tests.conftest import IsolatedSettings, make_settings


class TestSettingsDefaults:
    def test_defaults(self, monkeypatch):
        s = make_settings(monkeypatch)
        assert s.api_base_url == 'https://localhost:8445'
        assert s.ssl_verify is False
        assert s.command_timeout == 300.0
        assert s.playbook_timeout == 1800.0
        assert s.mcp_transport == 'stdio'
        assert s.mcp_host == '127.0.0.1'
        assert s.mcp_port == 8000
        assert s.attackmate_docs_path is None

    def test_ssl_verify_true(self, monkeypatch):
        s = make_settings(monkeypatch, SSL_VERIFY='true')
        assert s.ssl_verify is True

    def test_command_timeout_zero(self, monkeypatch):
        s = make_settings(monkeypatch, COMMAND_TIMEOUT='0')
        assert s.command_timeout == 0.0

    def test_playbook_timeout_override(self, monkeypatch):
        s = make_settings(monkeypatch, PLAYBOOK_TIMEOUT='3600')
        assert s.playbook_timeout == 3600.0

    def test_docs_path_parsed(self, monkeypatch, tmp_path):
        s = make_settings(monkeypatch, ATTACKMATE_DOCS_PATH=str(tmp_path))
        assert s.attackmate_docs_path == tmp_path

    @pytest.mark.parametrize('missing', ['API_USERNAME', 'API_PASSWORD'])
    def test_missing_required_field_raises(self, monkeypatch, missing):
        required = {'API_USERNAME': 'user', 'API_PASSWORD': 'pass'}
        required.pop(missing)
        for k, v in required.items():
            monkeypatch.setenv(k, v)
        monkeypatch.delenv(missing, raising=False)
        with pytest.raises(ValidationError):
            IsolatedSettings()

    def test_missing_required_field_becomes_runtime_error(self, monkeypatch):
        """_load_settings wraps a missing-field ValidationError into an actionable RuntimeError."""
        monkeypatch.delenv('API_USERNAME', raising=False)
        monkeypatch.delenv('API_PASSWORD', raising=False)
        with pytest.raises(RuntimeError, match='Missing required configuration') as exc_info:
            _load_settings(IsolatedSettings)
        assert 'API_USERNAME' in str(exc_info.value)
        assert 'API_PASSWORD' in str(exc_info.value)
        assert isinstance(exc_info.value.__cause__, ValidationError)

    def test_non_missing_validation_error_propagates_unwrapped(self, monkeypatch):
        """A ValidationError unrelated to missing fields (e.g. a bad literal) must not be masked."""
        monkeypatch.setenv('API_USERNAME', 'user')
        monkeypatch.setenv('API_PASSWORD', 'pass')
        monkeypatch.setenv('MCP_TRANSPORT', 'not-a-real-transport')
        with pytest.raises(ValidationError):
            _load_settings(IsolatedSettings)


class TestToTimeoutHelper:
    @pytest.mark.parametrize(
        'value,expected',
        [
            (None, None),
            (0, None),
            (0.0, None),
            (300.0, 300.0),
            (60.0, 60.0),
        ],
    )
    def test_values(self, value, expected):
        assert _to_timeout(value) == expected
