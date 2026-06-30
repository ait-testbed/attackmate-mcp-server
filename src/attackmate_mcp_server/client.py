import asyncio
import logging
from typing import Any

import httpx

from .config import settings

# None → no timeout; a float → seconds


def _to_timeout(value: float | None) -> float | None:
    return None if (value is None or value == 0) else value


logger = logging.getLogger(__name__)

_API_TOKEN_HEADER = 'X-Auth-Token'


class AttackMateAPIClient:
    def __init__(self) -> None:
        self._token: str | None = None
        self._auth_lock = asyncio.Lock()
        self._http = httpx.AsyncClient(
            base_url=settings.api_base_url,
            verify=settings.ssl_verify,
        )

    async def _login(self) -> None:
        logger.info('Authenticating with AttackMate API...')
        resp = await self._http.post(
            '/login',
            data={'username': settings.api_username, 'password': settings.api_password},
        )
        resp.raise_for_status()
        token = resp.json().get('access_token')
        if not token:
            raise RuntimeError(f"Login response missing 'access_token': {resp.text[:200]}")
        self._token = token
        logger.info('Authentication successful.')

    async def _ensure_token(self, invalidate: str | None = None) -> None:
        """Ensure a valid token is held, with at-most-one concurrent login.

        If `invalidate` is supplied (the stale token that triggered a 401), re-login
        only when the current token still matches, another task may already have refreshed it
        """
        async with self._auth_lock:
            if invalidate is not None:
                if self._token != invalidate:
                    return  # another task already refreshed the token
                self._token = None
            if self._token is None:
                await self._login()

    async def _request(
        self, method: str, path: str, timeout: float | None = httpx.USE_CLIENT_DEFAULT, **kwargs: Any
    ) -> dict[str, Any]:
        try:
            await self._ensure_token()
            headers = kwargs.pop('headers', {})
            headers[_API_TOKEN_HEADER] = self._token
            resp = await self._http.request(method, path, headers=headers, timeout=timeout, **kwargs)
            if resp.status_code == 401:
                logger.info('Token expired, re-authenticating...')
                await self._ensure_token(invalidate=headers[_API_TOKEN_HEADER])
                headers[_API_TOKEN_HEADER] = self._token
                resp = await self._http.request(method, path, headers=headers, timeout=timeout, **kwargs)
            resp.raise_for_status()
            return resp.json()  # type: ignore[return-value]
        except httpx.TimeoutException as exc:
            raise RuntimeError(
                f'Request timed out ({timeout}s). '
                'Raise COMMAND_TIMEOUT or PLAYBOOK_TIMEOUT in .env, or set to 0 to disable.'
            ) from exc
        except httpx.ConnectError as exc:
            raise RuntimeError(
                f'Cannot connect to AttackMate API at {settings.api_base_url}. '
                'Check that the server is running and API_BASE_URL is correct.'
            ) from exc
        except httpx.HTTPStatusError as exc:
            raise RuntimeError(
                f'AttackMate API error {exc.response.status_code} for {method} {path}: '
                f'{exc.response.text}'
            ) from exc
        except ValueError as exc:
            raise RuntimeError(
                f'AttackMate API returned non-JSON response for {method} {path}.'
            ) from exc

    async def execute_command(self, command_data: dict[str, Any]) -> dict[str, Any]:
        return await self._request(
            'POST', '/command/execute', json=command_data,
            timeout=_to_timeout(settings.command_timeout),
        )

    async def run_playbook(self, playbook_yaml: str, debug: bool = False) -> dict[str, Any]:
        return await self._request(
            'POST',
            '/playbooks/execute/yaml',
            content=playbook_yaml,
            params={'debug': debug},
            headers={'Content-Type': 'application/yaml'},
            timeout=_to_timeout(settings.playbook_timeout),
        )

    async def get_variable_store(self) -> dict[str, Any]:
        return await self._request('GET', '/instances/state')

    async def close(self) -> None:
        await self._http.aclose()
