# NFR Design Patterns — quality Unit

**Run ID:** 2026-06-03T08-21-21Z-improve-aidlc-factory-node-python-consolidation
**Unit:** quality
**Date:** 2026-06-03

## Resilience Patterns

### Pattern: Graceful Degradation (Logging)
- If `_log()` cannot be imported (e.g. user runs script standalone), fall back to bare `print(file=sys.stderr)`
- The logging helper itself should never raise — wrap in try/except

### Pattern: Idempotent Test Runner
- Running `pytest tests/` twice produces identical results
- Tests must not depend on shared mutable state

## Logging Strategy

### Log Helper Signature (`skill_utils.py`)
```python
def _log(level: str, msg: str, *, script: str = "", file=sys.stderr) -> None:
    """Unified logging for AIDLC factory scripts.

    Args:
        level: One of DEBUG, INFO, WARNING, ERROR, CRITICAL
        msg: The log message
        script: Script name (auto-detected from __name__ if empty)
        file: Output stream (default: sys.stderr)
    """
    import sys as _sys
    import os as _os
    if not script:
        script = _os.path.basename(_sys.argv[0] or "aidlc")
    label = f"[{script}] {level.upper()}: {msg}"
    print(label, file=file)
```

### Migration Table

| Pattern | Old | New |
|---------|-----|-----|
| `_die(msg)` | `print(msg, file=sys.stderr); sys.exit(code)` | `_log("ERROR", msg); sys.exit(code)` |
| `print(f"X: error: {msg}", file=sys.stderr)` | Script-prefixed error | `_log("ERROR", msg)` |
| `print("WARNING: ...")` | Bare warning to stdout | `_log("WARNING", msg)` |
| `print("ERROR: ...", file=sys.stderr)` | Error to stderr | `_log("ERROR", msg)` |

## Scaling Approach

Not applicable — refactoring and quality improvements have no scaling dimension.

## Complexity Reduction Strategy

### For `install_aidlc.py`:
1. Extract `install_orchestrator()` body → split into `_install_factory_scripts()`, `_install_contracts()`, `_install_per_tool()`, `_install_shared_deps()`
2. Extract `main()` → create `_handle_agent_skills()`, `_handle_orchestrator()`, `_handle_codegraph()` sub-functions
3. Add docstrings to all top-level functions

### For `factory_run.py`:
1. Extract `cmd_emit_audit_block()` validation logic into separate `_validate_emit_audit_args()` function
2. Simplify `_print_latency()` — extract per-stage timing into `_stage_timing()`
3. Extract `cmd_graph()` timeline parsing into `_parse_timeline_events()`

### For `factory_telemetry.py`:
1. Extract per-subcommand logic into focused functions
2. Extract common helpers (timeline parsing, event aggregation)
3. Reduce nesting in `discover` and `aggregate` subcommands
