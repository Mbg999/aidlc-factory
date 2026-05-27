---
name: factory-resume
description: Resume an interrupted AIDLC orchestrator run from its last checkpoint.
---

# factory-resume — AIDLC Resume

Adopt the role from `.aidlc-orchestrator/agents/orchestrator.md`.

**Argument:** the run-id provided by the user.

If run-id is empty: tell the user a run-id is required and show available
runs with `python3 aidlc-scripts/factory_run.py list`.

If run-id is provided: this is a **resume** request.

1. Read run state:
   ```bash
   python3 aidlc-scripts/factory_run.py status <run-id>
   ```
2. Compute the next stage to spawn:
   ```bash
   python3 aidlc-scripts/factory_run.py resume <run-id>
   ```
   The output includes `next_stage_suggestion` and any `partial_outputs[]`
   left from a prior crash.
3. **If `partial_outputs[]` is non-empty**: warn the user. Two recovery options:
   - **Trust and complete** — read the partial output, validate against
     contract, and if valid, mark the stage complete.
   - **Re-spawn fresh** — delete the partial output, then proceed with
     a clean spawn of the next stage.
4. Surface the recovery choice to the user; await confirmation.
5. Once confirmed, route to the appropriate stage per orchestrator protocol.

Hard rules from `.aidlc-orchestrator/agents/orchestrator.md` apply.
