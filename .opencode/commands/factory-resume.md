---
description: Resume an interrupted AIDLC orchestrator run from its last checkpoint. Use without an argument to adopt a legacy aidlc-docs/ project as a synthetic run.
argument-hint: <run-id>  (omit to adopt legacy aidlc-docs/)
---

You are now the AIDLC orchestrator.

Adopt the role from @.claude/agents/orchestrator.md.

**Argument:** $ARGUMENTS

If `$ARGUMENTS` is empty: this is a **legacy adoption** request. Run:
```bash
python3 aidlc-scripts/factory_run.py adopt-legacy
```
The script scans `aidlc-docs/aidlc-state.md` for `[x]` Stage Progress markers,
maps legacy stage names to current stage_ids (e.g. "Workspace Detection" →
`workspace-scout`), and synthesizes a manifest with run-id
`legacy-<repo-slug>-<ts>` and `adoption_status: complete (adopted)`. Adopted
stages are trusted as-is — they are NOT re-validated against the current
contracts. Surface the resulting `run_id` and adopted-stages list to the
user; offer to continue with the next pending stage.

If `$ARGUMENTS` is a run-id: this is a **resume** request.

1. Read run state:
   ```bash
   python3 aidlc-scripts/factory_run.py status <run-id>
   ```
2. Compute the next stage to spawn:
   ```bash
   python3 aidlc-scripts/factory_run.py resume <run-id>
   ```
   The output JSON includes `next_stage_suggestion` (the manifest's
   `current_stage` if not already in `completed_stages[]`, or the next
   uncompleted stage in PHASE_ORDER otherwise) and any `partial_outputs[]`
   left from a prior crash.
3. **If `partial_outputs[]` is non-empty**: warn the user that a prior
   handoff exists. Two recovery options:
   - **Trust and complete** — read the partial output, validate against
     contract, and if valid, mark the stage complete via
     `factory_run.py complete-stage`.
   - **Re-spawn fresh** — delete the partial output, then proceed with
     a clean spawn of the next stage.
4. Surface the recovery choice to the user; await confirmation.
5. Once confirmed, route to the appropriate slash command (e.g. if
   `next_stage_suggestion` is `requirements-analyst`, the user can
   invoke `/factory-spec` continuation in this same session, or you can
   spawn the agent directly per the orchestrator protocol).

Hard rules from @.claude/agents/orchestrator.md apply.
