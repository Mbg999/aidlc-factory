---
description: Quick reference for all AIDLC orchestrator commands.
argument-hint: [command-name]
---

# AIDLC Orchestrator — Command Reference

## Commands

| Command | What it does |
|---------|-------------|
| `/factory-onboarding` | Walk through the system |
| `/factory-state <run-id>` | Show run status: current stage, next step, budget |
| `/factory-spec <request>` | **Entrypoint.** Score + spawn stages |
| `/factory-plan <run-id>` | Execution plan + design units |
| `/factory-build <run-id>` | Parallel code-gen + build-test |
| `/factory-review <run-id>` | 4 parallel reviewers |
| `/factory-ship <run-id>` | Release notes, ADRs, changelog |
| `/factory-resume <run-id>` | Resume crashed run |
| `/factory-replay <run-id> --from <stage>` | Re-run from a stage |
| `/factory-self <task>` | Run on own codebase |

## Quick start

```
/factory-spec "add healthz endpoint"
```

## Monitoring

```bash
python3 scripts/factory_run.py graph <run-id>
python3 scripts/factory_budget.py status <run-id>
python3 scripts/factory_run.py tail <run-id> --follow
```

## Recovery

| Situation | Action |
|-----------|--------|
| Crash | `/factory-resume <run-id>` |
| Bad output | `/factory-replay <run-id> --from <stage>` |
| Stale locks | `python3 scripts/factory_conflict.py release <run-id> --stale --older-than 120` |

## Docs

- `docs/TROUBLESHOOTING.md`
- `.aidlc-orchestrator/contracts/REFERENCE.md`
- `ORCHESTRATOR-PLAN.md`
