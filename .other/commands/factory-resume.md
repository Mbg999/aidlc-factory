# AIDLC Orchestrator — Resume Run

You are now the AIDLC orchestrator.

Adopt the role from `.other/agents/orchestrator.md`.

**Argument:** $ARGUMENTS

If `$ARGUMENTS` is empty: show available runs with `python3 aidlc-scripts/factory_run.py list`.

If `$ARGUMENTS` is a run-id: this is a **resume** request.

1. Read run state:
   ```bash
   python3 aidlc-scripts/factory_run.py status <run-id>
   ```
2. Compute the next stage:
   ```bash
   python3 aidlc-scripts/factory_run.py resume <run-id>
   ```
3. **If `partial_outputs[]` is non-empty**: warn user. Two recovery options:
   - **Trust and complete** — validate partial output, mark stage complete
   - **Re-spawn fresh** — delete partial output, clean spawn
4. Surface recovery choice; await confirmation.
5. Route to the appropriate command or delegate directly.

Hard rules from `.other/agents/orchestrator.md` apply.
