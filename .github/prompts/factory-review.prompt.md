---
agent: orchestrator
description: Run AIDLC post-generation reviewer pool (code quality, security, performance, simplification) in parallel. Phase 4 of the orchestrator.
---

You are now the AIDLC orchestrator.

Adopt the role from @.github/agents/orchestrator.md and execute the
`/factory-review <run-id>` sequence (now **parallel fan-out** per Phase 4).

**STOP at the approval gate — do NOT auto-commit.** Surface the merged review report and wait for explicit user approval before committing or routing to the next stage.

**Run id:** _(from the user's message)_

Sequence:
1. Read `manifest.yaml`. Refuse if construction isn't complete.
1.5. **Collect framework skills from build** (Pre-Review Step 0.5 per
   `runtime/cmd-factory-review.md`): read `manifest.skill_paths` + all
   `code-generator.*.output.yaml` handoffs; extract skills not in the base set.
   Store as `framework_skill_paths`. Log the list even if empty.
1.75. **Build validation** (Pre-Review Step 0.75 per
   `runtime/cmd-factory-review.md`): detect build system, run compile/check
   command, surface approval gate on failure. Skip if no build system detected.
2. **Sequential knowledge queries** per active reviewer; build per-reviewer
   input handoff under `.aidlc-orchestrator/runs/<run-id>/handoffs/reviewer-<x>.input.yaml`
   with reviewer-specific tags and top-5 priors injected into `context_pointers[]`.
   For `reviewer-code`: merge `framework_skill_paths` into the handoff's
   `skills_required[]` and `skill_paths_resolved[]` before writing.
   Validate each input against `reviewer.input.v1.json`.
4. **Sequential spawn** — invoke each reviewer subagent via the `agent` tool **one at a time**
   (Copilot does not support parallel agent invocations; run reviewers sequentially,
   collecting all outputs before merging).
5. **Sequential post-processing** per reviewer: validate output →
   knowledge save → audit append.
6. **Merge**:
   ```bash
   python aidlc-scripts/factory_merge_reviews.py <run-id> [--reviewers <active-set>]
   ```
   Produces `aidlc-docs/operations/<run-id>-review-report.md`.
7. Surface report to user. Approval gate:
   - **Fixes requested** → route units back through `/factory-build <run-id>`
   - **Approved** → ask user for commit approval, then commit
     `docs(review): complete review report`, update state, then
     **offer next step (substitute `<run-id>` literally):** run
     `python aidlc-scripts/factory_run.py status <run-id> --next-cmd`
     to get the ready-to-paste command, OR format manually as
     `/factory-ship <RUN_ID_LITERAL>` with the actual run_id.
     **Never present `<run-id>` literally to the user.**

Hard rules from @.github/agents/orchestrator.md apply.

**Phase 4 acceptance**: review wall-clock should be ~`max(reviewer wall-clocks)`,
not sum. Track via `manifest.events[]` timestamps and reviewer `cost.wall_clock_min`.
