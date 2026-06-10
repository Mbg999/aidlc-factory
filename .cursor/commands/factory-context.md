---
description: Build and display a contextual snapshot from AIDLC traceability files (audit.md, aidlc-state.md, manifest, timeline). Use this to quickly understand project state before continuing work.
argument-hint: <run-id> [--depth minimal|standard|comprehensive|auto]
---

You are now the AIDLC orchestrator.

Adopt the role and authority rules from @.cursor/agents/orchestrator.md.

**Argument:** $ARGUMENTS

**Platform-specific instructions for Cursor:**
- Use "delegate" for all subagent invocations instead of `Task()`.
- Cross-cutting agents are at `.cursor/agents/cross-cutting/`.

Execute the full sequence end-to-end per @.aidlc-orchestrator/runtime/cmd-factory-context.md.

Hard rules from @.cursor/agents/orchestrator.md apply.
