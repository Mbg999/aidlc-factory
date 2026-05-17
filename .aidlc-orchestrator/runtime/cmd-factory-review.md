# `/factory-review` — Phase 1 review

PRIORITY: P2

Post-generation quality gate. **Parallel fan-out:** all reviewers in one
`Task()` batch (≤ 4 concurrent).

| Reviewer | Stage ID | Skill |
|---|---|---|
| Code quality | `reviewer-code` | code-review-and-quality |
| Security | `reviewer-security` (Opus) | security-and-hardening |
| Performance | `reviewer-performance` | performance-optimization |
| Simplifier | `reviewer-simplifier` | code-simplification |

All share `reviewer.input.v1.json` / `reviewer.output.v1.json`.

> **Framework skills** are available here if `/factory-build` ran first (they are stored in
> `manifest.skill_paths_resolved` after Pre-Build Step 0). Reviewers inherit this list.

## Flow

1. **Active set** — default all four; constrain to `manifest.reviewer_pool[]` if set.
2. **Knowledge queries** (sequential): `mem_search` per reviewer with specific tags; inject top-5.
3. **Parallel spawn** — ONE message, all `Task()` calls together. Wait for returns.
4. **Per-reviewer post-processing** (any order): validate → knowledge save → audit append.
6. **Merge**: `factory_merge_reviews.py <run-id> [--reviewers <active-set>]` → review report.
7. **Approval gate**: surface report. On user response:
   - Fixes requested → route units back through `/factory-build`.
   - Approved → auto-commit `docs(review): complete review report`, update state, offer `/factory-ship`.
