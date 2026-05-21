# Orchestrator Bug Fix Plan — 2026-05-11

**Trigger:** Live `/factory-spec` + `/factory-plan` e2e test on `pruebaaidlcv2/` (run_id `2026-05-11-healthz-endpoint`) surfaced 5 bugs across rule, vocabulary, and content layers.

**Status legend:** `PENDING` → `IN_PROGRESS` → `DONE` · `SKIPPED` (with reason) · `DEFERRED` (with reason)

---

## Bug A-generalized — Approval-gate audit blocks wall-clock their timestamps

**Severity:** High (will recur on every remaining `/factory-plan`, `/factory-build`, `/factory-ship` gate)
**Status:** `DONE`
**Recurrence:** at least 5 more gates without this fix.

**Root cause:** The original Bug A fix patched only `requirements-analyst` Pass 1 instruction 6. Every other approval gate in `orchestrator.md` still says "orchestrator surfaces and waits" with no instruction to emit a timeline event before writing the audit header. The shared-primitives Step 8 substep 6 has the general rule but is a cross-reference, not an inline mandate.

**Fix approach:** define a single canonical decision evt (`user_decision`), promote shared-primitives Step 8 substep 6 to a self-contained mandate, and inline the rule at every approval gate so the agent doesn't have to follow a cross-reference.

**Sub-tasks:**
- [x] `A.1` — Promote shared-primitives Step 8 substep 6 from cross-reference to self-contained mandate (full procedure inline). Define canonical evt vocabulary: `user_answers_received` for clarifying-question responses (already exists), `user_decision` for approval gates.
- [x] `A.2` — Patch Step 3.5 reverse-engineer approval gate (Phase 0)
- [x] `A.3` — Normalize Step 4 Pass 1 instruction 6 (already patched, just align to canonical vocab)
- [x] `A.4` — Patch `/factory-plan` Step 2 workflow-planner approval gate (caused Bug C)
- [x] `A.5` — Patch `/factory-build` per-unit approval gate (would cause next Bug C-class recurrence)
- [x] `A.6` — Patch `/factory-build` layer approval gate
- [x] `A.7` — Patch Step 6 generic Approval gate + outcome

---

## Bug C — Workflow-planner approval at 13:55:00Z has no timeline event

**Severity:** Already manifested; subsumed by A-generalized.
**Status:** `SKIPPED` (rolled into Bug A-generalized; same root cause)

---

## Bug D — `stage_skipped` recovery is undocumented; three sources disagree

**Severity:** Medium (cosmetic now, will confuse `/factory-resume` and `/factory-replay`)
**Status:** `DONE`

**Root cause:** When a stage spawn fails and the orchestrator decides to recover via skip-fallback (e.g. `unit-decomposer` 1M-context unavailability), no timeline event records the skip. The failed `spawn_end` remains in timeline.jsonl, but `manifest.skipped_stages[]` and `audit.md` header say "SKIPPED". Three views, three answers.

**Fix approach:** document the failed→skipped recovery pattern in orchestrator.md and require an explicit `stage_skipped` event emission.

**Sub-tasks:**
- [x] `D.1` — Add a "Failed→skipped recovery" subsection to orchestrator.md (in Run Manager block or shared-primitives) defining the canonical sequence: detect fail → log to audit → decide skip-vs-halt by stage criticality → emit `stage_skipped` event → add to `manifest.skipped_stages[]` → audit header uses the skip event's ts.
- [x] `D.2` — No `factory_run.py` code change required (`emit` is freeform).

---

## Bug E — `execution-plan.md` FR/NFR split mis-labeled

**Severity:** Cosmetic (one-off, content-only)
**Status:** `DONE`

**Root cause:** Plan file line 311 says "All 29 ACs (20 FR + 9 NFR) covered". Total is correct; the FR/NFR split is off-by-one. Actual: 19 FR + 10 NFR.

**Fix approach:** single-line edit to the file. No rule change.

**Sub-tasks:**
- [x] `E.1` — Replaced "(20 FR + 9 NFR)" with "(19 FR + 10 NFR)" at `pruebaaidlcv2/aidlc-docs/inception/plans/execution-plan.md:311`

---

## Bug F — `unit-decomposer` triggers "Extra usage is required for 1M context"

**Severity:** Low / config (graceful degradation already works)
**Status:** `DONE` (F1 done; F2 deferred)

**Real root cause** (different from initial hypothesis): `unit-decomposer.md` already declared `model: sonnet` since file creation. The 1M-context trigger came from the **budget**, not the model — `budgets/default.yaml` declared `unit-decomposer: tokens_max=400_000`, exceeding Sonnet's 200K standard context window. Anthropic's API then required the 1M-context extension, which the user's plan has unlocked for Opus but not Sonnet (that's why `workflow-planner` at `tokens_max=600_000` succeeded under `model: opus`). Actual unit-decomposer workload is <50K tokens; the 400K budget was wildly over-provisioned.

**Fix approach (revised):** F.1 — lower `unit-decomposer.tokens` from `400_000` → `150_000` (well under 200K standard tier). F.2 (pre-spawn model availability check) still deferred.

**Note for future:** Other Sonnet-model stages with budgets >200K (`story-writer: 300K`, `build-test-agent: 300K`) may hit the same wall when their input handoffs grow. Track and adjust per stage when observed.

**Sub-tasks:**
- [x] `F.1` — Lowered `unit-decomposer.tokens` in `budgets/default.yaml` from `400_000` → `150_000` with inline comment explaining the 1M-context trigger.
- [ ] `F.2` — DEFERRED — pre-spawn model availability check via `factory_run.py check-model`. Revisit if other stages hit the same wall.

---

## Retro-fixes to the current run's artifacts

After rule fixes land, retro-correct the on-disk state in `pruebaaidlcv2/` for run_id `2026-05-11-healthz-endpoint`.

**Status:** `DONE`

**Sub-tasks:**
- [x] `R.1` — Appended `user_decision` event for workflow-planner approval at `13:55:00+00:00` to `timeline.jsonl` (annotated as retro-fix)
- [x] `R.2` — Appended `stage_skipped` event for unit-decomposer at `13:57:46+00:00` to `timeline.jsonl` (annotated; preserves raw failed `spawn_end` for diagnostics)
- [x] `R.3` — FR/NFR label correction applied to `execution-plan.md:311` (Bug E)
- [x] `R.4` — Chronology + cross-check passed: 12 audit headers strictly monotonic; only 1 ungrounded header (`12:20:00Z Workspace Detection COMPLETE`) — pre-orchestrator legacy format, not a regression

---

## Execution order

1. Fix A-generalized (sub-tasks A.1 → A.7)
2. Fix D (D.1)
3. Fix F (F.1)
4. Fix E + retro-fixes (E.1, R.1–R.4)
5. Verify with the chronology + cross-check script

**Files expected to change:**
- `.claude/agents/orchestrator.md` (A.1–A.7, D.1) — ~50–80 lines added
- `.claude/agents/stage/unit-decomposer.md` (F.1) — model field
- `pruebaaidlcv2/.aidlc-orchestrator/runs/2026-05-11-healthz-endpoint/timeline.jsonl` (R.1, R.2) — 2 lines appended
- `pruebaaidlcv2/aidlc-docs/inception/plans/execution-plan.md` (E.1) — 1 line

No new scripts, no new contracts.
