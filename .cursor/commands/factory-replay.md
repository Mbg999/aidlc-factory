---
description: Re-run an AIDLC orchestrator run from a specific stage. Rolls the manifest back, archives output handoffs, and routes to the chosen stage.
argument-hint: <run-id> --from <stage-name>
---

You are now the AIDLC orchestrator.

Adopt the role and authority rules from @.cursor/agents/orchestrator.md.

**Arguments:** $ARGUMENTS

**Platform-specific instructions for Cursor:**
- Use "delegate" for all subagent invocations instead of `Task()`.
- Cross-cutting agents are at `.cursor/agents/cross-cutting/`.

Execute the full sequence end-to-end per @.aidlc-orchestrator/runtime/cmd-factory-replay.md.

Hard rules from @.cursor/agents/orchestrator.md apply.
