# Infrastructure Design — quality Unit

**Run ID:** 2026-06-03T08-21-21Z-improve-aidlc-factory-node-python-consolidation
**Unit:** quality
**Date:** 2026-06-03

## Deployment Model

No deployment changes. This unit modifies existing Python scripts and test files within the `aidlc-factory/` repository. All changes are local to the development environment.

## Infrastructure Services

| Service | Change | Rationale |
|---------|--------|-----------|
| Python runtime | None | All changes compatible with Python 3.10+ (existing target) |
| `radon` tool | Added as dev dependency | Required for cyclomatic complexity measurement (AC-2.1) |
| pytest | Already installed | Used for regression tests (AC-2.3) |

## CI/CD Impact

- No CI/CD changes
- New `scripts/validate_logging.py` can be added to CI pipeline as a quality gate
- All existing `/factory-*` commands must remain unchanged

## File Lock Requirements

| Path | Access | Purpose |
|------|--------|---------|
| `aidlc-factory/aidlc-scripts/*.py` | read+write | Refactoring (T2.1) + logging migration (T2.3) |
| `aidlc-factory/tests/` | read+write | New regression tests (T2.2) |
| `aidlc-factory/scripts/validate_logging.py` | create | New logging validation script (T2.3) |
| `aidlc-factory/aidlc-scripts/skill_utils.py` | read+write | Add `_log()` helper (T2.3) |

## Cross-Platform Considerations

- `_log()` helper uses `sys.stderr` (works on all platforms)
- `radon cc` is pure Python (works on all platforms)
- New tests use `subprocess` patterns already established in test suite
- `validate_logging.py` uses regex only (no platform-specific code)
