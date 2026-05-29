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
    AND the feature is user-facing. Otherwise log skip to audit via:
    ```bash
    python3 aidlc-scripts/factory_run.py emit_audit_block <run-id> \
        --evt stage_skipped --stage story-writer --phase INCEPTION \
        --label "Story Writer SKIPPED (not user-facing or single-component)" \
        --field reason="Scope is single-component or non-user-facing" \
        --bullet "[Orchestrator] Proceeding to workflow-planner"
    ```
    Two-pass with question gate when used.
3. **Workflow Planner** (always, `model: opus`):
   - Validate input -> spawn -> validate output
    - Output's `status: needs_human` is expected — surface the execution plan
      to user, wait for approval, log answer to audit via:
      ```bash
      python3 aidlc-scripts/factory_run.py emit_audit_block <run-id> \
          --evt user_decision --stage workflow-planner --phase INCEPTION \
          --label "User Decision (workflow-planner)" \
          --field decision=<approve|reject|amend> \
          --bullet "[User] <decision summary>"
      ```
      then re-spawn or proceed based on user feedback
3.5. **Pre-mortem visibility check (defensive guard).** Before proceeding,
   inspect `workflow-planner.output.yaml`:
   - Locate the `skill_compliance[]` row for `requirements-intelligence`.
     If MISSING -> append `[PlanPreMortem] missing — workflow-planner contract
     violation: no requirements-intelligence row in skill_compliance` to your
     own `audit_entries[]` and continue (do NOT halt — the plan content is
     still valid).
   - Locate any `audit_entries[]` bullet starting with `[PlanPreMortem]`.
     If the `skill_compliance[]` row is present but no `[PlanPreMortem]`
     bullet exists -> append `[PlanPreMortem] orphan compliance row —
     workflow-planner emitted skill_compliance without matching audit_entry`
     to your own audit_entries and continue.
4. **Conditional Unit Decomposer** — fire if `units.length >= 2` from the
   approved planner output OR if requirements call out distinct components.
5. Append all `audit_entries[]`, update state file. Present the final plan +
    decomposition output to the user and wait for explicit approval before committing.
    On user decision, log to audit:
    ```bash
    python3 aidlc-scripts/factory_run.py emit_audit_block <run-id> \
        --evt user_decision --stage workflow-planner --phase INCEPTION \
        --label "User Decision (planning-complete)" \
        --field decision=<approve|reject> \
        --bullet "[User] <summary>"
    ```
    On approval, commit `docs(workflow-planning): complete workflow planning`.

   **User-facing summary MUST include a `Pre-mortem:` line populated from
   `workflow-planner.output.skill_compliance[].requirements-intelligence`:**
   - `Pre-mortem: PASS — <N> plan-risk question(s)` (when status=PASS)
   - `Pre-mortem: N/A — <evidence>` (when status=N/A, e.g. trivial plan)
   - `Pre-mortem: MISSING — workflow-planner contract violation` (when row absent)

   Never omit this line. The user must see it.

6. **Offer next step:** Run `python3 aidlc-scripts/factory_run.py status <run-id> --next-cmd`
   to get the ready-to-paste command, OR format manually as
   `/factory-build <RUN_ID_LITERAL>` with the actual run_id.
   **Never present `<run-id>` literally to the user.**

Hard rules from `.aidlc-orchestrator/agents/orchestrator.md` apply.
