---
name: factory-state
description: Show the current state of a run — completed stages, current stage, next steps, budget, and any issues.
---

# factory-state — AIDLC Run Status

Adopt the role from `.aidlc-orchestrator/agents/orchestrator.md`.

**Argument:** the run-id provided by the user.

1. Read the manifest:
   ```bash
   python3 aidlc-scripts/factory_run.py status <run-id> --json
   ```

2. Show the visual timeline:
   ```bash
   python3 aidlc-scripts/factory_run.py graph <run-id>
   ```

3. Compute next steps:
   ```bash
   python3 aidlc-scripts/factory_run.py resume <run-id>
   ```

5. Check for stale locks:
   ```bash
   python3 aidlc-scripts/factory_conflict.py list <run-id>
   python3 aidlc-scripts/factory_conflict.py conflicts <run-id>
   ```

6. Summarize in plain language:
   - How many stages complete / total
   - What's the current stage and how it's doing
   - What stage runs next
   - Any conflicts, drift, or warnings
   - Suggested next `/factory-*` command to run
