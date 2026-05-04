# Cline Adapter for AI-DLC

This adapter explains how to use AI-DLC rules with **Cline** (VS Code extension).

## Setup

Cline reads project-level rules from `.clinerules` (file) or `.clinerules/` (directory).

Create `.clinerules/aidlc.md`:

```markdown
## AI-DLC Workflow

Follow the AI-DLC workflow defined in aidlc-rules/aws-aidlc-rules/core-workflow.md.
Load rule detail files from aidlc-rules/aws-aidlc-rule-details/ as specified.
```

## Subagents & Skills

Cline can execute terminal commands. Use the manager/pipeline directly:

```bash
python scripts/subagents/manager.py code-reviewer '{"run_folder":"runs/current"}'
python scripts/subagents/pipeline.py review-only '{"run_folder":"runs/current"}'
```

Skills installed under `~/.agents/skills/` are injected automatically.

## Verification

Ask Cline: "What phase are we in according to AI-DLC?" — it should respond
with the current phase from `aidlc-docs/aidlc-state.md`.
