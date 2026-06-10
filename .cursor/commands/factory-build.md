---
description: Run AIDLC construction (per-unit code generation + build/test) for an existing run. Layer-parallel per Phase 5 — independent units run in parallel; layers sequential.
argument-hint: <run-id>
---

You are now the AIDLC orchestrator.

Adopt the role and authority rules from @.cursor/agents/orchestrator.md.

**Run id:** $ARGUMENTS

**Platform-specific instructions for Cursor:**
- Use "delegate" for all subagent invocations instead of `Task()`.
- Cross-cutting agents are at `.cursor/agents/cross-cutting/`.

Execute the full sequence end-to-end per @.aidlc-orchestrator/runtime/cmd-factory-build.md.

Hard rules from @.cursor/agents/orchestrator.md apply.
