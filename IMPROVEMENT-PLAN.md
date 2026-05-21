# AIDLC Orchestrator — Comprehensive Improvement Plan

> Analysis date: 2026-05-12
> Scope: Full repo audit of the AIDLC multi-agent software factory at
> `/Users/miguel.belmonte/Desktop/custom aidlc/` (fork of `awslabs/aidlc-workflows`).

---

## 1. Platform & Reliability (the biggest risks)

### 1.1 Zero unit tests for orchestrator scripts

**Files:** `aidlc-scripts/factory_{triage,budget,run,conflict,merge_reviews}.py`
— ~1,800 lines, 5 scripts, **0 tests**.

**Risk:** Every bug fixed so far was found by manual inspection or ad-hoc smoke
testing. There is no regression safety net. A single `sys.exit()` change in a
shared function can silently break all callers.

**Fix:**
- Add `tests/test_factory_triage.py` — 10 parametrized cases (the 5 ACs + 5 edge
  cases like empty string, non-ASCII, very long request)
- Add `tests/test_factory_budget.py` — init/check/deduct/status cycle with
  tempdir fixtures
- Add `tests/test_factory_run.py` — init + complete-stage + resume cycle with
  tempdir; test `_next_stage()` with synthetic markers
- Add `tests/test_factory_conflict.py` — lock acquire/release/overlap detection
  with tempdir
- Add `tests/conftest.py` — shared fixtures (temp run dir, minimal budget)
- Wire into CI: `pytest tests/` in `.github/workflows/ci.yml`

**Effort:** ~3 hours for comprehensive test suite.
**ROI:** Prevents every class of bug found in Phase 2-6 review.

### 1.2 Crash resilience gaps

**Observation:** `complete-stage` writes manifest atomically but timeline event
and budget deduction are separate I/O calls. A crash between them leaves
inconsistent state.

| I/O call | Atomic? | After crash |
|----------|---------|-------------|
| `load_manifest()` → modify → `save_manifest_atomic()` | ✅ POSIX rename | File is consistent |
| `append_event()` (timeline.jsonl) | ❌ Not atomic with manifest | Event may be missing |
| `load_run_budget()` → modify → `save_run_budget()` | ❌ Not atomic with manifest | Budget may be wrong |

**Fix:**
- Add a `--reason` field to `complete-stage` that gets written into the manifest
  as a last-known-action marker
- On resume, check for budget/timeline/manifest drift and reconcile:
  ```python
  def reconcile(run_id):
      manifest_stages = set(manifest.completed_stages)
      timeline_stages = {e.stage for e in timeline if e.evt == 'stage_complete'}
      missing = manifest_stages - timeline_stages
      if missing:
          # Re-emit timeline events for completed-but-not-logged stages
  ```

### 1.3 Lock TTLs and stale cleanup

**Observation:** `factory_conflict.py acquire` sets no TTL. If `release` isn't
called (agent crash, network split), locks are held forever.

**Fix:**
- Add `--ttl-minutes` to `acquire` (default 60):
  ```yaml
  # lock file format
  holder: code-generator:auth-service
  acquired_at: 2026-05-12T10:00:00Z
  ttl_minutes: 60
  globs: [src/auth/**]
  ```
- Add `--stale` to `release` subcommand: `factory_conflict.py release <run-id> --stale --older-than 120`
- On `acquire`, skip stale locks (treat as auto-released)

### 1.4 No build caching for unchanged units

**Observation:** If a unit's source tree hasn't changed from a prior run,
re-running build-test-agent is wasteful. The orchestrator has no content-addressable
cache.

**Fix (Phase 7+):** Compute `git tree-object hash` of each unit's files before
spawning build-test-agent. If the hash matches a prior run's success, skip and
reuse the prior result.

---

## 2. Cross-Tool & Distribution (reach)

### 2.1 Install only targets Claude Code

**Observation:** `install_aidlc.py` copies to `.claude/` only. But:
- OpenCode uses `.opencode/`
- Codex CLI uses `.codex/`
- Cursor uses `.cursor/rules/`
- Windsurf uses `.windsurf/`

Each tool has different agent file format and command location.

