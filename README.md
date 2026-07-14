# attackmate-mcp-server

MCP server that exposes [AttackMate](https://github.com/ait-testbed/attackmate) to LLMs. Allows an LLM to execute commands and playbooks against a running AttackMate instance via its REST API.

## Requirements

- Python ≥ 3.13
- [`uv`](https://docs.astral.sh/uv/)
- A running AttackMate instance with its API reachable

## Setup

```bash
uv sync
cp env-example .env
# edit .env with your AttackMate API credentials
```

## Configuration (`.env`)

| Variable | Required | Default | Description |
|---|---|---|---|
| `API_BASE_URL` | | `https://localhost:8445` | AttackMate API base URL |
| `API_USERNAME` | yes | - | API username |
| `API_PASSWORD` | yes | - | API password |
| `SSL_VERIFY` | | `false` | `true`, `false`, or path to CA bundle |
| `ATTACKMATE_DOCS_PATH` | | - | Path to `attackmate/docs/source` to enable documentation resources |
| `COMMAND_TIMEOUT` | | `300` | Seconds to wait for a single `execute_command` call (`0` = no timeout) |
| `PLAYBOOK_TIMEOUT` | | `1800` | Seconds to wait for a `run_playbook` call (`0` = no timeout) |
| `MCP_TRANSPORT` | | `stdio` | `stdio` or `sse` |
| `MCP_HOST` | | `127.0.0.1` | Bind host (SSE only) |
| `MCP_PORT` | | `8000` | Bind port (SSE only) |

## Running

```bash
uv run attackmate-mcp
```

For SSE, set `MCP_TRANSPORT=sse` (and optionally `MCP_HOST`/`MCP_PORT`) in `.env` before running.

## MCP Tools

| Tool | Description |
|---|---|
| `execute_command` | Execute a single typed command on the persistent AttackMate instance |
| `run_playbook` | Run a YAML playbook on a transient instance |
| `get_variable_store` | Read the variable store of the persistent instance |
| `list_command_types` | Return the full JSON schema for all command types |

Documentation resources (`attackmate://docs/commands/{type}`, `attackmate://docs/playbook/{topic}`, `attackmate://schema/{type}`) are available when `ATTACKMATE_DOCS_PATH` is set.

## License

[EUPL-1.2](LICENSE.md)
