---
description: Show the current state of a run — completed stages, current stage, next steps, budget, and any issues.
argument-hint: <run-id>
---

# Run Status

You are the AIDLC orchestrator. The user wants to know the state of run
`$ARGUMENTS`.

1. Read the manifest:
   ```bash
   python3 scripts/factory_run.py status $ARGUMENTS --json
   ```

2. Show the visual timeline:
   ```bash
   python3 scripts/factory_run.py graph $ARGUMENTS
   ```

3. Check budget:
   ```bash
   python3 scripts/factory_budget.py status $ARGUMENTS
   ```

4. Compute next steps:
   ```bash
   python3 scripts/factory_run.py resume $ARGUMENTS
   ```

5. Check for stale locks:
   ```bash
   python3 scripts/factory_conflict.py list $ARGUMENTS
   python3 scripts/factory_conflict.py conflicts $ARGUMENTS
   ```

6. Summarize in plain language:
   - How many stages complete / total
   - What's the current stage and how it's doing
   - What stage runs next
   - Budget remaining (tokens and wall clock)
   - Any conflicts, drift, or warnings
   - Suggested next `/factory-*` command to run
