# Fast Path — Bypass Multi-Agent for Trivial Tasks

## Goal
Add a pre-pipeline triage step that, for genuinely trivial requests (a single
endpoint, a util function, a typo fix), bypasses the full orchestrator and
runs **a single direct `code-generator` Task() call** — no manifest, no
timeline, no audit blocks, no lock registry, no reviewer pool, no ship stage.

This is the mature answer to the question the existing tier system never asks:
**"does this even deserve multi-agent?"**

## The principle
> Governance overhead must scale sublinearly with task complexity.

Current SMALL tier still runs 7 stages with full manifest/timeline/audit
infrastructure. For a healthz endpoint that's still absurd overhead. FAST_PATH
makes the floor genuinely flat: 3 stages, no replay infrastructure, one commit.

## Non-Goals
- Not replacing SMALL/MEDIUM/LARGE — those handle real work. FAST_PATH is a
  new tier *below* SMALL.
- Not removing user approval — there is still one gate (review the diff).
- Not silent execution — every FAST_PATH run appends one line to
  `aidlc-docs/fast-path-log.md` so the operation is traceable, just not
  replayable.
- Not auto-deciding ambiguous cases — when triage is uncertain, fall through
  to SMALL. Conservative by default.

## Pipeline Comparison

| Tier   | Stages | Manifest | Timeline | Audit blocks | Locks | Reviewers | Ship |
|--------|--------|----------|----------|--------------|-------|-----------|------|
| TINY   | **3**  | no       | no       | 1 line       | no    | 0         | no   |
| SMALL  | 7      | yes      | yes      | full         | yes   | 1         | yes  |
| MEDIUM | 8      | yes      | yes      | full         | yes   | 3         | yes  |
| LARGE  | 9      | yes      | yes      | full         | yes   | 4         | yes  |

TINY's 3 stages:
1. **Triage** (`factory_triage.py` — deterministic, no LLM)
2. **Generate** (single `code-generator` Task() call with a stripped-down input)
3. **Confirm** (user reviews diff; orchestrator commits on approval)

## Triage Scoring (`factory_triage.py`)

Pure Python, no LLM. Reads the user request text + repo state, returns a score
and a tier recommendation.

```
factory_triage.py "<user request>" [--repo .] [--explain]
```

Output (stdout JSON):
```json
{
  "score": 1,
  "tier": "TINY",
  "factors": {
    "file_count_signal": 0,
    "architecture_signal": 0,
    "concurrency_signal": 0,
    "external_api_signal": 0,
    "security_signal": 1,
    "infrastructure_signal": 0,
    "domain_logic_signal": 0,
    "scope_breadth_signal": 0
  },
  "explanation": "Single endpoint, no concurrency/infra/external deps; only security touch is auth keyword.",
  "recommended_pipeline": "fast"
}
```

Scoring rules (each factor 0/1/2):

| Factor | +0 | +1 | +2 |
|--------|----|----|----|
| `file_count_signal` | 1 file mentioned | 2-5 files | 6+ files / "across the codebase" |
| `architecture_signal` | none | one of: microservice, service, module | multiple + "system" / "architecture" |
| `concurrency_signal` | none | one of: async, queue, worker, stream | multiple + "race", "lock", "distributed" |
| `external_api_signal` | none | one external (Stripe, S3, GitHub API) | multi-vendor integration |
| `security_signal` | none | one of: auth, JWT, encryption | OAuth flow, RBAC, key rotation |
| `infrastructure_signal` | none | Dockerfile, k8s, Terraform mentioned | full CI/CD pipeline, infra-as-code |
| `domain_logic_signal` | CRUD only | business rules mentioned | "pricing engine", "fraud detection", state machines |
| `scope_breadth_signal` | single function/endpoint | one module | "refactor X across all services", "migrate" |

Tier mapping:
| Total score | Tier |
|-------------|------|
| 0-2 | **TINY** → FAST_PATH |
| 3-5 | SMALL (existing path) |
| 6-8 | MEDIUM (existing path) |
| 9+  | LARGE (existing path) |

