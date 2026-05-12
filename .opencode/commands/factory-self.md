---
description: Run the AIDLC orchestrator on its own codebase. Self-hosting mode.
argument-hint: <feature description>
---

You are now the AIDLC orchestrator in SELF-HOSTING mode.

**User request:** $ARGUMENTS

This run targets the orchestrator's own codebase. Treat `scripts/`, `.claude/agents/`,
and `tests/` as the workspace being developed.

## Rules

1. Workspace scope: `scripts/`, `.claude/agents/`, `.aidlc-orchestrator/contracts/`, `tests/`
2. Design units map to individual scripts or agent files
3. Validation: `python3 -m pytest tests/ --tb=short`
4. Review focuses on test coverage and backward compatibility
5. No `/factory-ship` stage — self-hosting skips ship-agent

Proceed with standard `/factory-spec` flow.
