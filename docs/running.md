# Running

## Prerequisites

- Python >= 3.13 and `uv` installed
- `.env` configured with at least `API_USERNAME` and `API_PASSWORD`
- AttackMate running with its REST API accessible at `API_BASE_URL`

## stdio (default)

The default transport is stdio. The MCP client spawns the server as a subprocess and communicates over stdin/stdout.

```bash
uv run attackmate-mcp
```

No additional configuration is needed. This is the mode used by Claude Desktop, Cursor, and VS Code.

## SSE transport

Server-Sent Events transport runs an HTTP server that MCP clients connect to over the network.

Set in `.env`:

```
MCP_TRANSPORT=sse
MCP_HOST=127.0.0.1   # default, change only if remote clients need access
MCP_PORT=8000         # default
```

Then run:

```bash
uv run attackmate-mcp
```

The server listens at `http://<MCP_HOST>:<MCP_PORT>/sse`. MCP clients connect to this URL.

!!! warning
    Setting `MCP_HOST` to anything other than `127.0.0.1` / `localhost` / `::1` disables DNS rebinding protection. Do not expose the SSE endpoint on an untrusted network.

## Development mode

Use the MCP Inspector for interactive testing:

```bash
uv run mcp dev main.py
```

This opens a browser-based inspector where you can call tools and inspect responses directly without a full MCP client.

## Entry points

| Command | Description |
|---|---|
| `uv run attackmate-mcp` | Start via the installed CLI entry point |
| `uv run python main.py` | Start directly via the main module |
| `uv run mcp dev main.py` | Start with the MCP Inspector (development) |
