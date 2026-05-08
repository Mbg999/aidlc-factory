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

## Skills

- Installed skills (under `.agents/skills/`) are the primary mechanism for
  workflow enforcement. Each stage rule file references mandatory skills.
- Install skills with:
  ```bash
  python scripts/install_aidlc.py --tool copilot --with-agent-skills --dest .
  ```
- Without installed skills, inline fallback processes in stage rules are used.

## Verification

Ask Copilot: "What phase are we in according to AI-DLC?" — it should respond
with the current INCEPTION/CONSTRUCTION/OPERATIONS phase based on `aidlc-state.md`.
