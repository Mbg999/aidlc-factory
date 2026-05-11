# Orchestrator Live Integration Test — Findings & Follow-up Plan

**Tested:** 2026-05-09 against fresh install at `pruebaaidlcv2/`
**Coverage:** Phases 0-6 (script/runtime layer). Subagent-spawn-level e2e tests still require user-triggered `/factory-spec` runs inside the consumer project.

---

## Test Matrix

| Phase | Layer Tested | Result |
|---|---|---|
| 0 | Schema parse + validator exit codes | ✅ 20/20 schemas valid; validator returns 0/1 correctly |
| 1 | Stage agent definitions present | ✅ 13/13 stage agents + 2 cross-cutting + orchestrator + 7 commands |
| 2 | Cost Governor: init/check/deduct/status; 4 exit codes; downshift | ✅ all paths (ok=0, downshift=1, skip=2, halt=3) |
| 3 | Knowledge Agent: topic_key roundtrip via engram | ✅ save+search with `aidlc/<slug>/<kind>/<title-slug>` namespacing |
| 4 | Reviewer merge: full / partial / missing | ✅ all 3 scenarios with valid fixtures |
| 5 | Conflict Resolver: path-locks (4 cases) + Python AST drift + TS AST drift + JSX | ✅ all 8 sub-cases |
| 6 | Run Manager: init / complete / fail / resume / replay / adopt-legacy | ✅ but see Bug #5 below |

---

## Findings

### Bug #1 — Cost Governor lacks committed reference doc (LOW, doc-only) — ✅ FIXED 2026-05-09
**Symptom:** `.claude/agents/cross-cutting/` contained `knowledge-agent.md` and `conflict-resolver.md` but NOT `cost-governor.md`. ORCHESTRATOR-PLAN.md §12 acceptance criteria states "All 13 stage agents + 3 cross-cutting agents have committed schemas" — Cost Governor is the third cross-cutting agent.
**Impact:** Documentation completeness only. Runtime is unaffected.
**Fix shipped:** `.claude/agents/cross-cutting/cost-governor.md` written with same shape as the other two cross-cutting docs — purpose, four-path decision table, integration points, surfacing protocol, limitations, configuration reference. Propagated to `pruebaaidlcv2/` via install_aidlc.py.

### Bug #2 — `cost_max_usd` is policy-only (LOW, design choice) — ✅ FIXED 2026-05-09 (Option B)
**Symptom:** `budgets/default.yaml` declared `cost_max_usd: 50` but `factory_budget.py` never populated `used.cost_usd` because there was no token-rate table.
**Impact:** USD accounting was silently broken.
**Fix shipped (Option B — drop):** Removed `cost_max_usd: 50` from `budgets/default.yaml`. Removed `cost_usd: 0.0` from the initial `used` block in `scripts/factory_budget.py`. Updated `cost-governor.md` Limitations to note the deliberate drop and document the revival path (add `pricing` block keyed by model). Token budget remains the sole hard constraint.
**Verified:** `init` + `status` + `deduct` cycle on a fresh run still works after the field removal.

### Bug #3 — `factory_merge_reviews.py` crashes on malformed reviewer output (MEDIUM, robustness) — ✅ FIXED 2026-05-09
**Symptom:** If a reviewer's output YAML omits the schema-required `findings[].message` field, the merge script raises `KeyError: 'message'` with a Python traceback. No graceful fallback or schema-validation step.
**Impact:** A single malformed reviewer output crashes the entire merge; the user gets a stack trace, not a usable report.
**Fix shipped:**
1. `_load_validator()` builds a Draft7 validator from `reviewer.output.v1.json`. Each reviewer output is validated before merge; schema-invalid outputs are skipped with `WARNING: skipping <reviewer> (schema-invalid output)` + first 5 errors. Report header now includes `_Skipped (schema-invalid output): <list>_`.
2. `render_finding` now uses `f.get("message", "_(no message provided)_")` as defense-in-depth.
3. Graceful degradation: if `jsonschema` isn't installed, validator returns None and merge falls back to .get() defenses without contract enforcement.
4. Verified: invalid+valid mix, all-valid (no warnings), and degraded-mode all pass.

