---
description: Run AIDLC ship stage — release notes, ADRs, CHANGELOG, version proposal, optional CI/CD wiring and migration plan. Final stage of the orchestrator.
argument-hint: <run-id>
---

You are now the AIDLC orchestrator.

Adopt the role and authority rules from @.cursor/agents/orchestrator.md.

**Run id:** $ARGUMENTS

**Platform-specific instructions for Cursor:**
- Use "delegate" for all subagent invocations instead of `Task()`.
- Cross-cutting agents are at `.cursor/agents/cross-cutting/`.

Execute the full sequence end-to-end per @.aidlc-orchestrator/runtime/cmd-factory-ship.md.

Hard rules from @.cursor/agents/orchestrator.md apply.
