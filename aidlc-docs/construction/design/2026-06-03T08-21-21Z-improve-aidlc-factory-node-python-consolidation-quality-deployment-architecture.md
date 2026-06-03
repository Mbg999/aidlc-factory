# Deployment Architecture — quality Unit

**Run ID:** 2026-06-03T08-21-21Z-improve-aidlc-factory-node-python-consolidation
**Unit:** quality
**Date:** 2026-06-03

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    aidlc-factory/                            │
│                                                              │
│  ┌─────────────────────┐   ┌──────────────────────────┐     │
│  │ aidlc-scripts/       │   │ tests/                   │     │
│  │                      │   │                          │     │
│  │ factory_run.py      │   │ test_factory_run.py      │     │
│  │ install_aidlc.py    │   │ test_install_aidlc.py    │     │
│  │ factory_telemetry.py│   │ test_factory_validate.py │     │
│  │ factory_validate.py │   │  (other tests)           │     │
│  │ skill_utils.py ◄────┼───┤                          │     │
│  │ (other scripts)     │   │                          │     │
│  └─────────────────────┘   └──────────────────────────┘     │
│                                                              │
│  ┌─────────────────────┐                                     │
│  │ scripts/             │                                     │
│  │ validate_logging.py │  (NEW)                              │
│  └─────────────────────┘                                     │
└─────────────────────────────────────────────────────────────┘
```

## Data Flow

### T2.1 Complexity Reduction
```
radon cc aidlc-scripts/*.py -s
    → Identify top 3 complex scripts
    → Refactor each (extract functions, reduce nesting, add docstrings)
    → radon cc aidlc-scripts/*.py -s (verify ≥20% reduction)
```

### T2.2 Regression Tests
```
Identify Unit 1 bugs (from test comments, git log)
    → Write reproduction test
    → Confirm test fails on original code
    → Confirm test passes after fix
    → Run full pytest suite
```

### T2.3 Logging Consistency
```
Grep aidlc-scripts/*.py for print(...) with error/warning
    → Create _log() in skill_utils.py
    → Migrate each script
    → Create scripts/validate_logging.py
    → Run validation
```

## No External Infrastructure Changes

This unit does not modify deployment pipelines, container configurations, or cloud resources.
