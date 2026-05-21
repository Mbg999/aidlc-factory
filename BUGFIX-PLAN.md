# Bug-Fix Plan

Scope: results from a full-repo audit on 2026-05-13.

Priority legend: `[P0]` crash/data-loss / `[P1]` logic bug / `[P2]` fragility / `[P3]` docs/style.

---

## Status

Started: 2026-05-13 — **33 of 33 items fixed.** ✅

Legend: ✅ fixed, ⏳ pending

---

## P0 — Crash or data-loss bugs

### 1. `factory_run.py:259` — dead code with latent NameError ✅

**File:** `aidlc-scripts/factory_run.py`
**Problem:** Block guarded by `if False` references undefined `run_budget_path()`. Never runs today, but if the guard is removed it crashes.
**Fix:** Removed dead budget-drift block.

### 2. `factory_merge_reviews.py:222` — NoneType crash in sorted() ✅

**File:** `aidlc-scripts/factory_merge_reviews.py`
**Problem:** `f.get("line", 0)` returns `None` when key exists with `None` value → `TypeError` in `sorted()`.
**Fix:** Changed to `f.get("line") or 0`.

### 3. `factory_secretscan.py:124-130` — crash-safety hole in --strip ✅

**File:** `aidlc-scripts/factory_secretscan.py`
**Problem:** `path.rename(backup)` then `path.write_text(stripped)`. Crash between them = file lost at original path.
**Fix:** Write stripped to tmp file, then `tmp.replace(path)`. Also added backup conflict avoidance with timestamp fallback.

### 4. `factory_audit_writes.py:36-47` — audit misses new files ✅

**File:** `aidlc-scripts/factory_audit_writes.py`
**Problem:** `git diff --diff-filter=A` only catches tracked files that were re-created. Untracked new files are invisible to the audit.
**Fix:** Combined `git diff --diff-filter=A` with `git ls-files --others --exclude-standard` for full coverage.

### 5. `factory_conflict.py:184-258` — TOCTOU race on lock acquire ✅

**File:** `aidlc-scripts/factory_conflict.py`
**Problem:** `_list_locks()` + lock-file write is not atomic. Two parallel holders can both pass the conflict check and acquire overlapping locks.
**Fix:** Wrapped `cmd_acquire` body in `_do_acquire` with `fcntl.flock` serialize acquire per-run (falls back gracefully on non-POSIX).

### 6. `reverse-engineer.input.v1.json:12` — opaque `workspace_state` ✅

**File:** `.aidlc-orchestrator/contracts/reverse-engineer.input.v1.json`
**Problem:** `workspace_state` is `{ "type": "object" }` with zero properties — accepts `{}`, masking data loss.
**Fix:** Added properties: `project_type`, `existing_code`, `next_phase`, `tech_stack_summary`, `legacy_patterns`.

### 7. `custom-agent.output.v1.json:12-21` — divergent artifact shape ✅

**File:** `.aidlc-orchestrator/contracts/custom-agent.output.v1.json`
**Problem:** Uses `description` instead of standard `kind` enum + `hash`. No consumer can reliably parse these artifacts.
**Fix:** Aligned with all other output contracts: `{ path, kind, hash? }` with `required: ["path", "kind"]`.

### 8. `code-generator.input.v1.json:31-46` — allOf.then + default conflict ✅

**File:** `.aidlc-orchestrator/contracts/code-generator.input.v1.json`
**Problem:** `allOf > if(fast_path=true) > then` adds `tier` to required, but `tier` has a JSON Schema `default`. Defaults are metadata — not auto-injected. Fast-path payloads without `tier` will fail validation.
**Fix:** Removed `tier` from `then.required` — it has a top-level default.

---

## P1 — Logic bugs

### 9. `factory_model.py:59-66` — stage model fallback order wrong ✅

**File:** `aidlc-scripts/factory_model.py`
**Problem:** If `per_stage[stage]` exists but has no `"model"` key (e.g. `{"tokens": 500}`), `entry` is truthy so `custom-agent` fallback is skipped, returning `DEFAULT_MODEL` instead.
**Fix:** Check `"model" in entry` directly before checking truthiness; now falls through to `custom-agent` when model key absent.

### 10. `factory_validate.py:50` — float accepted as test count ✅

**File:** `aidlc-scripts/factory_validate.py`
**Problem:** `isinstance(tests_added, (int, float))` passes `1.5` as a valid test count.
**Fix:** Changed to `isinstance(tests_added, int)` only.

