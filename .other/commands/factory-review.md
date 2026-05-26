# AIDLC Orchestrator — Phase 4: Review

You are now the AIDLC orchestrator.

Adopt the role from `.other/agents/orchestrator.md` and execute the
`/factory-review <run-id>` sequence (parallel fan-out per Phase 4).

**Run id:** $ARGUMENTS

Sequence:
1. Read `manifest.yaml`. Refuse if construction isn't complete.
2. **Collect framework skills from build**: read `manifest.skill_paths` + all
   `code-generator.*.output.yaml` handoffs.
3. **Build validation**: detect build system, run compile/check command.
4. Build per-reviewer input handoffs under `.aidlc-orchestrator/runs/<run-id>/handoffs/`.
5. **Parallel delegation** — delegate to all N reviewers (≤ 4) concurrently:
   - `reviewer-code`
   - `reviewer-security`
   - `reviewer-performance`
   - `reviewer-simplifier`
   If your tool doesn't support parallel delegation, run sequentially.
6. **Sequential post-processing** per reviewer: validate output → audit append.
7. **Merge**:
   ```bash
   python3 aidlc-scripts/factory_merge_reviews.py <run-id>
   ```
8. Surface report to user. Approval gate → either fixes or approved.
9. **Offer next step**: `/factory-ship <RUN_ID_LITERAL>` with the actual run_id.

Hard rules from `.other/agents/orchestrator.md` apply.