**Conservative defaults**: when keyword detection is ambiguous, factor scores
round UP. Misclassifying a SMALL task as TINY is worse than the inverse —
loses governance on something that needed it. Misclassifying TINY as SMALL
just costs ~30 minutes of unnecessary stages.

## FAST_PATH Execution

When `factory_triage.py` returns `tier: TINY`, the orchestrator runs this
abbreviated flow inside `/factory-spec`:

```
1. Triage (just ran)
2. Build a minimal code-generator input — no contract validation:
   {
     "user_request": "<verbatim>",
     "tier": "TINY",
     "fast_path": true,
     "repo_root": ".",
     "constraints": ["produce minimum viable code", "TDD required", "no architectural decisions"]
   }
3. Single Task(subagent_type="code-generator") call with that input.
4. code-generator runs Red → Green → Refactor → Commit (as today) but emits a
   stripped output: just the diff summary, files changed, test count.
5. Orchestrator presents the diff to the user. One approval prompt.
6. On approve: append one line to aidlc-docs/fast-path-log.md:
     <ts> TINY score=<n> | <request first 80 chars> | <files changed> | commit=<sha>
   Done. Run terminates.
7. On reject: orchestrator escalates — re-runs as SMALL tier with full
   pipeline. User gets one chance to opt up.
```

No `manifest.yaml` is written. No `timeline.jsonl`. No `audit.md` block. The
git commit is the audit trail.

## What gets sacrificed (explicit)

For FAST_PATH runs only:
- No replay capability (cannot `/factory-replay` a TINY run)
- No knowledge emission to engram (saves are skipped)
- No reviewer pool (no security/performance/simplifier review)
- No ADRs (skip-ship)
- No build-test-agent stage (code-generator runs tests inline as part of TDD)
- No conflict-resolver locks (single-spawn, nothing to conflict with)
- No budget gate (no orchestrator tracking; code-generator self-monitors)

This is deliberate. The whole point is that for `add a healthz endpoint`, none
of these provide value greater than their overhead.

## Bailout / Escalation

Three bailout paths:

1. **User-initiated**: `/factory-spec --tier=small <request>` forces the
   existing SMALL path, ignoring triage.
2. **Triage-uncertain**: any factor scoring 2 → triage rounds the total UP
   one bracket. A "TINY-looking" request with one strong signal becomes SMALL.
3. **Post-generation rejection**: if user rejects the FAST_PATH diff, the
   orchestrator restarts the same request as SMALL (one-time auto-upgrade).
   Audit a single line: `<ts> ESCALATED TINY→SMALL | <reason>`.

## Files to Create / Modify

| File | Action | Purpose |
|------|--------|---------|
| `scripts/factory_triage.py` | **NEW** | Pre-pipeline complexity scorer |
| `.claude/agents/orchestrator.md` | MODIFY | Add Step 0 (Triage) before workspace-scout |
| `aidlc-docs/fast-path-log.md` | NEW (auto-created on first TINY run) | Single-line audit |
| `.aidlc-orchestrator/contracts/code-generator.input.v1.json` | MODIFY | Add optional `fast_path: bool` field |
| `.claude/agents/stage/code-generator.md` | MODIFY | Document fast_path mode (no plan gate, just generate) |

No new schemas needed (FAST_PATH deliberately skips contract validation past
the code-generator input).

## Implementation Tasks

### T1 — `factory_triage.py` with keyword-based scoring
- Pure Python, regex/keyword-based, no LLM
- Returns JSON with score + factor breakdown
- Repo-aware: reads file count from request if quoted ("create 2 files"), else
  defaults to 1
- Conservative rounding rule baked in
- Unit-testable: 5+ ACs spanning "add healthz" (TINY), "refactor auth" (SMALL),
  "build payment microservice" (MEDIUM)

