# Run Manager

PRIORITY: P3

`factory_run.py` — owns `runs/<run-id>/manifest.yaml` + `timeline.jsonl`.

| Call | Subcommand |
|---|---|
| Init | `init <run-id> --user-request <text> --project-slug <slug>` |
| Pre-spawn | `emit <run-id> --evt spawn_start --stage <s> --field tokens_estimate=N` |
| Post-spawn | `emit <run-id> --evt spawn_end --stage <s> --field status=<s> --field tokens=N --field wall_min=N` |
| Stage success/fail | `complete-stage` / `fail-stage <run-id> <stage> --reason <text>` |
| Resume | see [`runtime/cmd-factory-resume.md`](cmd-factory-resume.md) |
| Replay | see [`runtime/cmd-factory-replay.md`](cmd-factory-replay.md) |
| Non-spawn audit | `emit_audit_block` — see [`audit-block.protocol.md`](../contracts/audit-block.protocol.md) |
| Context snapshot | `factory_context_builder.py <run-id> --depth <depth>` — see [`runtime/contextualization.md`](contextualization.md) |

Atomicity: manifest POSIX-atomic (tmpfile+rename), timeline append-only atomic per line.
Failed→skipped recovery: [`runtime/recovery.md`](recovery.md).
