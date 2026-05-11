# Orchestrator Workflow Fixes — Plan (Bugs #6–#9 + wall-clock obs)

**Origin:** Live e2e test run `2026-05-11-healthz-endpoint` against `pruebaaidlcv2/`.
**Source bugs:** see `ORCHESTRATOR-LIVE-TEST-FINDINGS.md` §Bug #6–#9.
**Status:** Plan only — awaiting user approval before implementation.

---

## 0. Background — shared root cause

Three of the four bugs (#6, #7, #9) share one underlying defect: **the orchestrator does not own writes to `audit.md` and `manifest.yaml` enrichment.** Stage agents are inadvertently doing what the orchestrator should: writing audit blocks, fabricating timestamps, and signaling next-phase routing that gets ignored.

The fix pattern across all three:
- **Single writer** for `audit.md` (orchestrator only).
- **Single source of truth** for time (timeline.jsonl).
- **Single source of truth** for routing decisions (orchestrator, informed by but not bound to agent output).

Bug #8 (project_profile classification) is a separate missing-step gap in the orchestrator's run-setup sequence.

---

## 1. Fix scope per bug

### Bug #6 — Fabricated timestamps in `audit_entries`

**Root cause.** Stage agents are LLMs and don't read the wall clock. Their system prompts ask them to emit `audit_entries[]` with timestamps, so they invent plausible ones. Observed: workspace-scout wrote `2026-05-11T14:32:00Z` while timeline.jsonl says `07:15-07:27`.

**Files to change:**
- `.claude/agents/stage/workspace-scout.md` — drop timestamp instruction.
- `.claude/agents/stage/requirements-analyst.md` — drop timestamp instruction.
- `.claude/agents/stage/reverse-engineer.md` — drop timestamp instruction.
- `.claude/agents/stage/story-writer.md` — drop timestamp instruction.
- `.claude/agents/stage/workflow-planner.md` — drop timestamp instruction.
- `.claude/agents/stage/unit-decomposer.md` — drop timestamp instruction.
- `.claude/agents/stage/code-generator.md` — drop timestamp instruction.
- `.claude/agents/stage/build-test-agent.md` — drop timestamp instruction.
- `.claude/agents/stage/reviewer-{code,security,performance,simplifier}.md` — drop timestamp instruction.
- `.claude/agents/stage/ship-agent.md` — drop timestamp instruction.
- `.claude/agents/orchestrator.md` — add the audit-write step that injects timestamps.
- Optionally: schema docs in `.aidlc-orchestrator/contracts/*.output.v1.json` to clarify that `audit_entries[]` items are timestamp-free.

**Concrete changes:**

1. **Stage agent prompts** — replace audit instruction with:
   > Emit `audit_entries[]` as plain bullet lines (e.g. `[Skill] Executed: idea-refine — PASS`).
   > **Do NOT include timestamps or section headers.** The orchestrator owns time and structure.

2. **Orchestrator audit-write step (new):**
   ```
   After every Task() spawn returns:
     ts_start = grep first spawn_start event for this stage from timeline.jsonl
     ts_end   = grep matching spawn_end event for this stage
     stage_label = uppercase(stage_id).replace("-", " ")
     append to aidlc-docs/audit.md:
       "## {ts_start} {phase} - {stage_label} START"
       "- [Orchestrator] spawned with budget {tokens_max} tokens"
       (one blank line)
       for each entry in agent_output.audit_entries:
         "- {entry}"      # already plain bullet, no timestamp prefix
       (one blank line)
       "## {ts_end} {phase} - {stage_label} COMPLETE"
       "- [Orchestrator] tokens used: {tokens}, wall_min: {wall_min}"
   ```

3. Stage agents continue to write their handoff `.output.yaml` directly (per contract) — only `audit.md` is centralized.

**Test plan:**
- Re-run `/factory-spec` on a fresh run-id; diff audit.md timestamps against timeline.jsonl. Every `##` header timestamp MUST match a timeline event timestamp exactly.
- Unit test: feed a synthetic `audit_entries[]` containing a fabricated `2026-99-99T99:99:99Z` line; verify orchestrator strips/ignores it.

**Effort:** 2.5 hours (12 stage agent edits + orchestrator audit-write step + tests).

---

### Bug #7 — Duplicate workspace-detection block in `audit.md`

**Root cause.** Two writers to `audit.md`: (a) workspace-scout's `audit_entries[]` got appended by the orchestrator, AND (b) the agent's system prompt also triggered a direct `Edit/Write` to `audit.md`. The trace shows nearly-identical content with different section header conventions ("INCEPTION - Workspace Detection START" vs "WORKSPACE DETECTION - START") proving two write paths.

**Root cause within Bug #6's fix.** Once Bug #6's "orchestrator owns audit.md" rule is enforced, this disappears — provided we ALSO remove agents' permission to touch audit.md.

**Files to change:**
- `.claude/agents/stage/*.md` (all 13) — add explicit "DO NOT WRITE audit.md" to the "What you must NOT do" section. Already present in some agents (per ORCHESTRATOR-PLAN.md §5); audit and enforce universally.
- `.claude/agents/orchestrator.md` — pre-append dedupe check: if the last `##` section in `audit.md` for the same stage has the same `ts_start` we're about to write, skip the write (idempotent on retries).

**Concrete changes:**
1. Grep all 13 stage agents for current "What you must NOT do" sections. Add line:
   > Do NOT write to `aidlc-docs/audit.md` or `aidlc-docs/aidlc-state.md`. The orchestrator owns those. If your stage rule file says to write them (legacy AIDLC single-agent prose), ignore — emit `audit_entries[]` only.
2. Orchestrator audit-write step gets idempotency guard.

**Test plan:**
- Re-run `/factory-spec`; verify audit.md has exactly one block per stage (no duplicates).
- Force a stage failure + retry mid-spawn; verify the second spawn's audit append doesn't duplicate the first.

**Effort:** 1 hour (13 prompt edits + 10-line dedupe guard).

**Dependency:** Bug #6 fix lands first.

---

### Bug #8 — `project_profile` never classified

**Root cause.** `manifest.yaml` is initialized with `project_profile: {ui: false, api: false, has_legacy: false}` (factory_run.py init) but nothing ever updates these. There's no step in the orchestrator's "All flows share the same primitives" sequence that reads workspace-scout's output and writes project_profile back to manifest.

Consequence: conditional skills (`frontend-ui-engineering*`, `api-and-interface-design*`, `browser-testing-with-devtools*`, `deprecation-and-migration*`) never load because their gate (project_profile.ui / api / has_legacy) is always false.

**Files to change:**
- `.claude/agents/orchestrator.md` — add classification step.
- `scripts/factory_run.py` — add `classify-profile` subcommand OR allow `set --field project_profile.X=Y` (already supported? verify).

**Concrete changes:**

1. **Orchestrator new step "Step 3.5" (after workspace-scout completes):**
   ```
   Read workspace-scout output handoff.
   Classify project_profile:
     ui = (TypeScript|JavaScript|TSX|JSX in workspace_state.programming_languages) 
          AND (workspace_state.project_structure matches /SPA|frontend|React|Vue|Svelte|Angular|Next|Nuxt/)
     api = user_request matches /endpoint|route|REST|GraphQL|API|webhook|\/[a-z]+/i 
           OR workspace has express|fastify|hono|nestjs|fastapi|flask|django in dependencies
     has_legacy = workspace_state.reverse_engineering_artifacts_present == true 
                  OR user_request matches /migrat|refactor|deprecat|legacy|rewrite/i
   Apply via:
     python3 scripts/factory_run.py set <run-id> --field project_profile.ui=<bool>
     python3 scripts/factory_run.py set <run-id> --field project_profile.api=<bool>
     python3 scripts/factory_run.py set <run-id> --field project_profile.has_legacy=<bool>
   Append to audit.md (via orchestrator's audit-write step):
     "[Orchestrator] Classified project_profile: ui={ui}, api={api}, has_legacy={has_legacy}"
   ```

2. **`scripts/factory_run.py` `set` subcommand** — verify it accepts dotted-path field updates (e.g. `project_profile.ui`). If not, extend it. The current impl per the live test shows `--field FIELD` exists; need to confirm dotted paths work.

3. **Stage agent input prep** — when orchestrator computes `skills_required[]` for downstream stages (code-generator, build-test-agent, ship-agent), it MUST consult `manifest.project_profile` and add the conditional skills:
   - `ui: true` → add `frontend-ui-engineering` to code-generator, `browser-testing-with-devtools` to build-test-agent
   - `api: true` → add `api-and-interface-design` to code-generator
   - `has_legacy: true` → add `deprecation-and-migration` to ship-agent

**Test plan:**
- Run `/factory-spec` with `/healthz endpoint` request against the React SPA pruebaaidlcv2: expect `manifest.project_profile = {ui: true, api: true, has_legacy: false}`.
- Run against a Python CLI repo (no UI): expect `ui: false, api: false` (unless request implies API).
- Verify downstream `code-generator.input.yaml` includes `frontend-ui-engineering` and `api-and-interface-design` in `skills_required[]`.

**Effort:** 2 hours (classification logic in orchestrator prompt + factory_run.py verification/extension + downstream skill injection logic).

---

### Bug #9 — `/factory-spec` silently skips `reverse-engineer`

**Root cause.** `/factory-spec` orchestrator flow is hard-coded: workspace-scout → requirements-analyst. It doesn't branch on workspace-scout's `next_phase: reverse-engineering` signal even though the agent emitted it correctly.

**Files to change:**
- `.claude/agents/orchestrator.md` — Phase 0 sequence: add conditional reverse-engineer routing with approval gate.
- `.claude/commands/factory-spec.md` — document the new behavior.

**Concrete changes:**

1. **Orchestrator Phase 0 sequence revision (post-Step 3.5 classification, pre-requirements-analyst):**
   ```
   Step 3.6 — Reverse-engineer routing decision
   
   If workspace_state.next_phase == "reverse-engineering" 
      AND workspace_state.reverse_engineering_artifacts_present == false:
     
     Surface to user (approval gate):
       """
       ⏸️  Reverse-Engineer Recommendation
       
       Workspace Scout detected:
         - project_type: brownfield (existing code present)
         - reverse_engineering_artifacts_present: false
       
       Running `reverse-engineer` first produces:
         - aidlc-docs/inception/reverse-engineering/business-overview.md
         - architecture.md, code-structure.md, api-docs.md, component-inventory.md
         - interaction-diagrams.md, tech-stack.md, dependencies.md
       
       Recommended for: major refactors, new modules touching existing systems, 
                        or any change where the requirements-analyst would need 
                        codebase context.
       
       Skip-OK for: small features (a single endpoint, a config change, doc-only).
       
       Run reverse-engineer now? [Y/n]
       """
     
     If yes: 
       spawn reverse-engineer stage normally; 
       on completion, append to manifest.completed_stages.
     If no: 
       append to manifest.skipped_stages: ["reverse-engineer"];
       audit: "[Orchestrator] User opted to skip reverse-engineer 
               (small-scope request: '{user_request}')"
   
   Proceed to requirements-analyst regardless.
   ```

2. **`/factory-spec` slash command doc** — note the approval gate explicitly so users aren't surprised.

3. **`factory-spec --no-reverse-engineer` flag (optional, P3):** for scripted/CI use, allow bypassing the approval gate. Default behavior remains interactive.

**Test plan:**
- Run `/factory-spec` on brownfield repo with no RE artifacts: expect approval-gate prompt.
- Answer "no": expect requirements-analyst spawn, `manifest.skipped_stages = ["reverse-engineer"]`.
- Answer "yes": expect reverse-engineer spawn first, completion, then requirements-analyst.
- Run `/factory-spec` on greenfield repo (no existing code): expect no prompt, direct to requirements-analyst.
- Run `/factory-spec` on brownfield WITH existing RE artifacts: expect no prompt, direct to requirements-analyst (use existing artifacts).

**Effort:** 1.5 hours (orchestrator prompt revision + slash command doc + tests).

---

### Observation — wall_min undercounted in budget deduct

**Root cause.** Orchestrator passes a manually-estimated `--wall-min` to `factory_budget.py deduct` (often based on the "thinking" line shown in Claude Code's UI). Real wall time = `spawn_end_ts - spawn_start_ts` from timeline.jsonl. Observed: workspace-scout reported `wall_min: 1.0` but timeline shows 9m 12s.

**Files to change:**
- `.claude/agents/orchestrator.md` — post-flight reconciliation step.

**Concrete changes:**

1. **Orchestrator post-spawn deduct step revision:**
   ```
   After Task() returns:
     ts_start = timeline.jsonl spawn_start event for this stage (already captured pre-spawn)
     ts_end   = now()  (call date -u via Bash if needed)
     actual_wall_min = round((ts_end - ts_start) / 60, 1)
     
     tokens_in, tokens_out = parse from agent output's cost block 
                              (or estimate from default.yaml if missing)
     
     python3 scripts/factory_budget.py deduct <run> <stage> \
       --tokens-in {tokens_in} --tokens-out {tokens_out} \
       --wall-min {actual_wall_min}
   ```

**Test plan:**
- Run `/factory-spec`; verify `budget.yaml` per-stage `wall_min` matches `(spawn_end - spawn_start)` from timeline.jsonl within ±0.2 minutes for every stage.

**Effort:** 30 minutes.

---

## 2. Execution order

Recommended sequence (top-down dependency):

| Step | Bug | Why this order |
|---|---|---|
| 1 | #6 (audit timestamps) | Foundation — establishes "orchestrator owns audit.md" rule. |
| 2 | #7 (duplicate blocks) | Direct continuation of #6 — same single-writer principle, just adds the dedupe guard. Cheap once #6 is done. |
| 3 | #8 (project_profile) | Independent of #6/#7 but conceptually the same "orchestrator enriches manifest" pattern. |
| 4 | #9 (RE routing) | Independent. Could be done first if user prefers, but the approval-gate UI shares format with other gates added by #8. |
| 5 | wall-clock obs | Trivial, batch with any of the above. |

**Parallelism:** #6+#7 must be sequential. #8 and #9 are independent of each other and of #6/#7 — could be implemented in parallel by different sub-agents, but realistically one-shot serial is faster than coordinating parallel edits to orchestrator.md (high contention file).

---

## 3. Validation strategy

After all five fixes land:

1. **Replay the e2e** — same user request (`/healthz endpoint`) against pruebaaidlcv2, but on a new run-id. Compare:
   - audit.md: timestamps match timeline.jsonl ✅
   - audit.md: one block per stage ✅
   - manifest.yaml: `project_profile = {ui: true, api: true, has_legacy: false}` ✅
   - User receives reverse-engineer approval-gate prompt ✅
   - budget.yaml `wall_min` per stage matches timeline ±0.2 min ✅

2. **Compare full run diff vs the May 11 baseline** — most artifacts should be identical (requirements.md, knowledge entries) because the actual stage outputs are unchanged. Only the *plumbing* changes.

3. **Cross-check `pruebaaidlcv2/aidlc-docs/audit.md`** — should be ~half the line count it was on May 11 (no duplication, no fabricated headers from agents).

---

## 4. Out of scope (deliberate)

These were flagged in the live test but are NOT in this fix pass:

- **Mid-flight cancellation** — Cost Governor §Limitations. Requires Claude Code SDK changes. Tracked in ORCHESTRATOR-PLAN.md as Phase 7+.
- **Adaptive depth real-world validation** — only triggers when budget < 30% remaining. The /healthz run used 2.5%. Will surface naturally in a future big run.
- **Parallel reviewer pool wall-clock** (Phase 4 acceptance) — needs an actual `/factory-review` run. Pending user e2e continuation.
- **Two-unit shared-module conflict** (Phase 5 acceptance) — needs a deliberately multi-unit feature. Pending.

---

## 5. Risks

| Risk | Mitigation |
|---|---|
| Editing 13 stage agent prompts for Bug #6/#7 may regress other behaviors. | Each edit is additive (one new "DO NOT" line + removal of timestamp instruction). Diff each before/after; spot-test workspace-scout + requirements-analyst at minimum before declaring done. |
| Orchestrator audit-write step adds latency per spawn. | Negligible — one file append + 2 timeline reads. <100ms. |
| `factory_run.py set --field project_profile.ui=true` may not support dotted paths today. | Verify in Step 1 of implementation; extend the script if needed. Small change (~10 lines). |
| Bug #9 approval gate becomes annoying for repeated small features. | Add `--skip-reverse-engineer` flag and a per-project default in `manifest.yaml` (e.g. `defaults.reverse_engineer: never|ask|always`). Defer this to P3 unless user requests. |
| Backward-compat with the May 11 adopted run (`2026-05-11-healthz-endpoint`). | None — that run is already past Phase 0. The fixes only affect future runs. |

---

## 6. Total effort estimate

| Item | Hours |
|---|---|
| Bug #6 — strip-and-inject timestamps | 2.5 |
| Bug #7 — single-writer enforcement + dedupe | 1.0 |
| Bug #8 — project_profile classifier + skill injection | 2.0 |
| Bug #9 — RE approval-gate routing | 1.5 |
| Wall-clock observation | 0.5 |
| Validation replay (full /factory-spec e2e) | 1.0 (user-supervised) |
| **Total** | **~8.5 hours** (6.5h dev + 1h validation + 1h slack) |

---

## 7. Acceptance

After implementation, ORCHESTRATOR-LIVE-TEST-FINDINGS.md gets:
- Bug #6/#7/#8/#9 marked ✅ FIXED with the same shape as #1–#5.
- Wall-clock observation noted as resolved.
- Replay run-id documented as evidence.

Then we proceed with **continuing the May 11 e2e** (`/factory-plan` → `/factory-build` → `/factory-review` → `/factory-ship` on `2026-05-11-healthz-endpoint`) to surface any Phase 1/4/5/6 bugs that script-layer tests can't reach. That's the next loop.
