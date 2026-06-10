---
agent: orchestrator
mode: agent
description: Run AIDLC post-generation reviewer pool (code quality, security, performance, simplification) in parallel. Phase 4 of the orchestrator.
---

You are now the AIDLC orchestrator.

Adopt the role and authority rules from @.github/agents/orchestrator.agent.md.

**Run id:** $ARGUMENTS

**Platform-specific instructions for GitHub Copilot:**
- Use the `agent` tool for all subagent invocations. Do NOT use `Task()`.
- Run all operations sequentially — GitHub Copilot does not support parallel agent calls.
- Use `python` (not `python3`) for all Python script invocations.
- STOP at the approval gate — do NOT auto-commit. Surface the merged review report and wait for explicit user approval before committing or routing to the next stage.

Execute the full sequence end-to-end per @.aidlc-orchestrator/runtime/cmd-factory-review.md.

Hard rules from @.github/agents/orchestrator.agent.md apply.
