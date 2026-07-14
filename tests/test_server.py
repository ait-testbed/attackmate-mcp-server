"""Tests for server.py - schema helpers, resource handlers, and MCP tools."""

import json
from unittest.mock import MagicMock, patch

import pytest

from attackmate_mcp_server.server import (
    _DOC_FILENAME_OVERRIDES,
    _PLAYBOOK_DOC_FILES,
    _command_doc_path,
    _read_rst,
    _schema_by_type,
    execute_command,
    get_command_doc,
    get_command_schema,
    get_playbook_doc,
    get_variable_store,
    list_command_types,
    run_playbook,
)


class TestSchemaHelpers:
    @pytest.mark.parametrize('cmd_type', ['shell', 'ssh', 'debug', 'sleep', 'msf-module'])
    def test_schema_by_type_has_known_types(self, cmd_type):
        assert cmd_type in _schema_by_type

    def test_list_command_types_returns_defs(self):
        result = list_command_types()
        assert isinstance(result, dict)
        assert '$defs' in result

    def test_get_command_schema_known_type_is_valid_json(self):
        result = get_command_schema('shell')
        parsed = json.loads(result)
        assert isinstance(parsed, dict)

    def test_get_command_schema_unknown_type_error_message(self):
        result = get_command_schema('not-a-real-type')
        assert 'not-a-real-type' in result
        assert 'Available' in result


class TestReadRst:
    def test_no_docs_path_returns_config_message(self):
        with patch('attackmate_mcp_server.server.settings') as s:
            s.attackmate_docs_path = None
            result = _read_rst('any/path.rst')
        assert 'ATTACKMATE_DOCS_PATH' in result

    def test_existing_file_returns_content(self, tmp_path):
        (tmp_path / 'test.rst').write_text('RST content')
        with patch('attackmate_mcp_server.server.settings') as s:
            s.attackmate_docs_path = tmp_path
            result = _read_rst('test.rst')
        assert result == 'RST content'

    def test_missing_file_returns_not_found_message(self, tmp_path):
        with patch('attackmate_mcp_server.server.settings') as s:
            s.attackmate_docs_path = tmp_path
            result = _read_rst('nonexistent.rst')
        assert 'not found' in result.lower()


class TestCommandDocPath:
    @pytest.mark.parametrize(
        'cmd_type,expected',
        [
            ('shell', 'playbook/commands/shell.rst'),
            ('ssh', 'playbook/commands/ssh.rst'),
            ('http-client', 'playbook/commands/httpclient.rst'),
            ('msf-payload', 'playbook/commands/payload.rst'),
            ('mktemp', 'playbook/commands/mktemp.rst'),
        ],
    )
    def test_path_derivation(self, cmd_type, expected):
        assert _command_doc_path(cmd_type) == expected

    def test_overrides_cover_only_exceptions(self):
        assert set(_DOC_FILENAME_OVERRIDES) == {'http-client', 'msf-payload'}


class TestDocResources:
    @pytest.fixture
    def docs_tree(self, tmp_path):
        """Populate tmp_path with RST stubs for all schema types and playbook topics."""
        for cmd_type in _schema_by_type:
            p = tmp_path / _command_doc_path(cmd_type)
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(f'stub:{_command_doc_path(cmd_type)}')
        for rel_path in _PLAYBOOK_DOC_FILES.values():
            p = tmp_path / rel_path
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(f'stub:{rel_path}')
        return tmp_path

    @pytest.mark.parametrize('cmd_type', ['shell', 'ssh', 'debug', 'msf-payload', 'mktemp'])
    def test_get_command_doc_known(self, docs_tree, cmd_type):
        with patch('attackmate_mcp_server.server.settings') as s:
            s.attackmate_docs_path = docs_tree
            result = get_command_doc(cmd_type)
        assert result == f'stub:{_command_doc_path(cmd_type)}'

    def test_get_command_doc_unknown(self):
        result = get_command_doc('not-a-type')
        assert 'not-a-type' in result
        assert 'Available' in result

    @pytest.mark.parametrize('topic', ['structure', 'vars', 'examples'])
    def test_get_playbook_doc_known(self, docs_tree, topic):
        with patch('attackmate_mcp_server.server.settings') as s:
            s.attackmate_docs_path = docs_tree
            result = get_playbook_doc(topic)
        assert result == f'stub:{_PLAYBOOK_DOC_FILES[topic]}'

    def test_get_playbook_doc_unknown(self):
        result = get_playbook_doc('not-a-topic')
        assert 'not-a-topic' in result
        assert 'Available' in result


class TestTools:
    async def test_execute_command_delegates_to_client(self, mock_api_client):
        cmd = MagicMock()
        cmd.model_dump.return_value = {'type': 'debug', 'cmd': 'test'}
        result = await execute_command(cmd)
        cmd.model_dump.assert_called_once_with(mode='json', exclude_none=True)
        mock_api_client.execute_command.assert_awaited_once_with({'type': 'debug', 'cmd': 'test'})
        assert result == {'result': 'ok'}

    async def test_run_playbook_delegates_to_client(self, mock_api_client):
        result = await run_playbook('yaml: content', debug=True)
        mock_api_client.run_playbook.assert_awaited_once_with('yaml: content', debug=True)
        assert result == {'success': True}

    async def test_get_variable_store_delegates_to_client(self, mock_api_client):
        result = await get_variable_store()
        mock_api_client.get_variable_store.assert_awaited_once()
        assert result == {'vars': {}}
