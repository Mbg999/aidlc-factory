# Construction Planner Subagent

Purpose
- Generate a concrete construction/build plan for the workspace (install, test, lint, build steps).
- Output: `aidlc-docs/construction-plan.md` with actionable steps and suggested commands.

Role: `planner`

Enforcement
- Advisory by default; findings are reported in `aidlc-docs` and the run audit. Can be configured as blocking in workflow config.

Permissions
- Read: `workspace/**`
- Write: `aidlc-docs/**`

Notes for implementers
- Keep runtime logic sandboxed; do not modify source files without explicit approval.
- Keep checks idempotent and fast. Prefer writing reports in `aidlc-docs/` rather than editing code.

Entrypoint: `scripts/subagents/planner.py`

Execution
- The AI coding assistant MUST run this agent via terminal command — NOT simulate its behavior.
- Command:
  ```bash
  python scripts/subagents/manager.py planner '{"run_folder": "."}'
  ```
- After execution, read `aidlc-docs/construction-plan.md` and present key findings to the user.
- If the script is not present in the workspace, fall back to generating the plan manually and inform the user.