| Tool | Agent dir | Command dir | Skill dir |
|------|-----------|-------------|-----------|
| Claude Code | `.claude/agents/` | `.claude/commands/` | `.agents/` |
| OpenCode | `.opencode/agents/` | `.opencode/commands/` | `.agents/` |
| Codex CLI | `.codex/agents/` | `.codex/commands/` | `.agents/` |
| Cursor | `.cursor/rules/` | N/A (inline) | `.agents/` |
| Cline | `.cline/rules/` | N/A (inline) | `.agents/` |

**Fix:**
- Add `--tool` flag to `install_aidlc.py` with choices for all 5 tools
- Each tool has its own adapter file and target directory
- Orchestrator agent files are tool-agnostic (plain markdown); only the
  installation path differs

### 2.2 No version-locking between scripts and schemas

**Observation:** Scripts and schemas are in the same repo but there's no
enforcement that `factory_run.py v2` is used with `manifest.yaml v2`.
If a user updates scripts but not schemas (or vice versa), silent
incompatibility.

**Fix:**
- Add a `VERSION` file (like `aidlc-rules/VERSION`):
  ```json
  {"orchestrator_version": "0.2.0", "schema_version": 1}
  ```
- `factory_validate.py` checks `$id` in the schema against the expected version
- `factory_run.py init` writes `orchestrator_version` into manifest.yaml
- On `resume`, if version < min_compatible, warn and refuse

---

## 3. Monitoring & Observability (understand what's happening)

### 3.1 No run visualization

**Observation:** `timeline.jsonl` is the only run record. It's machine-readable
but human-hostile. Debugging a failed run requires reading through JSON lines.

**Fix:** Add `factory_run.py graph <run-id>`:
```bash
$ python3 aidlc-scripts/factory_run.py graph 2026-05-11-healthz-endpoint

Timeline: 2026-05-11-healthz-endpoint
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  workspace-scout      ■■■■■■■■■□□□  3.0m  ✅
  requirements-analyst ■■■■■■■■■■□□  8.1m  ✅
  workflow-planner     ■■■■■□□□□□□□  3.6m  ✅
  unit-decomposer      □□□□□□□□□□□□  0.1m  ⚠️ SKIPPED
  code-generator       ■■■■■■■■■■■■  45.4m ✅ (3 units)
  build-test-agent     ■■■■■■■■■■□□  30.3m ✅ (3 units)
  reviewer-*           ■■■■■□□□□□□□  4.0m  ✅ (4 parallel)
  ship-agent           ■■■□□□□□□□□□  2.0m  ✅
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Budget: 1.16M / 5M tokens (23%)  100.5 / 240 min (42%)
```

### 3.2 No budget trend tracking

**Observation:** Each run tracks budget in `budget.yaml` but there's no
cross-run analysis. "How many tokens did requirements-analysis use on average
over the last 10 runs?" is unanswerable without manual grep.

**Fix:**
- `factory_budget.py trends <run-id-prefix>`:
  ```bash
  $ python3 aidlc-scripts/factory_budget.py trends 2026-05
  Stage                  Avg tokens   Avg wall   Runs
  workspace-scout        48,200       2.8m       12
  requirements-analyst   265,000      8.0m       12
  code-generator         310,000      44.1m      12
  ```
- Store summary in `.aidlc-orchestrator/stats/per-stage.yaml`

### 3.3 Approval gate latency not tracked

**Observation:** User approval gates (stages returning `needs_human`) are the
biggest wall-clock consumers, but there's no tracking of "how long did the user
take to approve?" Data lives only in audit.md free-text.

**Fix:**
- Track in timeline.jsonl: `user_answers_received` and `user_decision` events
  already exist — just measure the delta between `spawn_end` of the needs_human
  stage and the `user_decision` event
- `factory_run.py status --latency` prints approval gate bottlenecks

---

## 4. Developer Experience (make it pleasant to use)

### 4.1 No dry-run mode

**Observation:** There's no way to see "what would this run do" without
spawning agents and spending tokens.

**Fix:** Add `--dry-run` to `/factory-spec`:
```bash
/factory-spec --dry-run "add healthz endpoint"
# Output:
#   Triage: TINY (score 0) → FAST_PATH
#   1 spawn code-generator, ~50K tokens, ~8 min
#
# /factory-spec --dry-run "refactor auth module"
#   Triage: SMALL (score 2) → FULL pipeline
#   7 stages, ~800K tokens, ~40 min
#   workspace-scout → requirements-analyst → workflow-planner
#   → code-generator → build-test-agent → review → ship
```

