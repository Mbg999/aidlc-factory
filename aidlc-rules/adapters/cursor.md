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

## Skills

Install skills for full workflow enforcement:

```bash
python scripts/install_aidlc.py --tool cursor --with-agent-skills --dest .
```

Skills installed under `.agents/skills/` are referenced by stage rule files.
Without them, inline fallback processes are used.

## Verification

Ask Cursor: "What phase are we in according to AI-DLC?" — it should respond
with the current phase based on `aidlc-state.md`.
