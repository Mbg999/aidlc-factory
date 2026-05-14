# Shared Spawn Loop

PRIORITY: P1

> **Load-critical.** This file is read on every stage spawn (~5.5 KB, ~1.4K tokens). Keep under 200 lines. Cold-path content (FAST_PATH, recovery, replay/adopt, project-profile) belongs in their respective `runtime/*.md` files, NOT here.

Two execution modes: **Full spawn loop** (parallel stages — uses `Task()`) and
**Post-execution loop** (sequential inline stages — no `Task()`). Both produce
identical timeline, budget, audit, and state outcomes.

## Full spawn loop (parallel stages)

Every parallel stage spawn follows this 13-step sequence. Steps 3-5 (handoff
validate → Task() → output validate) are SKIPPED for inline sequential stages.

0. **Timeline event (spawn_start)**: `python3 aidlc-scripts/factory_run.py emit <run-id> --evt spawn_start --stage <stage> --field tokens_estimate=N`

1. **Pre-flight budget gate**: `python3 aidlc-scripts/factory_budget.py check <run-id> <stage>`
   - exit `0` → spawn at full depth
   - exit `1` → set `depth: minimal` in input handoff; spawn (depth-flexible stages only)
   - exit `2` → skip; append `[CostGov] Skipped <stage> (under threshold)` to audit; continue
   - exit `3` → halt; append `[CostGov] HALT — <stage> would exceed remaining budget`; surface

2. **Knowledge query (pre-spawn)**: call `mcp__plugin_engram_engram__mem_search` with stage-derived query (see [`cross-cutting/knowledge-agent.md`](../../.claude/agents/cross-cutting/knowledge-agent.md)). Inject top-5 results (after confidence/deprecation filtering, antipattern boosting) into input handoff's `context_pointers[]` as markdown strings. Log `[Knowledge] Query <stage>: <N> priors retrieved` to audit. If engram is unavailable, leave `context_pointers[]` empty and log `[Knowledge] DEGRADED: engram unavailable`.

2.5. **Model resolution**: `python3 aidlc-scripts/factory_model.py resolve <stage>`. If output is non-empty and not the tool default, add `model_override: <model>` to input handoff. If user passed `--model` on the slash command, use that instead and skip the script.

3. **Validate input handoff** against its JSON Schema contract.

4. **Spawn subagent**: `Task(subagent_type=..., prompt=<input-handoff-path>)`. If input handoff has `model_override`, pass as `model=<model_override>`.

5. **Validate output handoff** against its JSON Schema contract.

6. **Post-flight reconciliation**: `python3 aidlc-scripts/factory_budget.py deduct <run-id> <stage> --tokens-in <N> --tokens-out <N> --wall-min <F>`
   - `tokens_in` / `tokens_out`: from agent output's `cost.{tokens_in,tokens_out}`. If absent, deduct conservative estimate from `budgets/default.yaml.per_stage[<stage>].tokens` and log `[CostGov] Estimated <stage> cost`.
   - `wall_min` is computed by the orchestrator from `timeline.jsonl`, NOT from agent output: `(spawn_end.ts - spawn_start.ts) / 60`, rounded to 1 decimal.

7. **Knowledge save (post-return)**: iterate `output.emitted_knowledge[]`. For each entry, call `mcp__plugin_engram_engram__mem_save` with topic_key `aidlc/<project_slug>/<kind>/<title-slug>`, project scope. If response includes `judgment_required: true`, apply the judgment heuristic from `knowledge-agent.md` (silent for related/compatible/scoped; surface low-confidence supersedes/conflicts_with on ADRs). Log `[Knowledge] Saved <kind>: <title>` each.

