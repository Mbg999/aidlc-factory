# `/factory-resume` — Resume Interrupted Run

PRIORITY: P3

Picks up an interrupted run from its last checkpoint.

1. Read run state:
   ```bash
   python3 aidlc-scripts/factory_run.py resume <run-id>
   ```
   This emits a JSON report with `completed_stages`, `current_stage`,
   `next_stage_suggestion`, `partial_outputs[]`, `reconcile`, and
   `version_warning` (if scripts version differs from manifest version).
   It also appends a `resume_requested` event to `timeline.jsonl`.

2. If `partial_outputs[]` is non-empty, surface to the user with two
   options:
   - **Trust and complete** — accept partial outputs as-is; proceeds to
     `next_stage_suggestion`.
   - **Re-spawn fresh** — discard partial outputs for the interrupted stage
     (re-queues it; re-spawns from scratch).
3. If `partial_outputs[]` is empty, proceed directly to
   `next_stage_suggestion`.
4. Log `[RunManager] Resumed run <run-id> from stage <s>` to audit.

Hard rules from the orchestrator apply.
