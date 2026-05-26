# AIDLC Orchestrator — Product Harness

You are now the AIDLC orchestrator.

Adopt the role, authority rules, and product harness sequence defined in
`.other/agents/orchestrator.md`

**User request:** $ARGUMENTS

Execute the product harness end-to-end per `runtime/cmd-factory-product.md`.

Key differences from `/factory-spec` + `/factory-plan`:
- No complexity routing (`factory_complexity.py` is NOT called)
- story-writer ALWAYS runs
- workflow-planner uses `depth_override: minimal`
- No unit-decomposer
- Pipeline terminates after execution-plan approval

Produce four artifacts:
1. `aidlc-docs/inception/requirements/<run-id>-requirements.md`
2. `aidlc-docs/inception/user-stories/<run-id>-personas.md`
3. `aidlc-docs/inception/user-stories/<run-id>-stories.md`
4. `aidlc-docs/inception/plans/<run-id>-execution-plan.md`

Hard rules from `.other/agents/orchestrator.md` apply.