8. **Append audit_entries[] to `aidlc-docs/audit.md`** (append-only). The orchestrator owns this file — agents emit content but never write headers or timestamps.

   **Spawn-cycle blocks** (the common case): read `ts_start` and `ts_end` from `timeline.jsonl`. Dedupe guard: if the last `## ` section in `audit.md` already has the same `ts_start` AND the same stage label, SKIP. Append:
   ```
   ## <ts_start> <PHASE> - <STAGE LABEL> START
   - [Orchestrator] spawned with tokens_max=<N>, wall_clock_max_min=<M>
   - <agent's audit_entries[] bullets, one per line>

   ## <ts_end> <PHASE> - <STAGE LABEL> COMPLETE
   - [Orchestrator] tokens used: <N>, wall_min: <F>
   ```
   `<PHASE>` ∈ `{INCEPTION, CONSTRUCTION, OPERATIONS}`. `<STAGE LABEL>` = stage_id uppercased with `-` → space. Strip rogue `##` headers or fabricated timestamps from agent `audit_entries[]`.

   **Non-spawn blocks** (user decisions, answers received, stage_skipped, orchestrator notes — anything without a spawn_start/spawn_end pair) MUST use `factory_run.py emit_audit_block`. Full protocol: [`contracts/audit-block.protocol.md`](../contracts/audit-block.protocol.md).

9. **Update `aidlc-docs/aidlc-state.md`**: set `Current Stage` and `Stage Progress`.

10. **Auto-commit**: per `core-workflow.md` MANDATORY rule. `git add -A && git commit -m "<type>(<scope>): <description>"`.

11. **Timeline event (spawn_end)**: `python3 aidlc-scripts/factory_run.py emit <run-id> --evt spawn_end --stage <stage> --field status=<s> --field tokens=N --field wall_min=F`

12. **State update**: on `status: complete`, `factory_run.py complete-stage <run-id> <stage> --next-stage <next>`. On `status: failed`, `factory_run.py fail-stage <run-id> <stage> --reason "<text>"`.

13. **Halt or surface**: if `status != complete`: halt and surface. If `status == needs_human`: pause, surface in [`## Structured Approval Format`](../../.claude/agents/orchestrator.md), wait for user response, log to audit, then continue.

## Post-execution loop (inline sequential stages)

Sequential stages (workspace-scout, requirements-analyst, workflow-planner,
ship-agent) execute inline in the orchestrator instead of via `Task()`. Steps
3-5 are skipped. **Context compaction** is mandatory after every inline stage
— discard transient reasoning, preserve only structured outputs and artifacts.

After inline stage execution, run these steps in order:

0. `spawn_start` emit
1. Budget gate (steps 0-1 identical to full loop)
2. Knowledge query (pre-spawn context injection — step 2 identical)
3. **Inline execution**: read `stage/<s>.md` and execute directly — no handoff
   files, no `Task()`, no contract validation.
4. **Lightweight validation**: verify required fields present, artifact paths
   exist, critical structural invariants hold. No JSON Schema validation.
5. **Context compaction**: extract structured outputs → summarize critical
   state → discard transient reasoning. The orchestrator accumulates
   artifacts and summaries, NOT raw cognition.
6. Budget deduct (same as full loop step 6)
7. Knowledge save (same as full loop step 7)
8. Audit append (same as full loop step 8)
9. State update (same as full loop step 9)
10. Auto-commit (same as full loop step 10)
11. `spawn_end` emit (same as full loop step 11)
12. State update — complete-stage/fail-stage (same as full loop step 12)
13. Halt or surface (same as full loop step 13)

## Stage-specific deltas

| Stage | Delta |
|-------|-------|
| requirements-analyst | Two-pass: inline execution runs twice (Pass 1 → surface → Pass 2) |
| code-generator | Three sub-stages (plan → generated → approved); each runs full spawn loop with Task() |
| reviewers (pool) | Step 4 spawns all active reviewers in parallel (≤ 4); full spawn loop |
| build-test-agent | Per-unit in parallel per wave (≤ 4); full spawn loop |

## See also
- Audit block protocol: [`contracts/audit-block.protocol.md`](../contracts/audit-block.protocol.md)
- Cold-path recovery: [`runtime/recovery.md`](recovery.md)
- Budget policy: [`budgets/default.yaml`](../budgets/default.yaml)
