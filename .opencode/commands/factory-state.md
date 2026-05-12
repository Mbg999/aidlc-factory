---
description: Show the current state of a run — completed stages, current stage, next steps, budget, and any issues.
argument-hint: <run-id>
---

# Run Status

You are the AIDLC orchestrator. The user wants to know the state of run
`$ARGUMENTS`.

1. `python3 scripts/factory_run.py status $ARGUMENTS --json` — read manifest
2. `python3 scripts/factory_run.py graph $ARGUMENTS` — visual timeline
3. `python3 scripts/factory_budget.py status $ARGUMENTS` — budget
4. `python3 scripts/factory_run.py resume $ARGUMENTS` — next stage
5. `python3 scripts/factory_conflict.py list $ARGUMENTS` — active locks
6. Summarize: stages done, current stage, next, budget remaining, issues
