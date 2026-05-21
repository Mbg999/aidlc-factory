---
description: Run AIDLC product harness — workspace scout + requirements + personas + stories + execution plan. Stops before code generation.
argument-hint: <feature description in natural language>
---

You are now the AIDLC orchestrator.

Adopt the role, authority rules, and product harness sequence defined in
@.cursor/agents/orchestrator.md

**User request:** $ARGUMENTS

Execute the product harness end-to-end per
@.aidlc-orchestrator/runtime/cmd-factory-product.md

Key differences from `/factory-spec` + `/factory-plan`:
- No complexity routing (`factory_complexity.py` is NOT called)
- story-writer ALWAYS runs — not gated on scope or complexity
- workflow-planner uses `depth_override: minimal`
- No unit-decomposer
- Pipeline terminates after execution-plan approval — do NOT offer `/factory-build`

Produce four artifacts:
1. `aidlc-docs/inception/requirements/<run-id>-requirements.md`
2. `aidlc-docs/inception/user-stories/<run-id>-personas.md`
3. `aidlc-docs/inception/user-stories/<run-id>-stories.md`
4. `aidlc-docs/inception/plans/<run-id>-execution-plan.md`

Hard rules from @.cursor/agents/orchestrator.md apply.
