import json
import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated, Any

from mcp.server.fastmcp import FastMCP
from pydantic import Field, TypeAdapter

from attackmate.schemas.command_subtypes import RemotelyExecutableCommand
from attackmate.schemas.command_types import Command

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

# Covers all types including 'remote' (valid in playbooks but not via execute_command).
# Used for schema exploration tools and resources only.
_full_schema = TypeAdapter(Command).json_schema()

# Pre-compute type → schema mapping so get_command_schema is a single dict lookup.
# Sliver types are doubly-discriminated (type + cmd); keep one representative
# schema per type rather than replicating the inner cmd union. TODO fix this in attackmate repo
_schema_by_type: dict[str, Any] = {}
for _def in _full_schema.get('$defs', {}).values():
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

    Note: the 'remote' type is only valid inside a playbook (run_playbook), not
    as a standalone execute_command call.
    """
    return _full_schema


# ---------------------------------------------------------------------------
# Resources - per-executor documentation (RST source)
# ---------------------------------------------------------------------------

# Types where the RST filename differs from the type discriminator value.
# All other types map to playbook/commands/{type}.rst by convention.
_DOC_FILENAME_OVERRIDES: dict[str, str] = {
    'http-client': 'httpclient',
    'msf-payload': 'payload',
}

_PLAYBOOK_DOC_FILES: dict[str, str] = {
    'structure': 'playbook/structure.rst',
    'vars': 'playbook/vars.rst',
    'examples': 'playbook/examples.rst',
}


def _command_doc_path(command_type: str) -> str:
    filename = _DOC_FILENAME_OVERRIDES.get(command_type, command_type)
    return f'playbook/commands/{filename}.rst'


# Warn at startup about any schema types whose doc file is missing on disk.
if settings.attackmate_docs_path:
    for _type in _schema_by_type:
        _doc_file = Path(settings.attackmate_docs_path) / _command_doc_path(_type)
        if not _doc_file.exists():
            logger.warning(
                "No documentation file for command type '%s': %s", _type, _doc_file
            )


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
    if command_type not in _schema_by_type:
        available = ', '.join(sorted(_schema_by_type))
        return f"Unknown command type '{command_type}'. Available: {available}"
    return _read_rst(_command_doc_path(command_type))


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
        available = ', '.join(sorted(_schema_by_type))
        return f"Schema not found for '{command_type}'. Available types: {available}"
    return json.dumps(def_schema, indent=2)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def run() -> None:
    if not settings.ssl_verify:
        logger.warning(
            'SSL_VERIFY is disabled. TLS certificates will not be validated. '
            'Set SSL_VERIFY=true in .env unless the AttackMate API uses a self-signed certificate.'
        )
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