### T2 — Orchestrator Step 0: Triage Gate
- Runs at `/factory-spec` entry, before workspace-scout
- If `tier == TINY`: branch into FAST_PATH (no manifest init, no run-id created
  beyond a `tiny-<timestamp>` slug)
- If `tier != TINY`: existing path; pass triage result to requirements-analyst
  as a prior so it doesn't re-derive what we already know

### T3 — FAST_PATH execution in orchestrator
- Build the minimal code-generator input (no full contract — just user_request
  + fast_path: true + repo_root)
- Single Task() call
- Present diff to user
- One approval prompt
- Single-line audit append on success
- Escalation-to-SMALL on rejection

### T4 — code-generator `fast_path: true` mode
- Skip Sub-stage 1 (no plan file written, no plan gate)
- Skip Sub-stage 3 (no approval re-spawn — orchestrator handles approval inline)
- Still run TDD Red → Green → Refactor → Commit
- Emit stripped output: just files_changed, tests_added, commit_sha
- No `emitted_knowledge[]` (saves are skipped)

### T5 — Documentation + escalation logic
- README addition explaining when to use `--tier=small` override
- `aidlc-docs/fast-path-log.md` template (header only, lines appended at runtime)
- One-line `ESCALATED TINY→SMALL` audit on auto-upgrade

## Expected Impact

For the canonical "add 2 endpoints + a util" case (the pruebaaidlcv2 baseline):

| Path | Stages | Approval gates | Manifest writes | Wall time (est.) |
|------|--------|----------------|-----------------|------------------|
| Pre-fix (no tiers) | 9 | 6 | ~30 | ~120 min |
| SMALL tier (shipped) | 7 | 2 | ~20 | ~40 min |
| **TINY / FAST_PATH** | **3** | **1** | **0** | **~8 min** |

The 8 minutes is dominated by the actual code-generation + TDD cycle. The
remaining overhead is one keyword scan (sub-second) and one approval prompt.

## Risks & Mitigations

| Risk | Mitigation |
|------|-----------|
| Triage misclassifies a SMALL task as TINY → missing governance | Conservative rounding + post-generation rejection auto-escalates to SMALL |
| Keyword-based scoring is brittle (synonyms, code-mixed input) | Score factors round UP on ambiguity; user can override with `--tier=small` |
| No replay capability bites later when a TINY produces a regression | Git commit IS the audit trail; git log + `fast-path-log.md` is enough for traceback |
| Code-generator without plan gate produces wrong code | TDD enforced; failing tests halt the run; user reviews the final diff |
| Users disable governance by always passing `--tier=tiny` | Override is `--tier=small/medium/large` only (no downward override); upward escalation requires explicit user opt-in |
| Triage runs but factor logic has a bug → all tasks classified as TINY | Phase-in plan: run triage in shadow mode for 1 week, log decisions, ship only after manual review confirms accuracy |

## Phase-in Plan

1. **Shadow mode** (week 1): `factory_triage.py` exists and runs at
   `/factory-spec` entry, but its output is *logged only* — orchestrator
   ignores the recommendation and runs the existing pipeline. Each run
   compares "what triage said" vs "what the existing tier system said." Review
   logs after 10 runs.
2. **Live mode, opt-in** (week 2): users pass `--allow-tiny` to enable
   FAST_PATH; otherwise existing SMALL/MEDIUM/LARGE path runs.
3. **Live mode, default** (week 3+): TINY classification activates FAST_PATH
   automatically. `--tier=small` available as opt-out.

## Out of Scope (Future Phases)
- LLM-based triage refinement (current is keyword-only; good enough to start)
- Multi-language triage (current is English-only; non-English requests round
  up to SMALL automatically)
- TINY→MEDIUM/LARGE direct escalation (current escalation is one-step:
  TINY→SMALL only; further escalation requires the user to re-issue)
- Per-repo triage tuning (factor weights are global; could be project-scoped
  later via `.aidlc-orchestrator/triage-config.yaml`)
