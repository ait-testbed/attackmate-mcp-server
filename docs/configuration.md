# Configuration

All configuration is read from a `.env` file in the repository root. Copy the example and fill in your values:

```bash
cp env-example .env
```

## Settings reference

| Variable | Required | Default | Description |
|---|---|---|---|
| `API_BASE_URL` | | `https://localhost:8445` | Base URL of the AttackMate REST API |
| `API_USERNAME` | yes | - | API username |
| `API_PASSWORD` | yes | - | API password |
| `SSL_VERIFY` | | `false` | `true`, `false`, or a path to a CA bundle. See note below. |
| `ATTACKMATE_DOCS_PATH` | | - | Path to the `docs/source` directory of the AttackMate source tree. Enables documentation resources. |
| `COMMAND_TIMEOUT` | | `300` | Seconds to wait for a single `execute_command` call. Set to `0` to disable. |
| `PLAYBOOK_TIMEOUT` | | `1800` | Seconds to wait for a `run_playbook` call. Set to `0` to disable. |
| `MCP_TRANSPORT` | | `stdio` | Transport to use: `stdio` or `sse`. |
| `MCP_HOST` | | `127.0.0.1` | Host to bind to (SSE only). |
| `MCP_PORT` | | `8000` | Port to bind to (SSE only). |

## Notes

### SSL_VERIFY

AttackMate's API typically runs with a self-signed certificate in development, so `SSL_VERIFY` defaults to `false`. Set it to `true` in any environment where the API is reachable from untrusted networks, or point it to a CA bundle path.

The server logs a warning at startup if `SSL_VERIFY` is `false`.

### COMMAND_TIMEOUT vs PLAYBOOK_TIMEOUT

`execute_command` sends a single typed command - typically fast (seconds to a minute). `run_playbook` executes a full scenario that may run for many minutes. The two timeouts are independent so you can tighten `COMMAND_TIMEOUT` for fast feedback without interrupting long-running playbooks.

Set either to `0` to disable the timeout entirely.

### ATTACKMATE_DOCS_PATH

When set, the server serves RST documentation from the AttackMate source tree as MCP resources:

- `attackmate://docs/commands/{type}` - field-level docs for each executor
- `attackmate://docs/playbook/structure` - playbook format reference
- `attackmate://docs/playbook/vars` - variable syntax
- `attackmate://docs/playbook/examples` - example playbooks

Point this to `attackmate/docs/source` in a local clone of the AttackMate repository:

```
ATTACKMATE_DOCS_PATH=/path/to/attackmate/docs/source
```

The server warns at startup for any command type whose documentation file is missing.

### SSE transport

When `MCP_TRANSPORT=sse` the server binds an HTTP server. If `MCP_HOST` is set to anything other than `127.0.0.1`, `localhost`, or `::1`, the server logs a security warning because DNS rebinding protection is disabled for external addresses. Do not expose the SSE endpoint on an untrusted network.
