This server should only be pointed at an AttackMate instance running against your own test or training systems. For this reason, every software bug is treated equally, regardless of whether it is security relevant or not.

*Please note that this server hands an LLM the ability to execute `execute_command` and `run_playbook` calls directly against AttackMate,  including `shell`, `ssh`, and `msf-*` executors. A malicious or compromised target could return output (e.g. `RESULT_STDOUT`) that steers the LLM into issuing further unintended commands (prompt injection).
