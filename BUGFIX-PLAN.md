# AIDLC Orchestrator — Bug Fix Plan

> **Scope:** Fix all bugs found during Phase 2–6 live integration review
> (2026-05-12 audit of `pruebaaidlcv2` full workflow run).
>
> Fixes target the **canonical scripts** at `<repo-root>/aidlc-scripts/` and
> propagate to consumer projects via `install_aidlc.py`.

---

## Priority Legend

| Tag | Meaning |
|-----|---------|
| 🔴 | Confirmed — causes incorrect behavior, data loss, or security issue |
| 🟡 | Confirmed — causes subtle incorrectness or reliability concern |
| 🟢 | Valid concern — but no active exploit path in current architecture; defensive improvement |
| 🔵 | Intentional design — documented but not enforced; could be enhanced |

---

## 🔴 Bug 1: `_next_stage()` returns garbage stage names

**File:** `aidlc-scripts/factory_run.py:276-277`
**Severity:** 🔴 HIGH — **CONFIRMED**

**Observation:** `_next_stage()` returns `current_stage` verbatim if it isn't in
`completed_stages[]` or `skipped_stages[]`, **without** validating it's a real
stage in `PHASE_ORDER`. The existing manifest has `current_stage: review-complete`
(a synthetic orchestrator marker set during the live run). Resume suggests
spawning stage `review-complete` — which doesn't exist.

**Verified:** `python3 aidlc-scripts/factory_run.py resume 2026-05-11-healthz-endpoint`
returns `"next_stage_suggestion": "review-complete"`.

**Fix:**

```python
# Before (line 276-277):
if current and current not in completed and current not in skipped:
    return current

# After:
if current and current not in completed and current not in skipped:
    if current in PHASE_ORDER:
        return current
    # synthetic marker (e.g. "review-complete") — fall through to scan
```

**Test:** Resume on the existing run should return `ship-agent` instead of
`review-complete`.

---

## 🔴 Bug 2: No non-negative constraint on `deduct` params

**File:** `aidlc-scripts/factory_budget.py:185,228-230`
**Severity:** 🔴 HIGH — **CONFIRMED**

**Observation:** `--tokens-in -999999` passes argparse and silently inflates
remaining budget.

**Verified:**
```
$ factory_budget.py deduct 2026-05-11-healthz-endpoint bugtest \
    --tokens-in -999999 --tokens-out 0 --wall-min -99.9
deducted -999,999 tokens, -99.9m for bugtest; remaining tokens: 5,835,303

$ factory_budget.py status
used:
  tokens: -835303       # negative — budget infinite
  wall_clock_min: -99.3 # negative — bypasses any future wall-clock checks
```

**Fix:** Use argparse `type` with validation:

```python
def non_negative_int(v: str) -> int:
    n = int(v)
    if n < 0:
        raise argparse.ArgumentTypeError(f"must be >= 0, got {n}")
    return n

def non_negative_float(v: str) -> float:
    n = float(v)
    if n < 0:
        raise argparse.ArgumentTypeError(f"must be >= 0, got {n}")
    return n

p_deduct.add_argument("--tokens-in", type=non_negative_int, default=0)
p_deduct.add_argument("--tokens-out", type=non_negative_int, default=0)
p_deduct.add_argument("--wall-min", type=non_negative_float, default=0.0)
```

**Test:** `factory_budget.py deduct <run> test --tokens-in -1` should fail with
`ArgumentTypeError`, not corrupt the budget.

---

## 🔴 Bug 3: `adopt-legacy` maps `[x] Review` to only 1 of 4 reviewers

**File:** `aidlc-scripts/factory_run.py:384`
**Severity:** 🔴 HIGH — **CONFIRMED**

**Observation:** `LEGACY_TO_PHASE` maps `"review" → "reviewer-code"`. Legacy
AIDLC had a single monolithic Review stage. On adoption, only `reviewer-code`
enters `completed_stages[]`; the other 3 reviewers are silently dropped (not in
completed_stages, not in skipped_stages).

**Verified:**
```json
"adopted_stages": ["workspace-scout", ..., "reviewer-code", "ship-agent"]
// reviewer-security, reviewer-performance, reviewer-simplifier: MISSING
```

