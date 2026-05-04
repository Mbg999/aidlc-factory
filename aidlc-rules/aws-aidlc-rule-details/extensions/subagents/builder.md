# Construction Builder Subagent

Purpose
- Suggest build commands and (optionally) run non-destructive build checks (lint, quick compile, smoke tests).
- Output: `aidlc-docs/build-report.md` with suggested commands, diagnostics and recommended next steps.

Role: `builder`

Enforcement
- Advisory. Should not run destructive commands by default; any destructive step must be explicitly allowed.

Permissions
- Read: `workspace/**`
- Write: `aidlc-docs/**`

Notes for implementers
- Prefer suggestion-only mode. If running checks, run them in the sandbox environment and record logs in `aidlc-docs`.

Entrypoint: `scripts/subagents/builder.py`

Execution
- The AI coding assistant MUST run this agent via terminal command — NOT simulate its behavior.
- Command:
  ```bash
  python scripts/subagents/manager.py builder '{"run_folder": "."}'
  ```
- After execution, read `aidlc-docs/build-report.md` and present suggested commands and diagnostics to the user.
- If the script is not present in the workspace, fall back to generating the report manually and inform the user.
