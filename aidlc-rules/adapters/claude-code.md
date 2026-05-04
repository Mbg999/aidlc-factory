# Claude Code Adapter for AI-DLC

This adapter explains how to use AI-DLC rules with **Claude Code** (`claude` CLI).

## Setup

Claude Code reads project instructions from `CLAUDE.md` at the repo root,
and from `.claude/CLAUDE.md` (project-scoped).

Create `.claude/CLAUDE.md` (or append to existing `CLAUDE.md`):

```markdown
## AI-DLC Workflow

Follow the AI-DLC workflow defined in aidlc-rules/aws-aidlc-rules/core-workflow.md.
Load rule detail files from aidlc-rules/aws-aidlc-rule-details/ as specified in
the core-workflow rule-details loading section.
```

## Subagents & Skills

Claude Code can invoke subagents via bash tool calls. Example:

```bash
python scripts/subagents/manager.py planner '{"run_folder":"runs/current"}'
python scripts/subagents/pipeline.py construction-full '{"run_folder":"runs/current"}'
```

Skills installed under `~/.agents/skills/` are automatically injected into
agent context by `manager.py`.

## Verification

Ask Claude: "What phase are we in according to AI-DLC?" — it should respond
with the current phase from `aidlc-docs/aidlc-state.md`.
