# AIDLC Orchestrator — Troubleshooting Guide

## Common Issues

### `factory_run.py resume` returns wrong stage

**Symptom:** Resume suggests a stage that was already completed or skips
a stage that should run next.

**Likely cause:** `current_stage` in manifest.yaml is a synthetic marker
set by `complete-stage --next-stage`. If the orchestrator set an unexpected
value, or the manifest was manually edited, `_next_stage()` may pick the wrong
index from `PHASE_ORDER`.

**Check:**
```bash
python3 scripts/factory_run.py status <run-id> --json | grep current_stage
python3 scripts/factory_run.py status <run-id> --json | grep completed_stages
```

**Fix:** Set the correct current_stage:
```bash
python3 scripts/factory_run.py set <run-id> --field current_stage=workspace-scout
```

### Budget shows negative remaining

**Symptom:** `factory_budget.py check` or `status` shows negative tokens remaining.

**Likely cause:** `deduct` was called with parameters exceeding the remaining
budget. The Cost Governor does not enforce hard caps on `deduct` (that's the
`check` gate's job). If `check` wasn't called before `deduct`, overspend is
possible.

**Check:**
```bash
python3 scripts/factory_budget.py status <run-id> | grep -A5 used
python3 scripts/factory_budget.py status <run-id> | grep tokens_max
```

**Fix:** None needed for display — negative remaining just indicates overspend.
To reset, re-initialize the budget via `factory_budget.py init <run-id>`.

### Parallel reviewers complete but merge fails

**Symptom:** `factory_merge_reviews.py` exits with error after all 4 reviewers
completed successfully.

**Likely cause:** One reviewer's output is malformed YAML, missing required
fields, or violates the reviewer.output.v1.json schema. The merge script
validates each output and skips schema-invalid ones.

**Check:**
```bash
# Validate each reviewer output individually
python3 scripts/factory_validate.py \
  .aidlc-orchestrator/contracts/reviewer.output.v1.json \
  .aidlc-orchestrator/runs/<run-id>/handoffs/reviewer-code.output.yaml
python3 scripts/factory_validate.py \
  .aidlc-orchestrator/contracts/reviewer.output.v1.json \
  .aidlc-orchestrator/runs/<run-id>/handoffs/reviewer-security.output.yaml
# ... repeat for performance, simplifier
```

**Fix:** The offending reviewer's output is logged as "WARNING: skipping" in
stderr. Correct the YAML syntax or missing fields and re-run merge.

### `/factory-build` fails on lock acquire

**Symptom:** Lock acquire returns conflict or the orchestrator reports it can't
acquire locks for a code generation unit.

**Likely cause (fresh conflict):** Two units in the same wave have overlapping
file globs. The `check-wave` command should have caught this — check if it was
run before the build wave.

**Check:**
```bash
python3 scripts/factory_conflict.py list <run-id>
python3 scripts/factory_conflict.py conflicts <run-id>
```

**Likely cause (stale lock):** A prior agent crashed without releasing its locks.
The lock file still exists but the holder is dead.

**Check:**
```bash
# List all locks
python3 scripts/factory_conflict.py list <run-id>
# Check if any are stale (based on TTL)
python3 scripts/factory_conflict.py release <run-id> --stale --older-than 120
```

**Fix:** Release stale locks or manually remove the holder's lock file:
```bash
python3 scripts/factory_conflict.py release <run-id> <holder>
# Or for all stale locks:
python3 scripts/factory_conflict.py release <run-id> --stale --older-than 120
```

### Triage returns unexpected tier

**Symptom:** A complex request scores TINY, or a simple request scores LARGE.

**Likely cause:** The keyword-based scorer in `factory_triage.py` is
conservative by design (only exact substring matches). A request that describes
complex work in simple terms may score lower than expected.

**Check:**
```bash
python3 scripts/factory_triage.py "<request>" --explain
# Shows which factors fired and at what intensity
```

**Fix:** None needed — the orchestrator treats TINY as a threshold (score == 0).
Any single keyword match pushes to SMALL+. If the score is truly wrong, add
keywords to `FACTOR_KEYWORDS` in `scripts/factory_triage.py`.

### Timeline events missing after crash

**Symptom:** After a crash, `resume` shows `reconcile.drift` with
`completed_not_in_timeline` stages.

**Likely cause:** The manifest was written atomically (via rename) but the
timeline event was not. A crash between the two I/O calls leaves the manifest
ahead of the timeline.

**Fix:** The orchestrator can safely resume — the manifest is the source of
truth for completed stages, and the timeline is best-effort for observability.
To fix the drift, the `resume` command will note it but proceed normally.
To manually repair:
```bash
# Re-emit missing events
python3 scripts/factory_run.py emit <run-id> --evt stage_complete --stage <missing-stage>
```

### `factory_run.py status --latency` shows no data

**Symptom:** The latency output is empty or shows "no timeline available".

**Likely cause:** The run has not yet emitted any `needs_human` or
`user_decision` events. Latency tracking requires at least one approval gate
to have been triggered.

**Check:**
```bash
python3 scripts/factory_run.py tail <run-id> --json | grep -E "needs_human|user_decision"
```
