---
name: factory-review
description: Run AIDLC post-generation reviewer pool (code quality, security, performance, simplification) in parallel. Phase 4 of the orchestrator.
---

# factory-review — AIDLC Review

Adopt the role from `.aidlc-orchestrator/agents/orchestrator.md` and execute the
`/factory-review <run-id>` sequence (parallel fan-out per Phase 4).

**Run id:** the run-id provided by the user.

Sequence:
1. Read `manifest.yaml`. Refuse if construction isn't complete.
1.5. **Collect framework skills from build**: read `manifest.skill_paths` + all
    `code-generator.*.output.yaml` handoffs; extract skills not in the base set.
1.75. **Build validation**: detect build system, run compile/check command,
    surface approval gate on failure. Skip if no build system detected.
2. **Sequential knowledge queries** per active reviewer; build per-reviewer
   input handoff under `.aidlc-orchestrator/runs/<run-id>/handoffs/reviewer-<x>.input.yaml`
   with reviewer-specific tags and top-5 priors in `context_pointers[]`.
   Validate each input against `reviewer.input.v1.json`.
4. **Parallel spawn** — emit ONE message containing all N (<=4) reviewer spawns.
5. **Sequential post-processing** per reviewer: validate output -> knowledge save -> audit append.
6. **Merge**:
   ```bash
   python3 aidlc-scripts/factory_merge_reviews.py <run-id>
   ```
   Produces `aidlc-docs/operations/<run-id>-review-report.md`.
7. Surface report to user. Approval gate:
   - **Fixes requested** -> route back through `/factory-build <run-id>`
   - **Approved** -> update `aidlc-docs/aidlc-state.md` Current Stage and Stage Progress,
     auto-commit `docs(review): complete review report`,
     then run `python3 aidlc-scripts/factory_run.py status <run-id> --next-cmd`
     to get the ready-to-paste command, or format as `/factory-ship <RUN_ID_LITERAL>`

**Phase 4 acceptance**: review wall-clock should be ~`max(reviewer wall-clocks)`.

Hard rules from `.aidlc-orchestrator/agents/orchestrator.md` apply.
