---
name: factory-replay
description: Re-run an AIDLC orchestrator run from a specific stage. Rolls the manifest back, archives output handoffs, and routes to the chosen stage.
---

# factory-replay — AIDLC Replay

Adopt the role from `.aidlc-orchestrator/agents/orchestrator.md`.

**Arguments:** `<run-id> --from <stage-name>`

Parse `<run-id>` and the `--from <stage>` value. If malformed, refuse with a usage hint.

1. Roll the manifest back and archive handoffs:
   ```bash
   python3 aidlc-scripts/factory_run.py replay <run-id> --from <stage>
   ```
   This:
   - Truncates `manifest.completed_stages[]` before `<stage>`
   - Sets `manifest.current_stage = <stage>`
   - Renames each rolled-back stage's `*.output.yaml` to `*.replay-<unix-ts>.yaml`
   - Emits a `replay_requested` event to `timeline.jsonl`

2. Surface the result to the user — list of `rolled_back` stages and
   `archived_outputs` paths.

3. Spawn the chosen stage per the orchestrator protocol (validate input,
   apply pre-flight gates from Cost Governor + Conflict Resolver, etc.).

**Use cases:**
- A reviewer found a P0 issue that requires re-doing code generation for a unit.
- The user wants to adjust requirements after seeing the plan.
- A schema bump requires re-running a stage with the new format.

**Replay is destructive to the manifest's progress record but non-destructive
to artifacts.** Old outputs are archived, never deleted.

Hard rules from `.aidlc-orchestrator/agents/orchestrator.md` apply.
