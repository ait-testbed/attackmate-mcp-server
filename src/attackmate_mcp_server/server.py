import json
import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated, Any

from mcp.server.fastmcp import FastMCP
from pydantic import Field, TypeAdapter

from attackmate.schemas.command_subtypes import RemotelyExecutableCommand

from .client import AttackMateAPIClient
from .config import settings

logger = logging.getLogger(__name__)


@asynccontextmanager
async def _lifespan(server: FastMCP):
    yield
    if _client is not None:
        await _client.close()
        logger.info('AttackMate API client closed.')


mcp = FastMCP('AttackMate', lifespan=_lifespan)

# Eagerly build the schema so any generation errors surface at startup
_command_adapter = TypeAdapter(RemotelyExecutableCommand)
_command_schema = _command_adapter.json_schema()

# Pre-compute type, schema mapping so get_command_schema is a single dict lookup
_schema_by_type: dict[str, Any] = {}
for _def in _command_schema.get('$defs', {}).values():
    _type_prop = _def.get('properties', {}).get('type', {})
    _key = _type_prop.get('const') or _type_prop.get('default')
    if _key:
        _schema_by_type[_key] = _def

# Singleton client - created on first tool call
_client: AttackMateAPIClient | None = None


def _get_client() -> AttackMateAPIClient:
    global _client
    if _client is None:
        _client = AttackMateAPIClient()
    return _client


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------

@mcp.tool()
async def execute_command(
    command: Annotated[
        RemotelyExecutableCommand,
        Field(description=(
            "The AttackMate command to execute. Set 'type' to select the executor "
            "(e.g. 'shell', 'ssh', 'msf-module'). "
            'Fetch attackmate://docs/commands/{type} for per-executor field details.'
        )),
    ]
) -> dict[str, Any]:
    """Execute a single AttackMate command on the persistent instance.

    Returns the command result (stdout, returncode, success) and the current
    variable store state after execution.
    """
    client = _get_client()
    command_dict = command.model_dump(mode='json', exclude_none=True)
    return await client.execute_command(command_dict)


@mcp.tool()
async def run_playbook(
    playbook_yaml: Annotated[str, Field(description=(
        'Full YAML content of the AttackMate playbook. '
        'Fetch attackmate://docs/playbook/structure for the playbook format. '
        'Fetch attackmate://docs/playbook/examples for ready-made examples.'
    ))],
    debug: Annotated[bool, Field(description=(
        'Enable DEBUG log level for this execution. '
        'When true, attackmate_log in the response contains verbose framework output.'
    ))] = False,
) -> dict[str, Any]:
    """Execute an AttackMate playbook from YAML content using a transient instance.

    Returns success, returncode, output_log, attackmate_log, and final variable store state.
    """
    client = _get_client()
    return await client.run_playbook(playbook_yaml, debug=debug)


@mcp.tool()
async def get_variable_store() -> dict[str, Any]:
    """Read the current variable store of the persistent AttackMate instance.

    Variables saved by previous commands (via 'saves_result_to') are available here.
    Fetch attackmate://docs/playbook/vars for variable syntax documentation.
    """
    client = _get_client()
    return await client.get_variable_store()


@mcp.tool()
def list_command_types() -> dict[str, Any]:
    """Return the full JSON schema for all available AttackMate command types.

    The schema is a discriminated union on the 'type' field. Use it to understand
    which fields each executor type requires. Individual schemas are also accessible
    at attackmate://schema/{command_type}.
    """
    return _command_schema


# ---------------------------------------------------------------------------
# Resources - per-executor documentation (RST source)
# ---------------------------------------------------------------------------