### 4.2 Structured approval UX

**Observation:** When a stage returns `needs_human`, the orchestrator presents
free-form text. User has to read everything and type a response.

**Fix:** Standardize approval prompts with structured options:
```
⏸️  Code Generation — Plan Approval

Unit: server-scaffold (3 tasks)
  T1: package.json     [✓ covers AC-1.5, AC-NFR-3.2]
  T2: npm install      [✓ covers AC-NFR-3.3]
  T3: index.js shell   [✓ covers AC-1.6, AC-NFR-4.1]

[Approve] [Request Changes] [Cancel Layer]
```

### 4.3 No inline help for slash commands

**Observation:** Typing `/factory-plan --help` in Claude Code doesn't work —
slash commands don't support `--help`. Users must read the command files.

**Fix:** Add a `factory-help.md` command:
```
/factory-help          → list all commands
/factory-help spec     → describe /factory-spec stages + example
/factory-help plan     → describe /factory-plan flow
```

---

## 5. Meta & Dogfooding (improve the factory with the factory)

### 5.1 Factory doesn't self-host

**Observation:** The most powerful improvement: run the AIDLC orchestrator on
itself. Add a new agent or modify a script using `/factory-spec`.

**Fix:** Create a `/factory-self <task>` command:
- `/factory-self "add --stale flag to factory_conflict.py release"` runs the
  full pipeline but targets `aidlc-scripts/` as the workspace
- Validates that the orchestrator's own dev process matches what it demands
- Serves as the ultimate integration test

### 5.2 No performance baseline

**Observation:** There's no benchmark measuring how long each stage takes, how
many tokens it consumes, or how the orchestrator's overhead compares to a
single-agent AIDLC run.

**Fix:** Add `aidlc-scripts/benchmark_orchestrator.py`:
- Runs a synthetic request through both single-agent and multi-agent paths
- Compares: tokens used, wall time, approval gates, files produced
- Outputs a comparison table

---

## 6. Security & Hardening

### 6.1 No handoff content validation beyond schema

**Observation:** JSON Schema validates structure (required fields, types) but
not content. An agent could return `status: complete` with an empty artifacts
list and pass schema validation.

**Fix:** Add `factory_validate.py --strict` mode that checks:
- `status: complete` requires at least 1 artifact with a non-empty `path`
- `tests_added > 0` requires at least 1 test file in `artifacts`
- `emitted_knowledge[].body` must be non-empty and markdown-formatted

### 6.2 No file-write guardrails for agents

**Observation:** Agents can write anywhere in the repo. Only `locks_required[]`
limits scope, and that's honor-system (the agent reads it in its input prompt).

**Fix:** Post-spawn file-write audit:
- `git diff --name-only --diff-filter=A` after each code-generator spawn
- Cross-reference against `locks_required[]` globs
- Flag files outside declared locks as `audit_entries[]` warnings
- For strict mode: mark the stage `blocked` if locks were violated

### 6.3 Secret scanning on handoff artifacts

**Observation:** `emitted_knowledge[].body` is free-form markdown. An agent
could accidentally include an API key or credential in a knowledge emission.

**Fix:**
- Add gitleaks scan to post-processing step for every stage output
- If a secret is detected: strip it, log warning, set `needs_human`

---

## 7. Documentation

### 7.1 No troubleshooting guide

**Observation:** When a run fails, there's no structured guide for what to check
first. Users with failing runs have to read the code.

**Fix:** Create `docs/TROUBLESHOOTING.md`:
| Symptom | Likely cause | Check first |
|---------|-------------|-------------|
| `factory_run.py resume` returns wrong stage | `current_stage` is a synthetic marker | `manifest.yaml:6` |
| Budget shows negative remaining | `deduct` called with negative params | Check bug 2 fix status |
| Parallel reviewers complete but merge fails | One reviewer output is malformed | `factory_merge_reviews.py --reviewers ...` |
| `/factory-build` fails on lock acquire | Stale lock from crashed agent | `factory_conflict.py list <run-id>` |

### 7.2 Schema reference for each contract

