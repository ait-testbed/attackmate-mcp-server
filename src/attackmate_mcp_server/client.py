import logging
from typing import Any

import httpx

from .config import settings

# None → no timeout; a float → seconds
def _command_timeout() -> float | None:
    t = settings.command_timeout
    return None if (t is None or t == 0) else t

logger = logging.getLogger(__name__)

_API_TOKEN_HEADER = "X-Auth-Token"


class AttackMateAPIClient:
    def __init__(self) -> None:
        self._token: str | None = None
        self._http = httpx.AsyncClient(
            base_url=settings.api_base_url,
            verify=settings.ssl_verify,
        )

    async def _login(self) -> None:
        logger.info("Authenticating with AttackMate API...")
        resp = await self._http.post(
            "/login",
            data={"username": settings.api_username, "password": settings.api_password},
        )
        resp.raise_for_status()
        self._token = resp.json()["access_token"]
        logger.info("Authentication successful.")

    async def _request(
        self, method: str, path: str, timeout: float | None = httpx.USE_CLIENT_DEFAULT, **kwargs: Any
    ) -> dict[str, Any]:
        if self._token is None:
            await self._login()
        headers = kwargs.pop("headers", {})
        headers[_API_TOKEN_HEADER] = self._token
        resp = await self._http.request(method, path, headers=headers, timeout=timeout, **kwargs)
        if resp.status_code == 401:
            # Token expired — re-authenticate once and retry
            logger.info("Token expired, re-authenticating...")
            self._token = None
            await self._login()
            headers[_API_TOKEN_HEADER] = self._token
            resp = await self._http.request(method, path, headers=headers, timeout=timeout, **kwargs)
        resp.raise_for_status()
        return resp.json()  # type: ignore[return-value]

    async def execute_command(self, command_data: dict[str, Any]) -> dict[str, Any]:
        return await self._request("POST", "/command/execute", json=command_data, timeout=_command_timeout())

    async def run_playbook(self, playbook_yaml: str, debug: bool = False) -> dict[str, Any]:
        return await self._request(
            "POST",
            "/playbooks/execute/yaml",
            content=playbook_yaml,
            params={"debug": debug},
            headers={"Content-Type": "application/yaml"},
            timeout=_command_timeout(),
        )

    async def get_variable_store(self) -> dict[str, Any]:
        return await self._request("GET", "/instances/state")

    async def close(self) -> None:
        await self._http.aclose()