The missing reviewers are NOT suggested by resume either (current_stage is
`ship-agent` which is past them in PHASE_ORDER), so 3 stages are just lost.

**Fix:**

```python
# In cmd_adopt_legacy(), after _stages_from_legacy() call:
REVIEWERS = {"reviewer-security", "reviewer-performance", "reviewer-simplifier"}
if "reviewer-code" in completed:
    for r in REVIEWERS:
        if r not in completed and r not in skipped:
            skipped.append(r)
```

**Test:** Adopt a state file with `[x] Review — <date>`. Verify all 4 reviewer
stages are accounted for (1 completed + 3 skipped).

---

## 🔴 Bug 4: Path traversal via unsanitized `run_id` / `holder`

**File:** `aidlc-scripts/factory_run.py:105`, `aidlc-scripts/factory_conflict.py:102`
**Severity:** 🔴 HIGH — **CONFIRMED**

**Observation:** `run_id` is used directly in `Path()` construction without
sanitization. `run_dir(run_id, must_exist=False)` + `mkdir` can create
directories outside the runs directory.

**Verified:**
```
RUNS_ROOT / "../../../tmp/evil" → /Users/miguel.belmonte/Desktop/custom aidlc/tmp/evil
```

Note: The orchestrator generates `run_id` automatically (not from user input),
so this is a defense-in-depth fix, but exploitable if any user-controlled
value ever feeds into a command argument.

**Fix:** Add validation function shared by both scripts:

```python
import re
_RUN_ID_RE = re.compile(r"^[a-zA-Z0-9_.-]+$")
_HOLDER_RE = re.compile(r"^[a-zA-Z0-9_.:-]+$")

def validate_run_id(run_id: str) -> None:
    if not _RUN_ID_RE.match(run_id):
        raise ValueError(f"invalid run_id: {run_id!r}")

def validate_holder(holder: str) -> None:
    if not _HOLDER_RE.match(holder):
        raise ValueError(f"invalid holder: {holder!r}")
```

Call at the top of every subcommand handler. Share via `aidlc-scripts/_common.py` or
inline in both files.

**Test:** `factory_run.py init "../../../etc/passwd" --user-request "x"` should
reject with an error.

---

## 🟡 Bug 5: Budget `check` ignores wall clock budget

**File:** `aidlc-scripts/factory_budget.py:126-177`
**Severity:** 🟡 MEDIUM — **DESIGN GAP**

**Assessment:** The budget yaml defines `wall_clock_max_min: 240` and `deduct`
tracks `used.wall_clock_min`, but `check` only enforces token budget. This may
be intentional (wall clock = advisory soft limit, tokens = hard cost constraint),
but the inconsistency is confusing — either enforce it or don't track it.

**Fix:** Add wall-clock check to `cmd_check()`:

```python
# In cmd_check(), after token check:
remaining_wall = float(state["budget"]["wall_clock_max_min"]) - float(state["used"]["wall_clock_min"])
if remaining_wall <= 0:
    decision_obj["remaining_wall_min"] = round(remaining_wall, 1)
    decision_obj["decision"] = "skip" if args.stage in OPTIONAL_STAGES else "halt"
    decision_obj["reason"] = "wall_clock_exhausted"
    print(json.dumps(decision_obj))
    if args.stage in OPTIONAL_STAGES:
        sys.exit(2)
    sys.exit(3)
```

**Test:** Set `used.wall_clock_min: 241` in a run's budget.yaml, then `check`
should exit 3 (halt).

---

## 🟡 Bug 6: `adopt-legacy` picks up prior-iteration `[x]` markers

**File:** `aidlc-scripts/factory_run.py:429-454`
**Severity:** 🟡 MEDIUM — **CONFIRMED**

**Observation:** `_stages_from_legacy()` scans ALL `[x]` lines in state file
without distinguishing "Prior Iterations" from "Current Iteration". Prior
iteration stages leak into adopted completed_stages.

**Verified:** State file line 40 `[x] Units Generation — 2026-05-08` (prior
iteration) was adopted as `unit-decomposer` in completed_stages, even though
the current iteration has `[-] Unit Decomposer SKIPPED` (line 48).

**Fix:**

