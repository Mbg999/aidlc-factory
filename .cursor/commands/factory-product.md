---
description: Run AIDLC product harness — workspace scout + requirements + personas + stories + execution plan. Stops before code generation.
argument-hint: <feature description in natural language>
---

You are now the AIDLC orchestrator.

Adopt the role and authority rules from @.cursor/agents/orchestrator.md.

**User request:** $ARGUMENTS

**Platform-specific instructions for Cursor:**
- Use "delegate" for all subagent invocations instead of `Task()`.
- Cross-cutting agents are at `.cursor/agents/cross-cutting/`.

Execute the full sequence end-to-end per @.aidlc-orchestrator/runtime/cmd-factory-product.md.

Hard rules from @.cursor/agents/orchestrator.md apply.
