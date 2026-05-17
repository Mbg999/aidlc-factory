# `/factory-review` — Phase 1 review

PRIORITY: P2

Post-generation quality gate. **Parallel fan-out:** active reviewers in one
`Task()` batch (≤ 4 concurrent).

## Reviewer pool

| Reviewer | Stage ID | Skill | Active by default |
|---|---|---|---|
| Code quality | `reviewer-code` | code-review-and-quality | **Yes** |
| Security | `reviewer-security` | security-and-hardening | **Yes** |
| Performance | `reviewer-performance` | performance-optimization | No — `--full` only |
| Simplifier | `reviewer-simplifier` | code-simplification | No — `--full` only |

All share `reviewer.input.v1.json` / `reviewer.output.v1.json`.

**Default active set**: `[reviewer-code, reviewer-security]` — covers the findings that block
shipping. Pass `/factory-review --full` to activate all four (adds performance + simplifier).

> **Model note:** `reviewer-security` runs on Sonnet. For high-stakes audits pass
> `/factory-review --model opus` to upgrade the security reviewer only.

> **Framework skills** are available here if `/factory-build` ran first (they are stored in
> `manifest.skill_paths_resolved` after Pre-Build Step 0). Reviewers inherit this list.

## Flow

### Pre-Review Step 0 — CodeGraph symbol cache (skip if `.codegraph/codegraph.db` absent)

Run inline in the orchestrator before spawning any reviewers. Goal: compute callers + impact
for every symbol in the generated unit ONCE, share the result via a cache file so reviewers
never duplicate these queries.

1. Collect `source_paths[]`: read all `code-generator.output.yaml` handoffs for this run;
   extract `artifacts[].path` where `kind == "source"`.
2. For each unique parent directory in `source_paths[]`, call `codegraph_files <dir>` →
   accumulate all symbol names. Deduplicate. Cap at 60 symbols (prioritise exported/public ones
   if over cap — heuristic: no leading `_`, not `test_*`).
3. For each symbol (sequentially, batch of ≤ 60):
   - `codegraph_callers <symbol>` → record `caller_count` + caller list
   - `codegraph_impact <symbol> --depth 2` → record `blast_radius` + impact list
4. Write to `.aidlc-orchestrator/runs/<run-id>/codegraph-cache.json`:
   ```json
   {
     "generated_at": "<ISO8601>",
     "source_files": ["<path>", ...],
     "symbols": {
       "<symbol_name>": {
         "file": "<path>",
         "caller_count": 0,
         "callers": [],
         "blast_radius": 0,
         "impact": []
       }
     }
   }
   ```
5. Set `codegraph_cache_path: .aidlc-orchestrator/runs/<run-id>/codegraph-cache.json` in every
   reviewer's input handoff.

Log: `[CodeGraph] Pre-computed <N> symbols → codegraph-cache.json`

If any step fails (codegraph unavailable, timeout): write an empty cache
`{"symbols": {}}` and continue — reviewers fall back to live calls transparently.

---

1. **Active set** — default `[reviewer-code, reviewer-security]`; use all four if `--full` flag set; constrain to `manifest.reviewer_pool[]` if set.
2. **Knowledge queries** (sequential): `mem_search` per reviewer with specific tags; inject top-5.
3. **Parallel spawn** — ONE message, all `Task()` calls together. Wait for returns.
4. **Per-reviewer post-processing** (any order): validate → knowledge save → audit append.
5. **Merge**: `factory_merge_reviews.py <run-id> [--reviewers <active-set>]` → review report.
6. **Approval gate**: surface report. On user response:
   - Fixes requested → route units back through `/factory-build`.
   - Approved → auto-commit `docs(review): complete review report`, update state, offer `/factory-ship`.