**Observation:** Contract schemas exist but there's no human-readable reference
for what each field means. Developers extending the system must read raw JSON
Schema.

**Fix:** Add a `contracts/REFERENCE.md` with:
- Per-contract table (fields, types, description, examples)
- Cross-reference: which agent produces this output, which consumes it as input
- Version history per contract

---

## 8. Infrastructure

### 8.1 No CI/CD for orchestrator itself

**Observation:** GitHub Actions exist for the AIDLC rules (lint, CodeQL, release)
but not for the orchestrator scripts.

**Fix:** Add to `.github/workflows/ci.yml`:
```yaml
- name: Test orchestrator scripts
  run: |
    pip install pyyaml jsonschema pytest
    pytest tests/ --tb=short
- name: Smoke test triage
  run: python3 aidlc-scripts/factory_triage.py "add healthz" | grep TINY
- name: Smoke test validate
  run: python3 aidlc-scripts/factory_validate.py \
    .aidlc-orchestrator/contracts/code-generator.input.v1.json \
    .aidlc-orchestrator/contracts/code-generator.input.v1.json
```

### 8.2 No release process for orchestrator

**Observation:** The AIDLC rules have a release process (CHANGELOG, version tags,
release PRs via `.github/workflows/release-pr.yml`) but the orchestrator scripts
have no version tracking.

**Fix:**
- Add `aidlc-scripts/VERSION` with semver
- Release orchestrator alongside AIDLC rules
- `install_aidlc.py` checks version compatibility before installing

---

## Priority Matrix

| # | Improvement | Impact | Effort | Quick win? |
|---|-------------|--------|--------|------------|
| 1.1 | Unit tests for scripts | 🔴 Critical | 3h | ✅ |
| 4.1 | `--dry-run` mode | 🟡 Medium | 30m | ✅ |
| 3.1 | Run visualization (`graph` command) | 🟡 Medium | 1h | ✅ |
| 4.3 | `factory-help` command | 🟢 Low | 15m | ✅ |
| 1.3 | Lock TTLs + stale cleanup | 🔴 Critical | 30m | ✅ |
| 3.2 | Budget trend tracking | 🟢 Low | 1h | |
| 6.1 | Strict validation mode | 🟡 Medium | 2h | |
| 4.2 | Structured approval UX | 🟡 Medium | 2h | |
| 1.2 | Crash resilience (reconcile) | 🔴 Critical | 2h | |
| 2.1 | Multi-tool install | 🟡 Medium | 3h | |
| 2.2 | Version locking | 🟡 Medium | 1h | |
| 5.1 | Self-hosting (`/factory-self`) | 🟡 Medium | 4h | |
| 7.1 | Troubleshooting guide | 🟢 Low | 1h | |
| 7.2 | Schema reference | 🟢 Low | 2h | |
| 8.1 | CI/CD for scripts | 🟡 Medium | 1h | ✅ |
| 6.2 | File-write audit | 🟢 Low | 1h | |
| 6.3 | Secret scanning | 🟢 Low | 1h | |
| 3.3 | Approval latency tracking | 🟢 Low | 30m | ✅ |
| 1.4 | Build caching (Phase 7+) | 🟢 Low | 4h | |
| 8.2 | Release process | 🟢 Low | 1h | |

**Quick wins (≤1h each):**
1. `--dry-run` mode → 30m
2. `factory-run graph` command → 1h
3. Lock TTLs → 30m
4. `factory-help` command → 15m
5. Approval latency tracking → 30m
6. CI/CD test step → 1h

**High-effort, high-impact:**
1. Unit tests (3h) — prevents regression on all future changes
2. Multi-tool install (3h) — unlocks OpenCode/Codex/Cursor users
3. Self-hosting (4h) — validates the entire premise

---

## Implementation Sequence

```
Phase 1 (this week): 1.1, 1.3, 4.1, 3.1, 8.1
  → safety net + visibility + 1h quick wins

Phase 2 (next week): 1.2, 4.3, 3.3, 6.1, 7.1
  → resilience + structured UX + docs

Phase 3 (next sprint): 2.1, 2.2, 4.2, 5.1
  → reach + self-hosting

Phase 4 (backlog): 3.2, 6.2, 6.3, 7.2, 8.2, 1.4
  → polish + advanced features
```
