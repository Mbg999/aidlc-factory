# NFR Requirements — quality Unit

**Run ID:** 2026-06-03T08-21-21Z-improve-aidlc-factory-node-python-consolidation
**Unit:** quality
**Date:** 2026-06-03

## Performance

| Requirement | Target | Measure |
|-------------|--------|---------|
| radon cc execution | < 5s | Wall-clock time for `radon cc aidlc-scripts/*.py -s` |
| pytest execution | < 30s total | `pytest tests/` with new tests |
| validate_logging.py execution | < 2s | Wall-clock time for single run |

## Security

| Requirement | Rationale |
|-------------|-----------|
| No shell injection in _log() helper | _log() only takes level, msg string args — no command execution |
| No secrets in log output | _log() does not accept arbitrary kwargs that could leak env vars |
| Error messages must not reveal internal paths | _log() truncates paths to relative when possible |

## Maintainability

| Requirement | Target | Measure |
|-------------|--------|---------|
| Cyclomatic complexity reduction | ≥20% | `radon cc` before vs after for target scripts |
| Shared logging helper | One `_log()` in `skill_utils.py` | Code review |
| No bare print() for errors/warnings | 0 matches | `grep -P 'print\s*\([^)]*error|warning' aidlc-scripts/*.py` |
| Validate_logging.py enforces consistency | Passes with 0 violations | `python scripts/validate_logging.py` |

## Observability

| Requirement | Implementation |
|-------------|----------------|
| Error output destination | sys.stderr for ERROR/WARNING levels |
| Log format | `[<script_name>] <LEVEL>: <msg>` |
| Log level vocabulary | DEBUG, INFO, WARNING, ERROR, CRITICAL |

## Testability

| Requirement | Implementation |
|-------------|----------------|
| Each bug fix has a regression test | Test that reproduces the bug and fails on original code |
| New tests are in existing test files | `test_factory_run.py`, `test_install_aidlc.py`, etc. |
| All tests pass | `pytest tests/` returns 0 failures |

## Compatibility

- All changes must work on Windows, macOS, Linux
- No external dependencies added beyond what's in `requirements.txt`
- Python 3.10+ compatibility
