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

## Verification

Ask Copilot: "What phase are we in according to AI-DLC?" — it should respond
with the current INCEPTION/CONSTRUCTION/OPERATIONS phase based on `aidlc-state.md`.
