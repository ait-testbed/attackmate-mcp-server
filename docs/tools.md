# Tools & Resources

## Tools

### execute_command

Execute a single typed command on the **persistent** AttackMate instance.

```
execute_command(command: RemotelyExecutableCommand) -> dict
```

The `command` object must have a `type` field that selects the executor. All other fields depend on that type. The server validates the command against the Pydantic schema before sending it to the API, so type errors are caught before the network call.

Returns the command result (stdout, returncode, success) and the current variable store after execution.

!!! note
    The `remote` command type is not valid here - it can only appear inside a playbook. Use `run_playbook` for scenarios that include `remote` commands.

**Example - run a shell command:**

```json
{
  "type": "shell",
  "cmd": "whoami"
}
```

**Example - run a Metasploit module:**

```json
{
  "type": "msf-module",
  "cmd": "exploit/multi/samba/usermap_script",
  "RHOSTS": "192.168.1.10",
  "payload": "cmd/unix/bind_perl",
  "creates_session": "SHELL_SESSION"
}
```

---

### run_playbook

Execute a full AttackMate playbook from YAML content using a **transient** instance.

```
run_playbook(playbook_yaml: str, debug: bool = False) -> dict
```

- `playbook_yaml` - the complete YAML content of the playbook
- `debug` - when `true`, AttackMate runs at DEBUG log level; the response includes verbose framework output in `attackmate_log`

Returns: `success`, `returncode`, `output_log`, `attackmate_log`, and the final variable store.

Playbooks can use all command types including `remote`. Use `attackmate://docs/playbook/structure` and `attackmate://docs/playbook/examples` for format reference.

---

### get_variable_store

Read the current variable store of the persistent AttackMate instance.

```
get_variable_store() -> dict
```

Returns the variables saved by previous `execute_command` calls (via `saves_result_to` and `creates_session`). Use this to inspect what sessions, addresses, or results have been captured so far.

Fetch `attackmate://docs/playbook/vars` for variable syntax documentation.

---

### list_command_types

Return the full JSON schema for all available AttackMate command types.

```
list_command_types() -> dict
```

The schema is a discriminated union on the `type` field. For most command types the schema maps directly to a single model. For `sliver` and `sliver-session` it contains a nested discriminated union on the `cmd` field - check the `discriminator.mapping` for the available `cmd` values and the `oneOf` entries for their field schemas.

Individual per-type schemas are also available at `attackmate://schema/{type}`.

---

## Command types

| Type | Description |
|---|---|
| `shell` | Local shell command |
| `ssh` | SSH command on a remote host |
| `sftp` | SFTP file transfer |
| `msf-module` | Metasploit module (exploit, auxiliary, post) |
| `msf-session` | Interact with an existing Metasploit session |
| `msf-payload` | Generate a Metasploit payload |
| `sliver` | Sliver C2 server operations (discriminated by `cmd`) |
| `sliver-session` | Sliver implant session operations (discriminated by `cmd`) |
| `browser` | Browser automation |
| `vnc` | VNC interaction |
| `http-client` | HTTP client request |
| `webserv` | Local web server |
| `bettercap` | Bettercap network attack |
| `debug` | Debug/no-op command for testing |
| `setvar` | Set a variable in the store |
| `regex` | Regex match/extract against a variable |
| `sleep` | Sleep for a duration |
| `include` | Include another playbook file |
| `loop` | Loop over a command block |
| `mktemp` | Create a temporary file or directory |
| `father` | Parent process manipulation |
| `json` | JSON parse/extract |
| `remote` | Execute a command or playbook on a remote AttackMate instance (playbook only) |

---

## Resources

Resources are available when `ATTACKMATE_DOCS_PATH` is set in `.env`.

### attackmate://docs/commands/{type}

RST documentation for a specific executor type - fields, types, defaults, and examples sourced directly from the AttackMate documentation tree.

Supported values for `{type}`: all types listed in the table above.

### attackmate://docs/playbook/{topic}

RST documentation for playbook topics.

| Topic | Content |
|---|---|
| `structure` | Overall playbook YAML format |
| `vars` | Variable syntax and substitution |
| `examples` | Ready-made example playbooks |

### attackmate://schema/{type}

JSON schema for a single command type, extracted from the full union schema. Useful for inspecting the exact fields and constraints for one type without reading the entire union.
