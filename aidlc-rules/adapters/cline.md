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

## Agency-Agents Integration

When installed with `--with-agency-agents`, specialist persona files from
[The Agency](https://github.com/msitarzewski/agency-agents) are placed in
`.clinerules/agents/`. Cline reads these as contextual guidance the AI assistant
consults during AIDLC phases.

- Files follow the naming pattern: `<division>-<slug>.md`
  (e.g., `engineering-backend-architect.md`)
- AIDLC automatically consults relevant personas when the agency-agents
  extension is enabled (see `extensions/agency-agents/agency-agents.md`).
- To install:
  ```bash
  python scripts/install_aidlc.py --tool cline --with-agency-agents --dest .
  ```
- To install only specific divisions:
  ```bash
  python scripts/install_aidlc.py --tool cline --with-agency-agents --agency-divisions engineering,testing --dest .
  ```

## Verification

Ask Cline: "What phase are we in according to AI-DLC?" — it should respond
with the current phase from `aidlc-docs/aidlc-state.md`.