# Maps the 'type' discriminator value to the relative RST path under docs/source/
_COMMAND_DOC_FILES: dict[str, str] = {
    'shell': 'playbook/commands/shell.rst',
    'ssh': 'playbook/commands/ssh.rst',
    'sftp': 'playbook/commands/sftp.rst',
    'msf-module': 'playbook/commands/msf-module.rst',
    'msf-session': 'playbook/commands/msf-session.rst',
    'msf-payload': 'playbook/commands/payload.rst',
    'sliver-session': 'playbook/commands/sliver-session.rst',
    'sliver': 'playbook/commands/sliver.rst',
    'browser': 'playbook/commands/browser.rst',
    'vnc': 'playbook/commands/vnc.rst',
    'httpclient': 'playbook/commands/httpclient.rst',
    'webserv': 'playbook/commands/webserv.rst',
    'bettercap': 'playbook/commands/bettercap.rst',
    'debug': 'playbook/commands/debug.rst',
    'setvar': 'playbook/commands/setvar.rst',
    'regex': 'playbook/commands/regex.rst',
    'sleep': 'playbook/commands/sleep.rst',
    'include': 'playbook/commands/include.rst',
    'loop': 'playbook/commands/loop.rst',
    'tempfile': 'playbook/commands/mktemp.rst',
    'father': 'playbook/commands/father.rst',
    'json': 'playbook/commands/json.rst',
    'remote': 'playbook/commands/remote.rst',
}

_PLAYBOOK_DOC_FILES: dict[str, str] = {
    'structure': 'playbook/structure.rst',
    'vars': 'playbook/vars.rst',
    'examples': 'playbook/examples.rst',
}


def _read_rst(relative_path: str) -> str:
    if not settings.attackmate_docs_path:
        return (
            'ATTACKMATE_DOCS_PATH is not configured. '
            'Set it in .env to the attackmate/docs/source directory.'
        )
    path = Path(settings.attackmate_docs_path) / relative_path
    if not path.exists():
        return f'Documentation file not found: {path}'
    return path.read_text()


@mcp.resource('attackmate://docs/commands/{command_type}')
def get_command_doc(command_type: str) -> str:
    """RST documentation for an AttackMate executor type (fields, examples, notes)."""
    rel_path = _COMMAND_DOC_FILES.get(command_type)
    if rel_path is None:
        available = ', '.join(sorted(_COMMAND_DOC_FILES))
        return f"Unknown command type '{command_type}'. Available: {available}"
    return _read_rst(rel_path)


@mcp.resource('attackmate://docs/playbook/{topic}')
def get_playbook_doc(topic: str) -> str:
    """RST documentation for AttackMate playbook topics: structure, vars, examples."""
    rel_path = _PLAYBOOK_DOC_FILES.get(topic)
    if rel_path is None:
        available = ', '.join(sorted(_PLAYBOOK_DOC_FILES))
        return f"Unknown topic '{topic}'. Available: {available}"
    return _read_rst(rel_path)


@mcp.resource('attackmate://schema/{command_type}')
def get_command_schema(command_type: str) -> str:
    """JSON schema for a specific AttackMate command type, extracted from the full union schema."""
    def_schema = _schema_by_type.get(command_type)
    if def_schema is None:
        available = ', '.join(sorted(_schema_by_type) or sorted(_COMMAND_DOC_FILES))
        return f"Schema not found for '{command_type}'. Available types: {available}"
    return json.dumps(def_schema, indent=2)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def run() -> None:
    if settings.mcp_transport == 'sse':
        mcp.settings.host = settings.mcp_host
        mcp.settings.port = settings.mcp_port
        # DNS rebinding protection is auto-enabled for localhost only;
        # clear it when binding to an external address.
        if settings.mcp_host not in ('127.0.0.1', 'localhost', '::1'):
            logger.warning(
                'MCP_HOST is set to %s (non-localhost). '
                'DNS rebinding protection has been disabled. '
                'Ensure this host is not reachable from untrusted networks.',
                settings.mcp_host,
            )
            mcp.settings.transport_security = None
        mcp.run(transport='sse')
    else:
        mcp.run(transport='stdio')


if __name__ == '__main__':
    run()