```python
def _stages_from_legacy(state_text: str) -> tuple[list[str], list[str]]:
    completed: list[str] = []
    skipped: list[str] = []
    # Only scan lines under "### Current Iteration"
    current_section = state_text.split("### Current Iteration", 1)
    if len(current_section) < 2:
        current_section = state_text.split("## Stage Progress", 1)
    scan_text = current_section[1] if len(current_section) >= 2 else state_text

    for line in scan_text.splitlines():
        m_completed = _LEGACY_STATE_RE.match(line)
        m_skipped = _LEGACY_SKIPPED_RE.match(line)  # new regex for [-]
        if m_completed:
            # ... existing mapping logic -> add to completed
        elif m_skipped:
            # ... mapping logic -> add to skipped
    return completed, skipped
```

Also add `_LEGACY_SKIPPED_RE = re.compile(r"^\s*-?\s*\[-\]\s*(.+)$")` to catch
`[-]` markers.

**Test:** State file with prior `[x] Units Generation` and current
`[-] Unit Decomposer SKIPPED`. Adoption should NOT include `unit-decomposer`
in completed_stages, and SHOULD include it in skipped_stages.

---

## 🟡 Bug 7: KeyError on missing `file` key in review merge

**File:** `aidlc-scripts/factory_merge_reviews.py:184`
**Severity:** 🟡 MEDIUM — **CONFIRMED**

**Observation:** `file_findings[f["file"]][reviewer].append(f)` raises KeyError
if a finding dict lacks the `file` key. Schema validation is optional (only
applied if `jsonschema` is installed), so malformed reviewer output can crash
the merge.

**Fix:**

```python
# Before (line 184):
file_findings[f["file"]][reviewer].append(f)

# After:
file_key = f.get("file", "?")
file_findings.setdefault(file_key, {}).setdefault(reviewer, []).append(f)
```

**Test:** Inject a finding without `file` field into a reviewer output YAML, run
merge — should warn and use `"?"` instead of crashing.

---

## 🟡 Bug 8: Floating-point accumulation in wall clock tracking

**File:** `aidlc-scripts/factory_budget.py:185`
**Severity:** 🟡 MEDIUM — **CONFIRMED**

**Observation:** Each `deduct` adds float values. IEEE 754 drift is visible in
existing data: `45.400000000000006`. Over many sub-stages this compounds.

**Verified:** Existing budget.yaml line 24 shows `45.400000000000006`.

**Fix:** `round()` to 1 decimal on every write:

```python
# In cmd_deduct():
state["used"]["wall_clock_min"] = round(
    float(state["used"].get("wall_clock_min", 0.0)) + float(args.wall_min), 1
)
```

**Test:** 1000 deductions of 0.1 min → accumulated value should be exactly
100.0, not 99.999999999.

---

## 🟢 Bug 9: TOCTOU race in `complete-stage` and `deduct`

**File:** `aidlc-scripts/factory_run.py:208-217`, `aidlc-scripts/factory_budget.py:180-204`
**Severity:** 🟢 LOW — **NO ACTIVE EXPLOIT PATH**

**Assessment:** The read-modify-write pattern lacks file locking, BUT the
orchestrator processes stage post-processing **sequentially** within each run.
Cross-run isolation prevents races between different runs. This would only be
exploitable if two orchestrator sessions controlled the same run simultaneously
— not possible in the current single-writer architecture.

Add file locking for defense-in-depth if desired, but not urgent.

**Fix (optional):**

```python
import fcntl

def _lock_file(path: Path) -> int:
    lock_path = path.parent / f".{path.name}.lock"
    fd = os.open(str(lock_path), os.O_CREAT | os.O_RDWR)
    fcntl.flock(fd, fcntl.LOCK_EX)
    return fd
```

Wrap read-modify-write cycles in try/finally.

---

## 🟢 Bug 10: Lock overwrite on second `acquire`

**File:** `aidlc-scripts/factory_conflict.py:198-204`
**Severity:** 🟢 LOW — **NO ACTIVE EXPLOIT PATH**

**Assessment:** If the same holder calls `acquire` twice, the second call
overwrites the first lock's globs. But each unit has a unique holder name
(`code-generator:<unit>`), and the orchestrator only calls acquire once per
unit per layer. Not an active bug — defensive improvement only.

**Fix (optional):**

