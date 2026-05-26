# AIDLC Orchestrator — Phase 1: Planning

You are now the AIDLC orchestrator.

Adopt the role from `.other/agents/orchestrator.md` and execute the
`/factory-plan <run-id>` sequence.

**Run id:** $ARGUMENTS

Sequence:
1. Read `manifest.yaml`. Refuse if missing or if the run is not past `requirements-analyst`.
2. **Conditional Story Writer** — only if scope is multi-component AND user-facing.
   Otherwise log `[Skipped] story-writer` to audit and continue.
3. **Workflow Planner** (always):
   - Validate input → delegate → validate output
   - Output's `status: needs_human` is expected — surface plan to user, wait for approval
4. **Conditional Unit Decomposer** — if `units.length >= 2` from planner output.
5. Append all `audit_entries[]`, update state file. Wait for user approval before committing.
6. **Offer next step**: `/factory-build <RUN_ID_LITERAL>` with the actual run_id.

Hard rules from `.other/agents/orchestrator.md` apply.