### 11. `core-workflow.md` vs `orchestrator.md` — audit format conflict ✅

**Files:** `aidlc-rules/aws-aidlc-rules/core-workflow.md`, `.claude/agents/orchestrator.md`
**Problem:** `core-workflow.md` defines `## <ISO8601> ...` audit headers with 30-entry archive policy. `orchestrator.md` uses `## <ts> <PHASE> - <STAGE LABEL>` with timeline.jsonl dedupe. Conflict causes inconsistent log entries when orchestrator is used alongside the non-orchestrator workflow.
**Fix:** Added carve-out in `core-workflow.md` audit section: "Orchestrator override: when `/factory-*` commands are active, the orchestrator's timeline-based format takes precedence."

### 12. `factory_build_cache.py:88` — yaml/json format mismatch ✅

**File:** `aidlc-scripts/factory_build_cache.py`
**Problem:** `cmd_check` uses `yaml.safe_load` exclusively. `cmd_save` writes JSON when pyyaml unavailable. If pyyaml is unavailable at read time, cache check always returns `{}` → false cache miss.
**Fix:** Added `json.loads` fallback in `cmd_check`.

---

## P2 — Fragility / False positives / Brittle code

### 13. `factory_secretscan.py:39` — AWS key pattern too broad ✅

**File:** `aidlc-scripts/factory_secretscan.py`
**Problem:** `[a-zA-Z0-9/+=]{40}` matches git SHAs, UUIDs, random 40-char IDs → extreme false positives.
**Fix:** Replaced bare 40-char regex with context-anchored pattern requiring `aws_secret|secret_access|secret_key` prefix before the value.

### 14. `factory_agent_discover.py:33-42` — manual frontmatter parser ✅

**File:** `aidlc-scripts/factory_agent_discover.py`
**Problem:** Hand-rolled line-split parser breaks on multi-line YAML values, colons in values, YAML lists.
**Fix:** Try `yaml.safe_load()` first; fall back to manual parser only on parse failure.

### 15. `factory_validate.py:53` — fragile `/test` path detection ✅

**File:** `aidlc-scripts/factory_validate.py`
**Problem:** `"/test" in path` matches `/mytestfile.py`, `/attestation/`, etc.
**Fix:** Changed to `"test" in Path(path).parts`.

### 16. `factory_budget.py:104-108` — non-atomic budget write ✅

**File:** `aidlc-scripts/factory_budget.py`
**Problem:** `p.write_text()` without tmp+rename. Crash mid-write corrupts `budget.yaml`.
**Fix:** Write to tmp file, then `tmp.replace(p)`.

### 17. `factory_budget.py:126-134` — fragile reviewer pattern matching ✅

**File:** `aidlc-scripts/factory_budget.py`
**Problem:** Uses `.replace()` chain for reviewer patterns. Adding a new reviewer type requires modifying the chain.
**Fix:** Changed to `stage.startswith("reviewer-")` wildcard.

### 18. `factory_secretscan.py:127-128` — backup overwrite ✅

**File:** `aidlc-scripts/factory_secretscan.py`
**Problem:** `path.with_suffix(".original")` silently overwrites existing backup.
**Fix:** Fixed as part of crash-safety rewrite — now checks for existing backup and falls back to timestamped name.

### 19. `factory_graph.py:82-108` — self-loop detection unclear ✅

**File:** `aidlc-scripts/factory_graph.py`
**Problem:** Self-referencing dependency produces "cycle detected" with no self-loop indication.
**Fix:** Added explicit check: `if u['name'] in unit_deps` raises ValueError with clear self-loop message.

### 20. `factory_complexity.py:115-118` — unrecognized scope/complexity silent fallback ✅

**File:** `aidlc-scripts/factory_complexity.py`
**Problem:** Unknown value silently falls back to `"MEDIUM"` via `.get()` default.
**Fix:** Added warning to stderr when scope or complexity is not in known mappings.

### 21. `factory_triage.py:157` — substring match too broad ✅

**File:** `aidlc-scripts/factory_triage.py`
**Problem:** `kw in lower` matches inside other words (`"race"` → `"racecar"`, `"braces"`).
**Fix:** Changed to `re.search(rf'(?<!\w){re.escape(kw)}(?!\w)', lower)` — word-boundary matching with non-word-character lookahead/behind. All 17 existing tests pass.

