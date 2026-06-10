---
description: Run AIDLC workflow planning (optional stories + execution plan + optional unit decomposition) for an existing run. Phase 1 of the orchestrator.
argument-hint: <run-id>
---

You are now the AIDLC orchestrator.

Adopt the role and authority rules from @.cursor/agents/orchestrator.md.

**Run id:** $ARGUMENTS

**Platform-specific instructions for Cursor:**
- Use "delegate" for all subagent invocations instead of `Task()`.
- Cross-cutting agents are at `.cursor/agents/cross-cutting/`.

Execute the full sequence end-to-end per @.aidlc-orchestrator/runtime/cmd-factory-plan.md.

Hard rules from @.cursor/agents/orchestrator.md apply.
