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

## Agency-Agents Integration

When installed with `--with-agency-agents`, specialist persona files from
[The Agency](https://github.com/msitarzewski/agency-agents) are placed in
`.claude/agents/`. Claude Code reads these as agent personas that the AI
assistant consults during AIDLC phases.

- Files follow the naming pattern: `<division>-<slug>.md`
  (e.g., `engineering-backend-architect.md`)
- AIDLC automatically consults relevant personas when the agency-agents
  extension is enabled (see `extensions/agency-agents/agency-agents.md`).
- To install:
  ```bash
  python scripts/install_aidlc.py --tool claude --with-agency-agents --dest .
  ```
- To install only specific divisions:
  ```bash
  python scripts/install_aidlc.py --tool claude --with-agency-agents --agency-divisions engineering,testing --dest .
  ```

## Verification

Ask Claude: "What phase are we in according to AI-DLC?" — it should respond
with the current phase from `aidlc-docs/aidlc-state.md`.
