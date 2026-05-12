---
description: AIDLC Orchestrator command reference. Lists all factory slash commands with descriptions and examples.
argument-hint: [command-name] (optional — filter to a specific command)
---

# AIDLC Orchestrator — Command Reference

## Available Commands

| Command | Description | Phase |
|---------|-------------|-------|
| `/factory-spec <request>` | Run inception (workspace detection + requirements analysis) | 0 |
| `/factory-plan <run-id>` | Run workflow planning + unit decomposition | 1 |
| `/factory-build <run-id>` | Run code generation + build/test in parallel waves | 2-3 |
| `/factory-review <run-id>` | Run parallel 4-reviewer pool + merge report | 4 |
| `/factory-ship <run-id>` | Run finalization and knowledge capture | 5-6 |
| `/factory-resume <run-id>` | Resume a crashed run from last checkpoint | Recovery |
| `/factory-replay <run-id> --from <stage>` | Roll back completed stages and replay | Recovery |

## Scripts (called by the orchestrator)

```
scripts/factory_triage.py     — Complexity scorer (TINY/SMALL/MEDIUM/LARGE)
scripts/factory_budget.py     — Cost Governor (init/check/deduct/status)
scripts/factory_run.py        — Run Manager (init/complete-stage/resume/replay/graph/status/tail)
scripts/factory_conflict.py   — Conflict Resolver (acquire/release/snapshot/check-symbols)
scripts/factory_validate.py   — JSON Schema validator
scripts/factory_merge_reviews.py — Merge 4 reviewer outputs into review-report.md
```

## Fast Path (TINY tier)

For trivial requests (score 0), the orchestrator skips the full pipeline and
spawns `code-generator` directly.

## Common Workflows

```bash
# 1. Score a request
python3 scripts/factory_triage.py "add healthz endpoint" [--dry-run]

# 2. Initialize a run
python3 scripts/factory_run.py init 2026-05-12-my-feature --user-request "..."
python3 scripts/factory_budget.py init 2026-05-12-my-feature

# 3. Check run status
python3 scripts/factory_run.py status 2026-05-12-my-feature [--latency]
python3 scripts/factory_run.py graph 2026-05-12-my-feature

# 4. Validate a contract
python3 scripts/factory_validate.py schema.json document.yaml [--strict]

# 5. Manage file locks
python3 scripts/factory_conflict.py acquire <run-id> <holder> <glob>... [--ttl-minutes 60]

# 6. Troubleshooting
See docs/TROUBLESHOOTING.md
```

