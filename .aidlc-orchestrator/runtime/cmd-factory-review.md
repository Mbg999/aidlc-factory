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

> **Framework skills** propagation: after Pre-Build Step 0, autoskills (e.g., `angular-developer`,
> `typescript-advanced-types`) are stored in `manifest.skill_paths` (and in each
> `code-generator.*.output.yaml` under `skill_paths_resolved`). Pre-Review Step 0.5 collects
> them and injects them into `reviewer-code`'s input handoff so the code reviewer has the same
> framework context as the generator.

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

### Pre-Review Step 0.5 — Collect framework skills from build

Run inline before building reviewer handoffs. Goal: propagate autoskill (framework) context
from the build phase into `reviewer-code` so it applies framework-specific idioms during review.

**Base skills** are defined by the union of workflow-required skills in
`aidlc-scripts/install_aidlc.py:WORKFLOW_REQUIRED_SKILLS` and `using-agent-skills`.
These are the universal process/quality skills that every agent should always load.
Everything else discovered by `select` is a **framework skill** (conditional, tech-stack-specific).

1. Read `manifest.yaml` → collect `skill_paths_resolved` map (all discovered skills).
2. Additionally, read all `code-generator.*.output.yaml` handoffs; union their `skill_paths_resolved[]`.
3. **Framework skills** = any skill NOT in the base set (from `WORKFLOW_REQUIRED_SKILLS`)
   whose SKILL.md exists on disk.
4. Store as `framework_skill_paths: {name: path, ...}` in the orchestrator's working state (not
   persisted to manifest — this is ephemeral per review run).
5. Log: `[Review] Framework skills from build: [<name>, ...]` (empty list is fine — log it anyway).

If no code-generator handoffs exist (review invoked without a prior build): `framework_skill_paths = {}`.

---

### Pre-Review Step 0.75 — Build Validation

Run inline before spawning reviewers. Goal: catch cross-unit integration issues
that per-unit builds (Step B.3 of `/factory-build`) may miss — the full merged
tree must still compile before quality review begins.

1. **Detect build system** — probe workspace root for known build files in this
   priority order. First match wins:

   | Detection file | Build command | Notes |
   |---|---|---|
   | `package.json` | `npm run build 2>&1` | Uses the `build` script. If `build` script missing, fall back to `npx tsc --noEmit 2>&1` if `typescript` in devDependencies; else skip (log WARN). |
   | `Cargo.toml` | `cargo check 2>&1` | Preferred over `cargo build` — faster, same correctness signal. |
   | `go.mod` | `go build ./... 2>&1` | |
   | `pyproject.toml` | `pip install -e . 2>&1 && python3 -c "import sys; sys.exit(0)"` | Install + import-check as a lightweight compile gate. |
   | `Makefile` | `make build 2>&1 \|\| make all 2>&1 \|\| make 2>&1` | Tries `build` target first, then `all`, then default. |
   | `pom.xml` | `mvn compile -q 2>&1` | |
   | `build.gradle` | `gradle classes -q 2>&1` | |
   | `requirements.txt` | `python3 -m py_compile $(find . -name '*.py' -not -path '*/\.*') 2>&1` | Pure-Python syntax check as a lightweight alternative. |

   If multiple build files exist, use the first match in this table order.
   If none found: log `[Build Validation] SKIPPED — no supported build system detected`
   and proceed (skip build check).

2. **Run build** — execute the detected command in the workspace root. Cap
   execution at 120 seconds (use `timeout 120` prefix). Capture exit code +
   merged stdout/stderr.

3. **On failure** (exit ≠ 0):
   ```
   [Build Validation] FAILED — <tool> exited <code>
   ```
   Append full output to `aidlc-docs/audit.md` under `[Build Validation] FAILED`.
   **Surface approval gate to user** with options:
   - `Abort review, return to /factory-build` — set `current_stage: CONSTRUCTION`,
     do NOT spawn reviewers.
   - `Proceed with review anyway` — log `[Build Validation] BYPASSED` to audit.

4. **On success** (exit = 0): log `[Build Validation] OK — <tool> <command>` to audit.

5. **Store result** in orchestrator working state as `build_validation:
   {status: "ok"|"failed"|"skipped", tool: "<name>", output: "<first-200-chars>"}`.

---

1. **Active set** — default `[reviewer-code, reviewer-security]`; use all four if `--full` flag set; constrain to `manifest.reviewer_pool[]` if set.
2. **Knowledge queries** (sequential): `mem_search` per reviewer with specific tags; inject top-5.
2.5. **Build reviewer input handoffs** — for each active reviewer:

    a. **Base** `skills_required`: reviewer's own base skill + `using-agent-skills` +
       `codegraph-aware-exploration`.

    b. **Conditional skills** (per [`project-profile.md`](project-profile.md) §65-78):
       - Read `manifest.project_profile`.
       - If `ui: true`, ALL 4 reviewers get `frontend-ui-engineering`, `design-system-composer`,
         and `ui-constraint-validator` added to `skills_required[]`.
       - Resolve matching SKILL.md paths → add to `skill_paths_resolved[]`.

    c. **Framework skills from build** (per Pre-Review Step 0.5 above):
       - `reviewer-code` **only**: append ALL keys from `framework_skill_paths` to
         `skills_required[]` and merge their paths into `skill_paths_resolved[]`.
       - `reviewer-security` **only**: append security-relevant framework skills (name contains
         `security`, `auth`, or `hardening`) from `framework_skill_paths`.
       - Other reviewers: base + conditional only (no framework skills).

    d. **Filter**: include ONLY paths for skills present in `skills_required[]`. Discard
       paths for irrelevant skills. Deduplicate if conditional + framework paths overlap.

    e. **Design system**: if `manifest.project_profile.ui == true` AND `manifest.project_profile.design_system_path`
       is set, inject `design_system_path` into ALL reviewer handoffs so each can run its axis-specific
       design system review checks.
3. **Parallel spawn** — ONE message, all `Task()` calls together. Wait for returns.
4. **Per-reviewer post-processing** (any order): validate → knowledge save → audit append.
5. **Merge**: `factory_merge_reviews.py <run-id> --reviewers <reviewer-names>` → review report.
   `--reviewers` takes the **`reviewer` field values**, not `stage_id` values:
   - `reviewer-code` → `code-quality`
   - `reviewer-security` → `security`
   - `reviewer-performance` → `performance`
   - `reviewer-simplifier` → `simplifier`
   Example: `factory_merge_reviews.py <run-id> --reviewers code-quality security`
6. **Approval gate**: surface report. On user response:
   - Fixes requested → route units back through `/factory-build`. If `manifest.project_profile.ui == true`
     AND `design_system_path` is set, capture the rejection feedback as a design system antipattern:
     ```bash
     python3 aidlc-scripts/factory_design_system_learn.py reject \
         --component <inferred-primitive> \
         --reason "<user feedback or reviewer finding>" \
         --source <primary-ui-file> \
         --run-id <run-id>
     ```
   - Approved → auto-commit `docs(review): complete review report`, update state, offer `/factory-ship`.
