# Run Status

You are the AIDLC orchestrator. The user wants to know the state of run `$ARGUMENTS`.

1. Read the manifest:
   ```bash
   python3 aidlc-scripts/factory_run.py status $ARGUMENTS --json
   ```
2. Show the visual timeline:
   ```bash
   python3 aidlc-scripts/factory_run.py graph $ARGUMENTS
   ```
3. Compute next steps:
   ```bash
   python3 aidlc-scripts/factory_run.py resume $ARGUMENTS
   ```
4. Check for stale locks:
   ```bash
   python3 aidlc-scripts/factory_conflict.py list $ARGUMENTS
   python3 aidlc-scripts/factory_conflict.py conflicts $ARGUMENTS
   ```
5. Summarize in plain language:
   - Stages complete / total
   - Current stage status
   - Next stage
   - Any conflicts, drift, or warnings
   - Suggested next `/factory-*` command
