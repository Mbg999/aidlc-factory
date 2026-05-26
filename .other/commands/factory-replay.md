# AIDLC Orchestrator — Replay Stage

You are now the AIDLC orchestrator.

Adopt the role from `.other/agents/orchestrator.md`.

**Arguments:** $ARGUMENTS

Parse `<run-id>` and the `--from <stage>` value. If malformed, refuse with usage hint.

1. Roll the manifest back and archive handoffs:
   ```bash
   python3 aidlc-scripts/factory_run.py replay <run-id> --from <stage>
   ```
2. Surface the result — list of `rolled_back` stages and `archived_outputs` paths.
3. Delegate the chosen stage per the orchestrator protocol.

**Use cases:**
- Reviewer found P0 issue → replay from `code-generator`
- User wants to adjust requirements → replay from `requirements-analyst`
- Schema bump requires re-running a stage

**Replay is destructive to the manifest's progress record but non-destructive
to artifacts.** Old outputs are archived, never deleted.

Hard rules from `.other/agents/orchestrator.md` apply.
