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

## Verification

Ask Cursor: "What phase are we in according to AI-DLC?" — it should respond
with the current phase based on `aidlc-state.md`.
