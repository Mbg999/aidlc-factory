---
agent: orchestrator
mode: agent
description: Show the current state of a run — completed stages, current stage, next steps, budget, and any issues.
---

# Run Status

You are the AIDLC orchestrator. The user wants to know the state of run
`<run-id>`.

1. Read the manifest:
   ```bash
   python aidlc-scripts/factory_run.py status <run-id> --json
   ```

2. Show the visual timeline:
   ```bash
   python aidlc-scripts/factory_run.py graph <run-id>
   ```

3. Compute next steps:
   ```bash
   python aidlc-scripts/factory_run.py resume <run-id>
   ```

5. Check for stale locks:
   ```bash
   python aidlc-scripts/factory_conflict.py list <run-id>
   python aidlc-scripts/factory_conflict.py conflicts <run-id>
   ```

6. Summarize in plain language:
   - How many stages complete / total
   - What's the current stage and how it's doing
   - What stage runs next
   - Any conflicts, drift, or warnings
   - Suggested next `/factory-*` command to run