### Bug #4 — Severity enum is too narrow (LOW, schema design) — ✅ FIXED 2026-05-09
**Symptom:** `reviewer.output.v1.json` `severity` enum was `["P0", "P1", "P2"]`. Real reviewer findings often need a "P3 / info / nit" tier.
**Impact:** Reviewers either inflated trivial findings to P2 or omitted them.
**Fix shipped:** Extended `severity` enum to `["P0", "P1", "P2", "P3"]`. Added `P3_count` (required) to `findings_summary`. Updated `factory_merge_reviews.py SEVERITY_ORDER`. Updated all 4 reviewer agent docs (reviewer-code/security/performance/simplifier) with P3 wording per their domain. Updated `reviewer-code.md`'s "findings_summary" reminder line to include P3_count.
**Verified:** Full e2e — 4 reviewers each emitting a P3 finding flow through merge correctly; report shows `P3 | 1 | 1 | 1 | 1 | 4` row.

### Bug #5 — `adopt-legacy` ignores the explicit "Current Stage" line (MEDIUM, UX) — ✅ FIXED 2026-05-09
**Symptom:** Legacy `aidlc-docs/aidlc-state.md` typically contains both `[x] Stage Progress` markers AND a `## Current Stage` line (e.g., `INCEPTION - Workflow Planning`). `adopt-legacy` only reads `[x]` markers and sets `current_stage` to the last-completed stage. After adoption, `resume` walks PHASE_ORDER and may suggest a CONDITIONAL stage the legacy run had already decided to skip (e.g., `story-writer` instead of `workflow-planner`).
**Impact:** First post-adoption resume routes to the wrong next stage. User has to manually re-route.
**Repro:**
```
aidlc-state.md:
## Current Stage
INCEPTION - Workflow Planning
## Stage Progress
- [x] Workspace Detection
- [x] Requirements Analysis

Result: adopt-legacy → resume → next_stage_suggestion: "story-writer"
Expected:                              next_stage_suggestion: "workflow-planner"
```
**Fix shipped:**
1. New `_legacy_current_stage(state_text)` parser reads the `## Current Stage` block, strips phase prefixes ("INCEPTION - ", etc.), maps via `LEGACY_TO_PHASE` (with PHASE_ORDER substring fallback).
2. `cmd_adopt_legacy` now: when legacy_current is parseable AND ahead of last completed in PHASE_ORDER, sets `manifest.current_stage = legacy_current` and populates `manifest.skipped_stages[]` with the conditional stages (`reverse-engineer`, `story-writer`, `unit-decomposer`) that fall in the gap. Falls back to old "current = last completed" when no `## Current Stage` line is present.
3. `_next_stage()` updated to skip over `skipped_stages[]` during PHASE_ORDER scan.
4. Verified: 3 scenarios pass — original bug case, missing-Current-Stage fallback, Stories-actually-done. Non-legacy resume regression also passes.

### Finding (initial-pass) — Live e2e tests still pending (DOC, by design — superseded by Phase 0 e2e on 2026-05-11)
The `[ ]` items per phase in ORCHESTRATOR-PLAN.md§9 are subagent-spawn-level tests:
- Phase 0/1: real `/factory-spec` end-to-end
- Phase 2: artificially low budget halts cleanly (real subagent token usage)
- Phase 3: second run on same project shows reduced tokens on requirements-analyst
- Phase 4: review stage wall-clock drops 3-4× vs sequential
- Phase 5: two parallel code-generators with shared module surface conflict
- Phase 6: kill mid-`requirements-analyst` Pass 1, resume, identical artifacts

These can't be run from the AIDLC source-repo session — they need `cd pruebaaidlcv2 && claude` then `/factory-spec <feature>`. **Not bugs**, just deferred tests. Phase 0 e2e ran on 2026-05-11 (run_id `2026-05-11-healthz-endpoint`) and surfaced Bugs #6-#9 below.

---

## Findings from Phase 0 e2e (2026-05-11)

