# AttackMate MCP Server

An [MCP (Model Context Protocol)](https://modelcontextprotocol.io) server that bridges LLMs with [AttackMate](https://github.com/ait-testbed/attackmate), a cybersecurity attack automation framework. It exposes AttackMate's command execution and playbook capabilities as MCP tools, allowing an LLM to drive attack scenarios interactively against a running AttackMate instance.

## How it works

The server connects to the AttackMate REST API and wraps it in four MCP tools:

- **execute_command** - send a single typed command to a persistent AttackMate instance
- **run_playbook** - execute a full YAML playbook on a transient instance
- **get_variable_store** - read variables saved by previous commands
- **list_command_types** - inspect the full JSON schema for all supported command types

Documentation resources for all command types and playbook syntax are also available when the AttackMate source tree is present locally.

## Quick start

```bash
# 1. Install dependencies
uv sync

# 2. Configure credentials
cp env-example .env
# edit .env - set API_USERNAME and API_PASSWORD at minimum

# 3. Run
uv run attackmate-mcp
```

The server starts on stdio by default, ready to be picked up by any MCP client. See [Running](running.md) for transport options and [Connecting Agents](agents.md) for client-specific setup.

## Requirements

- Python >= 3.13
- [`uv`](https://docs.astral.sh/uv/)
- A running AttackMate instance with its REST API reachable
