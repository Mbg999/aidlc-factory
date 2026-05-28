---
description: 'Python conventions for AIDLC runtime scripts'
applyTo: 'aidlc-scripts/**,tests/**,src/**'
---

# AIDLC Python scripts

- Prefer `pathlib.Path` over string paths; use `AIDLC_ROOT` when resolving repo root.
- Never use `subprocess(..., shell=True)` without sanitization; no `eval()`.
- Factory scripts exit non-zero on validation failure — propagate errors, do not swallow.
- Handoff validation: `python aidlc-scripts/factory_validate.py <schema> <handoff> [--strict]`.
- Run state lives in `.aidlc-orchestrator/runs/` (gitignored) — never commit manifests or handoffs from runs.
