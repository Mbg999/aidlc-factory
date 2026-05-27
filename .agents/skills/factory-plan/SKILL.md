---
name: factory-plan
description: Run AIDLC workflow planning (optional stories + execution plan + optional unit decomposition) for an existing run. Phase 1 of the orchestrator.
---

# factory-plan — AIDLC Workflow Planning

Adopt the role from `.aidlc-orchestrator/agents/orchestrator.md` and execute the
`/factory-plan <run-id>` sequence.

**Run id:** the run-id provided by the user.

Sequence:
1. Read `manifest.yaml` for the run. Refuse if missing or if the run is not
   past `requirements-analyst`.
2. **Conditional Story Writer** — fire only if scope is multi-component
   AND the feature is user-facing. Two-pass with question gate when used.
3. **Workflow Planner** (always, `model: opus`):
   - Validate input -> spawn -> validate output
   - Output's `status: needs_human` is expected — surface the execution plan
     to user, wait for approval, log answer to audit, re-spawn or proceed
     based on user feedback
3.5. **Pre-mortem visibility check** — inspect `workflow-planner.output.yaml`
   for `skill_compliance[]` row for `requirements-intelligence`. Log violations.
4. **Conditional Unit Decomposer** — fire if `units.length >= 2` from the
   approved planner output OR if requirements call out distinct components.
5. Append all `audit_entries[]`, update state file. Present the final plan +
   decomposition output to the user and wait for explicit approval before committing.
   On approval, commit `docs(workflow-planning): complete workflow planning`.

   **User-facing summary MUST include a `Pre-mortem:` line.**

6. **Offer next step:** `/factory-build <RUN_ID_LITERAL>`

Hard rules from `.aidlc-orchestrator/agents/orchestrator.md` apply.
