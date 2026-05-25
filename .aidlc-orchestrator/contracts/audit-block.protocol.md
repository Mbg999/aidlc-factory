# Audit-Block Protocol — Canonical Reference

**Single source of truth** for non-spawn audit blocks (user decisions, user
answers, stage-skipped events, orchestrator notes). Enforced by
`aidlc-scripts/factory_run.py emit_audit_block`. For helper internals,
example renders, file lifecycle, and history, see
[`audit-block.protocol.appendix.md`](audit-block.protocol.appendix.md).

## Invocation

Every non-spawn audit block is created with **one call**:

```bash
python3 aidlc-scripts/factory_run.py emit_audit_block <run-id> \
    --evt <evt-name> \
    --stage <stage-id> \
    --phase <PHASE> \
    --label "<BLOCK LABEL>" \
    --field key=value [--field ...] \
    --bullet "<text>" [--bullet ...]
```

The helper validates inputs, emits a timeline event for the canonical `ts`,
acquires `flock` on `aidlc-docs/audit.md`, dedupes retries, enforces
chronology, appends the block, and prints the `ts` to stdout. On failure it
returns non-zero with no mutation. Full sequence in the appendix.

## Canonical evt vocabulary

The ONLY allowed evt names for non-spawn audit blocks:

| Trigger | evt | Required fields | Required `--stage` |
|---|---|---|:---:|
| User answered clarifying questions (e.g. Pass 1 of requirements-analyst) | `user_answers_received` | — | yes |
| User approved / rejected / amended a stage artifact at an approval gate | `user_decision` | `decision=<approve\|reject\|amend\|cancel>` | yes |
| A non-critical stage spawn failed and the orchestrator recovered by skipping | `stage_skipped` | `reason=<text>` | yes |
| Orchestrator-side state mutation that doesn't fit the above (rare) | `orchestrator_note` | `summary=<text>` | no |

**Spawn cycles** (`spawn_start` / `spawn_end`) use plain `factory_run.py emit` —
NOT this helper. This helper is for the four non-spawn evts above.

## Header format (locked)

```
## <ts> <PHASE> - <BLOCK LABEL>
- bullet1
- bullet2
```

Followed by exactly one blank line as the section separator. The H2 header is
the only structural marker; reviewers and downstream tools parse against this
pattern. `<PHASE>` ∈ {`INCEPTION`, `CONSTRUCTION`, `OPERATIONS`}.

## Failure modes (all return non-zero, no mutation)

| Condition | Error |
|---|---|
| evt not in vocabulary | `unknown evt: ... Valid evt vocabulary: ...` |
| phase ∉ {INCEPTION, CONSTRUCTION, OPERATIONS} | `invalid phase: ...` |
| evt requires `--stage` but none given | `evt 'X' requires --stage` |
| evt requires `--field K=V` but K is missing | `evt 'X' requires --field K=<value>` |
| no `--bullet` supplied | `at least one --bullet is required` |
| run_id doesn't have a manifest.yaml | `run not found: ...` |
| ts < last header's ts (chronology violation) | `chronology violation: ts <new> < last audit ts <old>` |

## Retry semantics

If a stage spawn fails after `emit_audit_block` succeeded but before the
orchestrator commits its own state, the orchestrator may re-invoke
`emit_audit_block` with `--ts <previous-ts>` to retry idempotently. The
dedupe guard will detect the identical block and skip; the helper still
exits 0 and prints `<ts> (dedupe skipped — identical block already present)`.

## Concurrency

POSIX `fcntl.flock` on `audit.md.lock`. Multiple parallel writers (e.g.
layer-parallel `/factory-build` writing audit entries per unit) serialize
correctly; no two writers can interleave into the same `## ` block.
Verified by `tests/test_emit_audit_block.py::test_emit_audit_block_concurrent_writers_serialize`.

## Exact invocations per gate

The orchestrator references these sections by name from `.claude/agents/orchestrator.md`. Each block is the literal command to run when that gate fires.

### § reverse-engineer gate

```bash
python3 aidlc-scripts/factory_run.py emit_audit_block <run-id> \
    --evt user_decision --stage reverse-engineer --phase INCEPTION \
    --label "User Decision (reverse-engineer)" \
    --field decision=<approve|reject> \
    --bullet "[User] <Approved reverse-engineer spawn | Skipped reverse-engineer (small-scope: <truncated request>)>"
```

### § user_answers_received

For requirements-analyst Pass 1 (after the user provides letter picks):

```bash
python3 aidlc-scripts/factory_run.py emit_audit_block <run-id> \
    --evt user_answers_received --stage requirements-analyst --phase INCEPTION \
    --label "User Answers Received" \
    --bullet "[User] Q1=<letter> (<gloss>)" \
    --bullet "[User] Q2=<letter> (<gloss>)" \
    --bullet "[Orchestrator] Tension flagged for Pass 2: <text>"
```

Repeat `--bullet` once per answered question and once per Pass 2 tension carry-forward.

### § workflow-planner gate

```bash
python3 aidlc-scripts/factory_run.py emit_audit_block <run-id> \
    --evt user_decision --stage workflow-planner --phase INCEPTION \
    --label "User Decision (workflow-planner)" \
    --field decision=<approve|reject|amend> \
    --bullet "[User] <Approved|Rejected|Amended> <run-id>-execution-plan.md (<gloss>)"
```

### § code-generator gate

For each approval inside `/factory-build` (sub-stages `plan` and `generated`):

```bash
python3 aidlc-scripts/factory_run.py emit_audit_block <run-id> \
    --evt user_decision --stage code-generator --phase CONSTRUCTION \
    --label "User Decision (code-generator <sub_stage>)" \
    --field decision=<approve|reject|cancel> --field sub_stage=<plan|generated> \
    --field rejected_units="<csv>" \
    --bullet "[User] <decision summary per unit>"
```

### § build-test-agent gate

```bash
python3 aidlc-scripts/factory_run.py emit_audit_block <run-id> \
    --evt user_decision --stage build-test-agent --phase CONSTRUCTION \
    --label "User Decision (layer <n> build/test)" \
    --field decision=<approve|reject|amend> --field layer=<n> \
    --bullet "[User] <decision summary>"
```

### § review gate

```bash
python3 aidlc-scripts/factory_run.py emit_audit_block <run-id> \
    --evt user_decision --stage review --phase CONSTRUCTION \
    --label "User Decision (review)" \
    --field decision=<approve|request_fixes> --field rejected_units="<csv>" \
    --bullet "[User] <outcome summary>"
```

### § stage_skipped

For Failed→skipped recovery when a non-critical stage spawn fails:

```bash
python3 aidlc-scripts/factory_run.py emit_audit_block <run-id> \
    --evt stage_skipped --stage <s> --phase <PHASE> \
    --label "<STAGE LABEL> SKIPPED (<short-reason>)" \
    --field reason="<text>" \
    --bullet "[Orchestrator] failure cause: <text>" \
    --bullet "[Orchestrator] skip decision rationale: <text>" \
    --bullet "[Orchestrator] fallback: <text>"
```

Critical stages (`workspace-scout`, `requirements-analyst`, `workflow-planner`, `code-generator`, `build-test-agent`) MUST halt instead — use `factory_run.py fail-stage`, not this helper.
