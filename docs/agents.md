# Connecting Agents

The server supports two transports: **stdio** (default) and **SSE**. Most desktop clients use stdio. SSE is useful when the server runs on a separate host or when multiple clients share one instance.

---

## Claude Desktop

Claude Desktop connects to MCP servers over stdio. Edit the Claude Desktop configuration file:

- **macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows:** `%APPDATA%\Claude\claude_desktop_config.json`

Add an entry under `mcpServers`:

```json
{
  "mcpServers": {
    "attackmate": {
      "command": "uv",
      "args": [
        "--directory",
        "/absolute/path/to/attackmate-mcp-server",
        "run",
        "attackmate-mcp"
      ]
    }
  }
}
```

Replace `/absolute/path/to/attackmate-mcp-server` with the actual path to the repository on your machine. Restart Claude Desktop after saving.

---

## Cursor

Cursor supports MCP servers via a JSON config file. You can configure it globally or per-project.

**Global** (`~/.cursor/mcp.json`):

```json
{
  "mcpServers": {
    "attackmate": {
      "command": "uv",
      "args": [
        "--directory",
        "/absolute/path/to/attackmate-mcp-server",
        "run",
        "attackmate-mcp"
      ]
    }
  }
}
```

**Per-project** (`.cursor/mcp.json` in the project root):

Same format as above.

Restart Cursor (or reload the window) after saving.

---

## VS Code

VS Code with GitHub Copilot supports MCP servers via `.vscode/mcp.json` in the workspace root:

```json
{
  "servers": {
    "attackmate": {
      "type": "stdio",
      "command": "uv",
      "args": [
        "--directory",
        "/absolute/path/to/attackmate-mcp-server",
        "run",
        "attackmate-mcp"
      ]
    }
  }
}
```

MCP tool calls are available in Copilot Chat agent mode.

---

## SSE-based clients

For clients that connect over HTTP rather than spawning a subprocess, run the server in SSE mode:

```
MCP_TRANSPORT=sse
MCP_HOST=127.0.0.1
MCP_PORT=8000
```

```bash
uv run attackmate-mcp
```

The server then listens at `http://127.0.0.1:8000/sse`. Point your MCP client at this URL. The exact configuration key varies by client - look for an `url` or `endpoint` field in the MCP server settings.

---

## Environment variables per client

If you prefer not to use a `.env` file, most clients accept an `env` block in the server config. For example in Claude Desktop:

```json
{
  "mcpServers": {
    "attackmate": {
      "command": "uv",
      "args": [
        "--directory",
        "/absolute/path/to/attackmate-mcp-server",
        "run",
        "attackmate-mcp"
      ],
      "env": {
        "API_BASE_URL": "https://192.168.1.10:8445",
        "API_USERNAME": "admin",
        "API_PASSWORD": "secret",
        "SSL_VERIFY": "false"
      }
    }
  }
}
```

Values in `env` override anything in `.env`.
