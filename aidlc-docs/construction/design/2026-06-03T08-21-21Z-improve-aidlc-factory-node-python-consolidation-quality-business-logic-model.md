# Business Logic Model — quality Unit

**Run ID:** 2026-06-03T08-21-21Z-improve-aidlc-factory-node-python-consolidation
**Unit:** quality
**Date:** 2026-06-03

## Overview

This unit targets three dimensions of codebase quality in the `aidlc-factory/` project:
1. **Maintainability** — reduce cyclomatic complexity in 3+ high-complexity scripts
2. **Test coverage** — add regression tests for critical paths covering bugs fixed in Unit 1
3. **Logging consistency** — replace bare `print()` for errors/warnings with a shared `_log()` helper

## Domain Model

### Entity: Script
- **Properties**: path, lines_of_code, cyclomatic_complexity (avg), functions[], dependencies[]
- **Relationships**: Script has-many Functions; Script belongs-to Repository
- **Detected Property**: Round-trip (serializable — script path can be serialized and loaded)

### Entity: ComplexityBaseline
- **Properties**: script_path, before_avg_complexity, after_avg_complexity, reduction_pct, timestamp
- **Detected Property**: Invariant — reduction_pct >= 20 after refactoring for target scripts; Oracle — Computed from radon cc

### Entity: RegressionTest
- **Properties**: test_name, bug_id, test_file, status (pass/fail), reproduced_bug (bool)
- **Detected Property**: Idempotency — running the test twice with same code yields same result

### Entity: LogHelper
- **Properties**: function_name (`_log`), signature `(level: str, msg: str, **kwargs) -> None`
- **Behavior**: Writes to sys.stderr for ERROR/WARNING levels; prefix format `[<script_name>] <LEVEL>: <msg>`

### Entity: LogValidator
- **Properties**: script_path, violations (list of bare print() calls), validation_result (pass/fail)
- **Behavior**: Greps for `print(...)` containing error/warning keywords

## Property Detection (PBT)

| Property | Domain Entity | Why It Applies |
|----------|--------------|----------------|
| Round-trip | Script | Path serialization round-trips correctly |
| Invariant | ComplexityBaseline | reduction_pct >= 20% |
| Oracle | ComplexityBaseline | radon cc is deterministic for same code |
| Idempotency | RegressionTest | Running the same test twice with the same code produces the same pass/fail result |
| Stateful | LogHelper | State changes are append-only (log lines written to stderr, cannot be undone) |

## Data Flow

1. **T2.1 Flow**:
   - Run `radon cc` on all `aidlc-scripts/*.py` → identify top 3 most complex
   - Refactor each: extract functions, reduce nesting, add docstrings
   - Re-run `radon cc` → verify ≥20% reduction

2. **T2.2 Flow**:
   - Identify bugs fixed in Unit 1 from test comments and git history
   - Write test that reproduces the bug → confirm it fails on original code
   - Apply fix (if not already fixed) → confirm test passes
   - Add to test suite

3. **T2.3 Flow**:
   - Audit all `aidlc-scripts/*.py` for `print()` with error/warning
   - Create shared `_log()` in `skill_utils.py` (existing shared module)
   - Migrate all scripts to use `_log()`
   - Create `scripts/validate_logging.py` → enforce consistency
