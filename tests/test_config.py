"""Tests for config.py - Settings loading and _to_timeout helper."""
import pytest
from pydantic import ValidationError

from attackmate_mcp_server.client import _to_timeout
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

    def test_missing_fields_error_has_wrapper_compatible_structure(self, monkeypatch):
        """The ValidationError structure matches what the module-level RuntimeError wrapper expects."""
        monkeypatch.delenv('API_USERNAME', raising=False)
        monkeypatch.delenv('API_PASSWORD', raising=False)
        with pytest.raises(ValidationError) as exc_info:
            IsolatedSettings()
        missing = [str(e['loc'][0]) for e in exc_info.value.errors() if e['type'] == 'missing']
        assert missing, "Expected 'missing'-type errors, wrapper filter would silently skip them"
        message = f"Missing required configuration: {', '.join(missing)}"
        assert any(f in message for f in ('API_USERNAME', 'API_PASSWORD'))


class TestToTimeoutHelper:
    @pytest.mark.parametrize('value,expected', [
        (None, None),
        (0, None),
        (0.0, None),
        (300.0, 300.0),
        (60.0, 60.0),
    ])
    def test_values(self, value, expected):
        assert _to_timeout(value) == expected
