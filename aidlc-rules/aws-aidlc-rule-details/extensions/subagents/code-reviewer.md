# Code Reviewer Subagent

This file documents the Code Reviewer subagent. It is always enabled and loaded automatically at workflow start.

Purpose
- Provide fast, deterministic lint and lightweight security checks on generated code artifacts.
- Produce annotations and a short summary report inserted into `aidlc-docs/reporting/` and `aidlc-docs/audit.md`.

Role: `reviewer`

Enforcement
- This subagent is intended as an advisory enforcement: non-compliant findings are reported as blocking items in the stage completion summary when configured to be blocking. See `agents.yaml` for enforcement-level metadata.

Permissions
- Read: `workspace/**`
- Write: `aidlc-docs/**`

Notes for implementers
- Keep runtime logic sandboxed. Use the evaluation sandbox container for executing third-party checks.
- Keep checks fast and idempotent; this agent should not modify source files directly without explicit approval.

Entrypoint: `scripts/subagents/code_reviewer.py`

Execution
- The AI coding assistant MUST run this agent via terminal command — NOT simulate its behavior.
- Command:
  ```bash
  python scripts/subagents/manager.py code-reviewer '{"run_folder": "."}'
  ```
- After execution, read findings from `aidlc-docs/reporting/` and present them to the user.
- Blocking findings must be resolved before the stage can complete.
- If the script is not present in the workspace, fall back to performing review manually and inform the user.
