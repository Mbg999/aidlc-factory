# GitHub Copilot Adapter for AI-DLC

This adapter explains how to use AI-DLC rules with **GitHub Copilot** (VS Code extension).

## Setup

Copilot reads agent instructions from `.github/copilot-instructions.md` (workspace-level)
and from `*.instructions.md` files in `.github/instructions/`.

**Option A — single instructions file (recommended for small teams):**

Create `.github/copilot-instructions.md` with this content:

```markdown
@AIDLC_RULES_PATH/aws-aidlc-rules/core-workflow.md
```

Replace `AIDLC_RULES_PATH` with the relative path to your `aidlc-rules/` directory
(e.g., `aidlc-rules` if committed at repo root).

**Option B — scoped instructions per language/path:**

Create `.github/instructions/aidlc-core.instructions.md`:

```markdown
---
applyTo: "**"
---
Follow the AI-DLC workflow defined in aidlc-rules/aws-aidlc-rules/core-workflow.md.
Load rule detail files from aidlc-rules/aws-aidlc-rule-details/ as specified.
```

## Subagents & Skills

- Subagents (`scripts/subagents/`) are invoked by Copilot via the MCP bridge
  when agents return `mcp_calls` in their output.
- Installed skills (under `~/.agents/skills/`) are automatically injected into
  agent context by `manager.py` based on each agent's `skills` list in `agents.yaml`.
- MCP tools available in your VS Code installation are surfaced via
  `mcp_bridge.py list_tools`.

## Agency-Agents Integration

When installed with `--with-agency-agents`, specialist persona files from
[The Agency](https://github.com/msitarzewski/agency-agents) are placed in
`.github/agents/`. These are **VS Code Copilot agent-mode personas** that the
AI assistant reads as additional context during AIDLC phases.

- Files follow the naming pattern: `<division>-<slug>.md`
  (e.g., `engineering-backend-architect.md`)
- Copilot can activate them via `@AgentName` or AIDLC consults them automatically
  when the agency-agents extension is enabled.
- To install:
  ```bash
  python scripts/install_aidlc.py --tool copilot --with-agency-agents --dest .
  ```
- To install only specific divisions:
  ```bash
  python scripts/install_aidlc.py --tool copilot --with-agency-agents --agency-divisions engineering,testing --dest .
  ```

See `extensions/agency-agents/agency-agents.md` for the full phase-to-agent mapping.

## Verification

Ask Copilot: "What phase are we in according to AI-DLC?" — it should respond
with the current INCEPTION/CONSTRUCTION/OPERATIONS phase based on `aidlc-state.md`.