```python
existing_lock = locks_dir / f"{args.holder}.yaml"
if existing_lock.exists():
    existing = yaml.safe_load(existing_lock.read_text()) or {}
    merged = list(dict.fromkeys(existing.get("globs", []) + list(args.globs)))
    args.globs = merged
    if existing.get("mode") != args.mode:
        _die(f"cannot change lock mode from {existing['mode']} to {args.mode}")
```

---

## 🔵 Bug 11: Budget `check` ignores wall clock (enhancement context)

**See Bug 5** — this is the same issue. I consider this a feature gap
rather than a bug, because the plan's Cost Governor spec focuses on token
budget enforcement and wall clock is not mentioned in the `check` exit-code
contract. Re-classified from "wall clock ignored" to "wall clock enforcement
not implemented" — a Phase 6.5 enhancement, not a Phase 6 bug.

---

## Implementation Order

| Step | Bug | File | Severity | Effort |
|------|-----|------|----------|--------|
| 1 | 🔴 4 — Path traversal guard | `factory_run.py` + `factory_conflict.py` | 🔴 | 15 min |
| 2 | 🔴 2 — Non-negative deduct | `factory_budget.py` | 🔴 | 5 min |
| 3 | 🔴 1 — `_next_stage` validation | `factory_run.py` | 🔴 | 5 min |
| 4 | 🔴 3 — Legacy review mapping | `factory_run.py` | 🔴 | 10 min |
| 5 | 🟡 8 — Float precision | `factory_budget.py` | 🟡 | 5 min |
| 6 | 🟡 7 — KeyError guard | `factory_merge_reviews.py` | 🟡 | 5 min |
| 7 | 🟡 6 — Prior iteration exclusion | `factory_run.py` | 🟡 | 15 min |
| 8 | 🟡 5 — Wall clock check | `factory_budget.py` | 🟡 | 10 min |
| 9 | 🟢 9 — File locking (optional) | `factory_run.py` + `factory_budget.py` | 🟢 | 20 min |
| 10 | 🟢 10 — Lock merge (optional) | `factory_conflict.py` | 🟢 | 10 min |

**Total essential (🔴+🟡):** ~1 hour for 8 fixes.
**Total with 🟢 optional:** ~1.5 hours for 10 fixes.

---

## Fix Status (2026-05-12)

| Bug | Severity | File | Status | Verified |
|-----|----------|------|--------|----------|
| 1 — `_next_stage()` PHASE_ORDER guard | 🔴 | `factory_run.py` | ✅ Fixed | `resume → ship-agent` |
| 2 — Non-negative deduct | 🔴 | `factory_budget.py` | ✅ Fixed | `--tokens-in -1` rejected |
| 3 — Legacy review → 4 reviewers | 🔴 | `factory_run.py` | ✅ Fixed | All 4 in adopted_stages |
| 4 — Path traversal guard | 🔴 | `factory_run.py` + `factory_conflict.py` | ✅ Fixed | `../../../etc` rejected |
| 5 — Wall clock check | 🟡 | `factory_budget.py` | ✅ Fixed | `remaining_wall_min` in output; exhaustion → exit 3 |
| 6 — Prior-iteration exclusion | 🟡 | `factory_run.py` | ✅ Fixed | Prior `[x]` not in adopted |
| 7 — KeyError on missing `file` | 🟡 | `factory_merge_reviews.py` | ✅ Fixed | `.get("file", "?")` guard |
| 8 — Float precision | 🟡 | `factory_budget.py` | ✅ Fixed | `round(..., 1)` applied |
| 9 — File locking | 🟢 | (deferred) | ⏸️ Not implemented | No active exploit path |
| 10 — Lock merge on re-acquire | 🟢 | `factory_conflict.py` | ✅ Fixed | `src/**` + `tests/**` merged |

## Propagation to Consumer Projects

After fixing canonical scripts at `<repo-root>/aidlc-scripts/`:

```bash
python3 aidlc-scripts/install_aidlc.py --dest ../pruebaaidlcv2

# Verify fixes:
python3 ../pruebaaidlcv2/aidlc-scripts/factory_run.py resume 2026-05-11-healthz-endpoint
python3 ../pruebaaidlcv2/aidlc-scripts/factory_budget.py status 2026-05-11-healthz-endpoint
```
