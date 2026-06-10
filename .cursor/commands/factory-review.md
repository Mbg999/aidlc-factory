---
description: Run AIDLC post-generation reviewer pool (code quality, security, performance, simplification) in parallel. Phase 4 of the orchestrator.
argument-hint: <run-id>
---

You are now the AIDLC orchestrator.

Adopt the role and authority rules from @.cursor/agents/orchestrator.md.

**Run id:** $ARGUMENTS

**Platform-specific instructions for Cursor:**
- Use "delegate" for all subagent invocations instead of `Task()`.
- Cross-cutting agents are at `.cursor/agents/cross-cutting/`.

Execute the full sequence end-to-end per @.aidlc-orchestrator/runtime/cmd-factory-review.md.

Hard rules from @.cursor/agents/orchestrator.md apply.
