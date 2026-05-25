---
description: Run AIDLC workflow planning (optional stories + execution plan + optional unit decomposition) for an existing run. Phase 1 of the orchestrator.
argument-hint: <run-id>
---

You are now the AIDLC orchestrator.

Adopt the role from @.claude/agents/orchestrator.md and execute the
`/factory-plan <run-id>` sequence (see "Phase 1 sequences" in the orchestrator
spec).

**Run id:** $ARGUMENTS

Sequence:
1. Read `manifest.yaml` for the run. Refuse if missing or if the run is not
   past `requirements-analyst`.
2. **Conditional Story Writer** — fire only if scope is multi-component
   AND the feature is user-facing (per requirements-analyst output's
   `request_classification`). Otherwise log `[Skipped] story-writer ...` to
   audit and continue. Two-pass with question gate when used.
3. **Workflow Planner** (always, `model: opus`):
   - Validate input → spawn → validate output
    - Output's `status: needs_human` is expected — surface `<run-id>-execution-plan.md`
     to user, wait for approval, log answer to audit, re-spawn or proceed
     based on user feedback
3.5. **Pre-mortem visibility check (defensive guard).** Before proceeding,
   inspect `workflow-planner.output.yaml`:
   - Locate the `skill_compliance[]` row for `requirements-intelligence`.
     If MISSING → append `[PlanPreMortem] missing — workflow-planner contract violation: no requirements-intelligence row in skill_compliance` to your own `audit_entries[]` and continue (do NOT halt — the plan content is still valid).
   - Locate any `audit_entries[]` bullet starting with `[PlanPreMortem]`.
     If the `skill_compliance[]` row is present but no `[PlanPreMortem]` bullet exists → append `[PlanPreMortem] orphan compliance row — workflow-planner emitted skill_compliance without matching audit_entry` to your own audit_entries and continue.
   - These guards exist because the workflow-planner contract requires DUAL
     emission (compliance row + matching audit bullet); the orchestrator must
     log the violation so it's visible in `audit.md` instead of silently swallowed.
4. **Conditional Unit Decomposer** — fire if `units.length >= 2` from the
   approved planner output OR if requirements call out distinct components.
5. Append all `audit_entries[]`, update state file. Present the final plan +
   decomposition output to the user and wait for explicit approval before committing.
   On approval, commit `docs(workflow-planning): complete workflow planning`.

   **User-facing summary MUST include a `Pre-mortem:` line populated from
   `workflow-planner.output.skill_compliance[].requirements-intelligence`:**
   - `Pre-mortem: PASS — <N> plan-risk question(s)`  (when status=PASS)
   - `Pre-mortem: N/A — <evidence>`                  (when status=N/A, e.g. trivial plan)
   - `Pre-mortem: MISSING — workflow-planner contract violation` (when row absent)

   Never omit this line. The user must see it.
6. **Offer next step (substitute `<run-id>` literally):** Run
   `python3 aidlc-scripts/factory_run.py status <run-id> --next-cmd` to get
   the ready-to-paste command, OR format manually as `/factory-build <RUN_ID_LITERAL>`
   — replace `<RUN_ID_LITERAL>` with the actual run_id (e.g.
   `2026-05-22T10-00-00Z-jwt-auth`). **Never present `<run-id>` literally to the user.**

Hard rules from @.claude/agents/orchestrator.md apply.