### 22. `factory_triage.py:63` — duplicate keyword ✅

**File:** `aidlc-scripts/factory_triage.py`
**Problem:** `"api gateway"` appears twice in `architecture_signal` list.
**Fix:** Removed duplicate.

### 23. `build-test-agent.output.v1.json:22` — missing `"source"` in artifact enum ✅

**File:** `.aidlc-orchestrator/contracts/build-test-agent.output.v1.json`
**Problem:** Enum is `["doc", "test", "config"]`. If agent produces source patches, they can't be recorded.
**Fix:** Added `"source"` to the enum.

### 24. `code-generator.input.v1.json:13` — `unit_spec_path` always optional ✅

**File:** `.aidlc-orchestrator/contracts/code-generator.input.v1.json`
**Problem:** `unit_spec_path` not in top-level `required`. For non-fast-path code-gen, it's almost certainly needed.
**Fix:** Added `description` field clarifying it's required for non-fast-path usage.

### 25. `reviewer.input.v1.json` — `stage_id`/`reviewer` dual identity ✅

**File:** `.aidlc-orchestrator/contracts/reviewer.input.v1.json`
**Problem:** `stage_id` uses `["reviewer-code", ...]` but `reviewer` field uses `["code-quality", ...]`. Non-obvious mapping.
**Fix:** Added `description` field to `reviewer` property documenting the mapping. Also documented in README.md and REFERENCE.md.

### 26. `contracts/README.md` — missing contract entries ✅

**File:** `.aidlc-orchestrator/contracts/README.md`
**Problem:** `custom-agent.input`, `custom-agent.output`, `approval.input` exist on disk but aren't listed.
**Fix:** Added rows for custom-agent (input v1, output v1) and approval (input v1 only) to the table.

---

## P3 — Docs out of sync

### 27. `contracts/REFERENCE.md` — field listings ~80% wrong ✅

**File:** `.aidlc-orchestrator/contracts/REFERENCE.md`
**Problem:** Almost every contract's described fields don't match actual JSON schemas.
**Fix:** Full rewrite matching actual schema files. Every row now reflects real field names from the `.json` files. Added reviewer naming exception documentation.

### 28. `contracts/REFERENCE.md` — missing complexity_tiers ✅

**File:** `.aidlc-orchestrator/contracts/REFERENCE.md`
**Problem:** `budgets/default.yaml` has `complexity_tiers` block but REFERENCE.md doesn't document it.
**Fix:** Added "Complexity tiers" section with table showing SMALL/MEDIUM/LARGE caps, skip stages, and reviewer pools.

### 29. `core-workflow.md:361-372` — commands missing `<run-id>` arg ✅

**File:** `aidlc-rules/aws-aidlc-rules/core-workflow.md`
**Problem:** `/factory-plan`, `-build`, `-review`, `-ship` listed without `<run-id>`.
**Fix:** Added `<run-id>` to each.

### 30. `core-workflow.md:374` — single-platform reference ✅

**File:** `aidlc-rules/aws-aidlc-rules/core-workflow.md`
**Problem:** Only references `.claude/agents/orchestrator.md`, not `.opencode/` equivalent.
**Fix:** Added `.opencode/agents/orchestrator.md` reference alongside `.claude/`.

### 31. `core-workflow.md:64-66` vs `orchestrator.md` — skill search path mismatch ✅

**File:** `aidlc-rules/aws-aidlc-rules/core-workflow.md`
**Problem:** Lists `<repo>/.agents/custom-skills/` as highest-priority; `orchestrator.md` only mentions `.agents/skills/` and `~/.agents/skills/`.
**Fix:** Added orchestrator note in core-workflow.md documenting the discrepancy with suggestion to symlink or update orchestrator.md.

### 32. `factory_run.py:503` — docstring off-by-one ✅

**File:** `aidlc-scripts/factory_run.py` (not factory_conflict.py)
**Problem:** Docstring says "truncate before target stage" but code truncates from target onward.
**Fix:** Added comment noting "truncate from target stage onward (inclusive)".

### 33. `factory_conflict.py:363-364` — `_strip_leading_colon(":")` returns `""` ✅

**File:** `aidlc-scripts/factory_conflict.py`
**Problem:** Edge case where stripping colon from a single colon returns empty string instead of `":"`.
**Fix:** `if len(s) <= 1: return s`.
