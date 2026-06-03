# Domain Entities — quality Unit

**Run ID:** 2026-06-03T08-21-21Z-improve-aidlc-factory-node-python-consolidation
**Unit:** quality
**Date:** 2026-06-03

## Entities

### ScriptComplexity
```
{
  "path": "aidlc-scripts/install_aidlc.py",
  "functions": [
    {"name": "install_orchestrator", "complexity": 25, "lines": 140},
    {"name": "main", "complexity": 18, "lines": 80},
    {"name": "preflight_check", "complexity": 15, "lines": 60}
  ],
  "avg_complexity": 8.2,
  "total_lines": 2380
}
```

### RefactoringSlice
```
{
  "script": "aidlc-scripts/install_aidlc.py",
  "functions_extracted": ["install_orchestrator", ...],
  "nesting_reduced": true,
  "docstrings_added": true,
  "before_complexity": 8.2,
  "after_complexity": 5.8,
  "reduction_pct": 29.3
}
```

### Baseline (radon cc output)
```
{
  "script": "aidlc-scripts/install_aidlc.py",
  "before": {"avg": 8.2, "max": 25, "functions": 35},
  "after": {"avg": 5.8, "max": 15, "functions": 38}
}
```

## Target Scripts (T2.1)

| Script | Lines | Est. Avg CC | Reason |
|--------|-------|-------------|--------|
| `install_aidlc.py` | ~2380 | High (8+) | Monolithic main(), complex install_orchestrator(), deep nesting |
| `factory_run.py` | ~1042 | High (7+) | Multiple subcommands, long cmd_* functions, _flock/lock logic |
| `factory_telemetry.py` | ~953 | High (7+) | Multiple subcommands, aggregate/discover logic, nested loops |

## Regression Bug Targets (T2.2)

| Bug ID | Description | Script | Test File |
|--------|-------------|--------|-----------|
| B1 | `_flock` cross-platform lock race on Windows (fcntl/msvcrt fallback) | `factory_run.py` | `test_factory_run.py` — already partially tested |
| B2 | `_run_codegraph` Windows cmd.exe wrapper order (subprocess not resolving .cmd) | `install_aidlc.py` | `test_install_aidlc.py` |
| B3 | `update_workflow_doc_pointer` force-replace corrupts content after marker | `install_aidlc.py` | `test_install_aidlc.py` — already partially tested |

## LogAuditViolation (T2.3)
```
{
  "script": "aidlc-scripts/factory_validate.py",
  "line": 265,
  "violation": "print(f\"INVALID {doc_path} ({len(errors)} schema error...\", file=sys.stderr)",
  "action": "migrate to _log('error', ...)",
  "fixed": false
}
```