Live `/factory-spec` against pruebaaidlcv2 surfaced four additional bugs (#6-#9)
plus a wall-clock observation. All fixed in source repo and propagated via
`install_aidlc.py` to `pruebaaidlcv2/`.

### Bug #6 — Stage agents fabricate audit timestamps (MEDIUM) — ✅ FIXED 2026-05-11

**Symptom:** `workspace-scout.output.yaml` audit_entries claimed `2026-05-11T14:32:00Z` (afternoon UTC). `timeline.jsonl` showed the actual time was `07:15-07:27` (~7h earlier). Agents are LLMs without wall-clock access — they invent plausible timestamps when prompted to include them.

**Fix shipped:**
1. All 13 stage agent system prompts updated: `audit_entries[]` now MUST be plain bullet lines with NO `##` section headers and NO timestamps. Agents informed the orchestrator wraps with `## <ts> ... START/COMPLETE` headers using `timeline.jsonl` timestamps when appending to `audit.md`.
2. Orchestrator `.claude/agents/orchestrator.md` shared-primitives step 8 rewritten with explicit procedure: read `ts_start`/`ts_end` from timeline.jsonl, dedupe-guard against retries, wrap agent entries in dated headers, defensively strip any rogue `##` lines.
3. All 3 per-flow audit-append callouts (Phase 0 step 7, parallel-spawn template, reviewer-pool step 4) updated to reference the canonical step 8 procedure.

**Verified:** factory_run.py smoke tests pass; orchestrator.md grep shows `dedupe-guarded` references in 4 places; agent prompts no longer have `<ts>` / `<ISO8601>` placeholders.

### Bug #7 — Duplicate `aidlc-docs/audit.md` blocks (MEDIUM) — ✅ FIXED 2026-05-11

**Symptom:** `aidlc-docs/audit.md` had two near-identical workspace-detection blocks with different section-header conventions ("INCEPTION - Workspace Detection START" vs "WORKSPACE DETECTION - START") — proof of two write paths.

**Fix shipped:**
1. All 13 stage agents now have explicit "Do not modify `aidlc-docs/audit.md` or `aidlc-docs/aidlc-state.md` directly. Emit `audit_entries[]` only — the orchestrator owns those files." in their "What you must NOT do" section. Previously 9 of 13 were missing this. (workspace-scout, code-generator, requirements-analyst, reverse-engineer already had it; the other 9 were missing.)
2. Orchestrator step 8 dedupe guard: if `audit.md`'s last `## ` section already has the same `ts_start` AND the same stage label, the append is skipped (idempotent on retries).

**Verified:** all 13 stage agents now contain `audit.md` prohibition (grep count ≥1 each).

### Bug #8 — `project_profile` never classified (LOW, blocks conditional skills) — ✅ FIXED 2026-05-11

**Symptom:** `manifest.yaml.project_profile` always `{ui: false, api: false, has_legacy: false}` because nothing in the orchestrator flow updated it post-workspace-scout. Conditional skills (`frontend-ui-engineering*`, `api-and-interface-design*`, `browser-testing-with-devtools*`, `deprecation-and-migration*`) gated on these flags never load.

**Fix shipped:**
1. New "Step 3.5 — Classify `project_profile`" in orchestrator.md, runs after workspace-scout completes. Three heuristics:
   - `ui: true` if TypeScript/JavaScript in languages AND project_structure matches SPA/frontend/React/Vue/Svelte/Angular/Next/Nuxt patterns, or workspace has a UI-framework dep.
   - `api: true` if user_request matches `/endpoint|route|REST|GraphQL|API|webhook|\/[a-z]...` OR workspace has express/fastify/hono/nestjs/fastapi/flask/django.
   - `has_legacy: true` if reverse-engineering artifacts present OR user_request mentions migrate/refactor/deprecate/legacy/rewrite/port.
2. Applied via `factory_run.py set <run-id> --field project_profile.ui=...` (dotted-path support added to `cmd_set` — new helper `_set_dotted`).
3. Step 3.5 also documents conditional-skill injection: when building input handoffs for `code-generator`, `build-test-agent`, `ship-agent`, the orchestrator MUST read `manifest.project_profile` and add the corresponding skills + paths.

**Verified:** factory_run.py dotted-path smoke test passes (`project_profile.ui=true` + `project_profile.api=true` survives a round-trip through `status`).

### Bug #9 — `/factory-spec` silently skips `reverse-engineer` (MEDIUM) — ✅ FIXED 2026-05-11

**Symptom:** workspace-scout emits `next_phase: reverse-engineering` for brownfield-without-artifacts, but `/factory-spec` orchestrator skipped it without asking. Risk: requirements-analyst runs without codebase context on a brownfield repo and makes wrong assumptions for major changes.

**Fix shipped:**
1. Orchestrator Step 3.5 Section B: if `workspace_state.next_phase == "reverse-engineering"` AND no RE artifacts present, surface an approval gate via `AskUserQuestion` with options "Run reverse-engineer first (recommended for big changes)" / "Skip and go straight to requirements-analyst (OK for small features)".
2. If yes: spawn `reverse-engineer` stage following shared-primitives; on completion, append to `manifest.completed_stages[]`, then proceed to Step 4.
3. If no: `factory_run.py set --field skipped_stages='["reverse-engineer"]'`, append `[Orchestrator] User opted to skip reverse-engineer` to next stage's audit block, proceed to Step 4.
4. If workspace-scout didn't flag RE-needed (greenfield, or brownfield-with-artifacts): no prompt; proceed directly.
5. `.claude/commands/factory-spec.md` updated to document the new Step 3.5 behavior.

**Verified:** factory-spec command doc updated; orchestrator.md contains the new approval-gate spec; backward-compatible (greenfield runs see no change).

### Wall-clock observation — `wall_min` undercounted in budget deduct — ✅ FIXED 2026-05-11

**Symptom:** Workspace-scout `wall_min: 1.0` in budget.yaml but spawn_start→spawn_end timeline delta was 9m 12s. Orchestrator was eyeballing Task() UI durations instead of computing from timeline.

**Fix shipped:**
1. Orchestrator shared-primitives step 6 (post-flight reconciliation) explicitly states: "wall_min is computed by the orchestrator, NOT taken from the agent output. Read matching spawn_start and spawn_end events from timeline.jsonl and compute (spawn_end.ts - spawn_start.ts) / 60, rounded to 1 decimal. This is authoritative because agent-reported wall-clock is unreliable."
2. Per-flow callouts (Phase 0 workspace-scout 6a, requirements-analyst, reviewer pool §Wall-clock acceptance) all updated to `<computed_wall_min>` and reference shared-primitives step 6.

**Verified:** grep shows `cost.wall_clock_min` no longer referenced as authoritative; `computed_wall_min` is the new pattern in all 3 deduct call sites.

---

## Plan

| # | Item | Effort | Priority | Status |
|---|---|---|---|---|
| 1 | Bug #5 — adopt-legacy "Current Stage" parsing + skipped_stages | 1.5h | **P1** | ✅ FIXED |
| 2 | Bug #3 — factory_merge_reviews.py validate-then-merge + .get() fallback | 45m | **P1** | ✅ FIXED |
| 3 | Bug #4 — Add P3 severity tier | 30m | P2 | ✅ FIXED |
| 4 | Bug #1 — Add cost-governor.md reference doc | 30m | P2 | ✅ FIXED |
| 5 | Bug #2 — Decide A/B on cost_max_usd, then implement | 15m | P3 | ✅ FIXED (Option B) |
| 6 | Live e2e Phase 0 in pruebaaidlcv2 (`/factory-spec /healthz endpoint`) | done | **P1** | ✅ COMPLETED 2026-05-11 (run_id `2026-05-11-healthz-endpoint`) |
| 7 | Bug #6 — Stage agents fabricate audit timestamps | 2.5h | **P1** | ✅ FIXED 2026-05-11 |
| 8 | Bug #7 — Duplicate workspace-detection block in audit.md | 1.0h | **P1** | ✅ FIXED 2026-05-11 |
| 9 | Bug #8 — project_profile never classified | 2.0h | P2 | ✅ FIXED 2026-05-11 |
| 10 | Bug #9 — `/factory-spec` silently skips reverse-engineer | 1.5h | **P1** | ✅ FIXED 2026-05-11 |
| 11 | Wall-clock observation — deduct uses timeline deltas | 30m | P2 | ✅ FIXED 2026-05-11 |
| 12 | Live e2e Phases 1-6 in pruebaaidlcv2 (continue from run_id above) | 1-2h user-time | **P1** | 🔲 PENDING |

**All script-layer + Phase 0 subagent bugs fixed (10/10).** Phase 0 e2e proved the orchestrator works end-to-end at the subagent level; bugs #6-#9 (+ wall-clock) all came from that e2e and are now fixed in the source repo + propagated to `pruebaaidlcv2/` via re-install. Remaining: continue e2e through Phases 1-6 (`/factory-plan` → `/factory-build` → `/factory-review` → `/factory-ship` on `2026-05-11-healthz-endpoint`) to exercise parallel reviewer pool wall-clock and unit conflict detection.

---

## What this test pass DID NOT cover

- **Subagent system prompts.** Each stage agent's `.md` is loaded as a system prompt by Claude Code at Task() spawn. None of those prompts have been exercised against a real LLM in this pass.
- **Skill execution protocol enforcement.** §5.1 of ORCHESTRATOR-PLAN.md says every subagent must paste the 6-step protocol verbatim. I haven't audited every stage agent file to confirm presence — only verified the files exist.
- **Concurrency cap (4 simultaneous).** Only testable with a real `/factory-build` against a multi-unit feature.
- **`context_pointers[]` token budget (~2,500).** Only meaningful when an LLM consumes them.
- **Post-stage emit→engram→prior-retrieval loop.** Tested the round-trip primitives (Phase 3) but not the orchestrator's wiring.
