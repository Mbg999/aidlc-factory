# Cursor Adapter for AI-DLC

This adapter explains how to use AI-DLC rules with **Cursor**.

## Setup

Cursor reads project rules from `.cursor/rules/*.mdc` files.

Create `.cursor/rules/aidlc.mdc`:

```markdown
---
description: AI-DLC workflow rules
globs: ["**/*"]
alwaysApply: true
---

Follow the AI-DLC workflow defined in aidlc-rules/aws-aidlc-rules/core-workflow.md.
Load rule detail files from aidlc-rules/aws-aidlc-rule-details/ as specified.
```

## Subagents & Skills

Cursor does not natively run Python subagents, but you can invoke the pipeline
executor manually from the terminal:

```bash
python scripts/subagents/pipeline.py construction-full '{"run_folder":"runs/my-run"}'
```

Skills installed under `~/.agents/skills/` are injected into agent context
automatically when agents are run via `manager.py`.

## Agency-Agents Integration

When installed with `--with-agency-agents`, specialist persona files from
[The Agency](https://github.com/msitarzewski/agency-agents) are placed in
`.cursor/rules/` as `.mdc` files. Cursor loads these as rule files that the
AI assistant consults during AIDLC phases.

- Files follow the naming pattern: `<division>-<slug>.mdc`
  (e.g., `engineering-backend-architect.mdc`)
- AIDLC automatically consults relevant personas when the agency-agents
  extension is enabled (see `extensions/agency-agents/agency-agents.md`).
- To install:
  ```bash
  python scripts/install_aidlc.py --tool cursor --with-agency-agents --dest .
  ```

## Verification

Ask Cursor: "What phase are we in according to AI-DLC?" — it should respond
with the current phase based on `aidlc-state.md`.
