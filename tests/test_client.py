"""Tests for client.py - AttackMateAPIClient."""
from unittest.mock import MagicMock

import httpx
import pytest

from tests.conftest import make_response


class TestLogin:
    async def test_success_stores_token(self, client, mock_http):
        mock_http.post.return_value = make_response(json_data={'access_token': 'mytoken'})
        await client._login()
        assert client._token == 'mytoken'

    async def test_missing_access_token_raises(self, client, mock_http):
        mock_http.post.return_value = make_response(json_data={})
        with pytest.raises(RuntimeError, match='access_token'):
            await client._login()

    async def test_http_error_propagates(self, client, mock_http):
        mock_http.post.return_value = make_response(status_code=401)
        with pytest.raises(httpx.HTTPStatusError):
            await client._login()


class TestEnsureToken:
    async def test_calls_login_when_no_token(self, client, mock_http):
        mock_http.post.return_value = make_response(json_data={'access_token': 'tok'})
        await client._ensure_token()
        mock_http.post.assert_awaited_once()
        assert client._token == 'tok'

    async def test_skips_login_when_token_present(self, client, mock_http):
        client._token = 'existing'
        await client._ensure_token()
        mock_http.post.assert_not_called()

    async def test_invalidate_matching_triggers_relogin(self, client, mock_http):
        client._token = 'old-token'
        mock_http.post.return_value = make_response(json_data={'access_token': 'new-token'})
        await client._ensure_token(invalidate='old-token')
        mock_http.post.assert_awaited_once()
        assert client._token == 'new-token'

    async def test_invalidate_stale_skips_relogin(self, client, mock_http):
        client._token = 'already-refreshed'
        await client._ensure_token(invalidate='old-token')
        mock_http.post.assert_not_called()
        assert client._token == 'already-refreshed'


class TestRequest:
    async def test_success_returns_json(self, authed_client):
        client, mock_http = authed_client
        mock_http.request.return_value = make_response(json_data={'data': 'value'})
        result = await client._request('GET', '/test')
        assert result == {'data': 'value'}

    async def test_401_triggers_reauth_and_retries(self, authed_client):
        client, mock_http = authed_client
        mock_http.post.return_value = make_response(json_data={'access_token': 'new-token'})
        resp_401 = MagicMock(spec=httpx.Response)
        resp_401.status_code = 401
        resp_ok = make_response(json_data={'retried': True})
        mock_http.request.side_effect = [resp_401, resp_ok]

        result = await client._request('GET', '/test')

        assert result == {'retried': True}
        assert mock_http.request.await_count == 2
        mock_http.post.assert_awaited_once()
        assert client._token == 'new-token'
        second_call_headers = mock_http.request.call_args_list[1].kwargs['headers']
        assert second_call_headers['X-Auth-Token'] == 'new-token'

    @pytest.mark.parametrize('exc_type,match', [
        (httpx.TimeoutException, 'COMMAND_TIMEOUT'),
        (httpx.ConnectError, 'API_BASE_URL'),
    ])
    async def test_network_errors_become_runtime_error(self, authed_client, exc_type, match):
        client, mock_http = authed_client
        mock_http.request.side_effect = exc_type('simulated')
        with pytest.raises(RuntimeError, match=match):
            await client._request('GET', '/test')

    async def test_http_status_error_includes_status_code(self, authed_client):
        client, mock_http = authed_client
        mock_http.request.return_value = make_response(status_code=500, text='boom')
        with pytest.raises(RuntimeError, match='500'):
            await client._request('GET', '/test')

    async def test_non_json_response_raises(self, authed_client):
        client, mock_http = authed_client
        resp = make_response()
        resp.json.side_effect = ValueError('not json')
        mock_http.request.return_value = resp
        with pytest.raises(RuntimeError, match='non-JSON'):
            await client._request('GET', '/test')


class TestPublicMethods:
    async def test_execute_command(self, authed_client):
        client, mock_http = authed_client
        mock_http.request.return_value = make_response(json_data={'success': True})
        await client.execute_command({'type': 'debug', 'cmd': 'test'})
        args, kwargs = mock_http.request.call_args
        assert args == ('POST', '/command/execute')
        assert kwargs['json'] == {'type': 'debug', 'cmd': 'test'}

    async def test_run_playbook_default_debug_false(self, authed_client):
        client, mock_http = authed_client
        mock_http.request.return_value = make_response()
        await client.run_playbook('yaml: content')
        args, kwargs = mock_http.request.call_args
        assert args == ('POST', '/playbooks/execute/yaml')
        assert kwargs['content'] == 'yaml: content'
        assert kwargs['params'] == {'debug': False}
        assert kwargs['headers']['Content-Type'] == 'application/yaml'

    async def test_run_playbook_debug_true(self, authed_client):
        client, mock_http = authed_client
        mock_http.request.return_value = make_response()
        await client.run_playbook('yaml', debug=True)
        assert mock_http.request.call_args.kwargs['params'] == {'debug': True}

    async def test_get_variable_store(self, authed_client):
        client, mock_http = authed_client
        mock_http.request.return_value = make_response(json_data={'vars': {}})
        await client.get_variable_store()
        args, _ = mock_http.request.call_args
        assert args == ('GET', '/instances/state')
