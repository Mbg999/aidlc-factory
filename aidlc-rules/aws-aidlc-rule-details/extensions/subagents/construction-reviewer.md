# Construction Reviewer Subagent

Purpose
- Automated review during construction: style checks, TODOs inventory, secret scanning, and optional lightweight linters (flake8, eslint).
- Output: `aidlc-docs/construction-review.md` with findings and recommended fixes.

Role: `reviewer`

Enforcement
- Advisory by default; can be configured as blocking depending on workflow settings.

Permissions
- Read: `workspace/**`
- Write: `aidlc-docs/**`

Notes for implementers
- Keep all analysis non-destructive. Run potentially expensive checks in the sandbox and summarize results.
- Integrate secret-detection heuristics and provide clear remediation steps.

Entrypoint: `scripts/subagents/construction_reviewer.py`

Execution
- The AI coding assistant MUST run this agent via terminal command — NOT simulate its behavior.
- Command:
  ```bash
  python scripts/subagents/manager.py construction-reviewer '{"run_folder": "."}'
  ```
- After execution, read `aidlc-docs/construction-review.md` and present findings to the user.
- If the script is not present in the workspace, fall back to performing the review manually and inform the user.
