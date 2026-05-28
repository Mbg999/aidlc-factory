---
name: factory-help
description: AIDLC Orchestrator help. Explains all commands and how to get started.
---

# factory-help — AIDLC Orchestrator Help

Start any new feature with:

```
/factory-spec "<request>"
```

## Orchestrator workflow

The orchestrator uses specialized subagents per stage. Start with:

```
/factory-spec "add JWT auth to the API gateway"
```

This triggers triage (TINY -> FastPath, or SMALL+ -> full pipeline).

### Full pipeline

| Command | Purpose |
|---------|---------|
| `/factory-spec <request>` | workspace-scout -> requirements-analyst |
| `/factory-plan <run-id>` | workflow-planner -> unit-decomposer |
| `/factory-build <run-id>` | code-generator x N units + build-test-agent |
| `/factory-review <run-id>` | 4 parallel reviewers -> merged report |
| `/factory-ship <run-id>` | release notes, ADRs, changelog, CI/CD |

Each command waits for your approval before proceeding.

### Fast Path (TINY tier)

For trivial requests, the orchestrator skips all stages and goes directly to
code-generator.

## Command reference

| Command | What happens |
|---------|-------------|
| `/factory-onboarding` | Guided tour of the system |
| `/factory-code-tour` | Architecture map, key flows, conventions |
| `/factory-spec "<request>"` | Triages request, spawns scout + analyst |
| `/factory-plan <run-id>` | Creates execution plan + design units |
| `/factory-build <run-id>` | Generates code + runs tests in parallel |
| `/factory-review <run-id>` | 4 reviewers analyze code in parallel |
| `/factory-ship <run-id>` | Release notes, ADRs, changelog |
| `/factory-state <run-id>` | Current stage, next step, timeline |
| `/factory-resume <run-id>` | Picks up from the last completed stage |
| `/factory-replay <run-id> --from <stage>` | Rolls back and re-runs from that stage |
| `/factory-self "<task>"` | Runs pipeline against orchestrator's own code |
| `/factory-help` | This page |

## Monitoring

```bash
python3 aidlc-scripts/factory_run.py graph <run-id>
python3 aidlc-scripts/factory_run.py status <run-id> --latency
python3 aidlc-scripts/factory_run.py tail <run-id> --follow
```

## Recovery

| Situation | Solution |
|-----------|----------|
| Run crashed or session closed | `/factory-resume <run-id>` |
| Stage produced wrong output | `/factory-replay <run-id> --from <stage>` |
| Stale locks | `factory_conflict.py release <run-id> --stale --older-than 120` |

## CLI tools

```bash
python3 aidlc-scripts/factory_triage.py prefilter "add healthz" --dry-run
python3 aidlc-scripts/factory_validate.py schema.json doc.yaml --strict
```
