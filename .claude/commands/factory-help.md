---
description: Quick reference for all AIDLC orchestrator commands. For a step-by-step guide, use /factory-onboarding.
argument-hint: [command-name]
---

# AIDLC Orchestrator — Command Reference

## Commands

| Command | What it does |
|---------|-------------|
| `/factory-onboarding` | Walk through the system: how runs work, what to expect |
| `/factory-budget <status\|config\|help>` | Configure and monitor the Cost Governor |
| `/factory-state <run-id>` | Show run status: current stage, next step, budget, timeline |
| `/factory-spec <request>` | **Entrypoint.** Scores your request, spawns the right stages |
| `/factory-plan <run-id>` | After spec: creates execution plan and design units |
| `/factory-build <run-id>` | After plan: generates code + runs tests in parallel |
| `/factory-review <run-id>` | After build: 4 parallel reviewers (code, security, perf, simplifier) |
| `/factory-ship <run-id>` | After review: release notes, ADRs, changelog, CI/CD |
| `/factory-resume <run-id>` | Pick up a crashed/interrupted run from last checkpoint |
| `/factory-replay <run-id> --from <stage>` | Re-run from a specific stage (archives prior outputs) |
| `/factory-self <task>` | Run the orchestrator on **its own codebase** (self-hosting) |

## Quick start

```
/factory-spec "add healthz endpoint to the API gateway"
```

If the request is trivial (typo, one-file change), the Fast Path kicks in:
`/factory-spec` → code-generator → commit → done. No multi-agent overhead.

For complex work, the full pipeline runs: spec → plan → build → review → ship.
Each step is a separate `/factory-*` command so you can inspect before proceeding.

## Monitoring a run

```bash
# Visual timeline of completed stages
python3 scripts/factory_run.py graph <run-id>

# Budget usage (tokens, wall clock)
python3 scripts/factory_budget.py status <run-id>

# Approval gate latency
python3 scripts/factory_run.py status <run-id> --latency

# Live event tail
python3 scripts/factory_run.py tail <run-id> --follow
```

## Recovery

| Situation | What to do |
|-----------|-----------|
| Run crashed mid-stage | `/factory-resume <run-id>` |
| Stage produced wrong output | `/factory-replay <run-id> --from <stage>` |
| Agent crashed, locks stale | `python3 scripts/factory_conflict.py release <run-id> --stale --older-than 120` |
| Run burned too many tokens | Start over with tighter budget in `.aidlc-orchestrator/budgets/default.yaml` |

## Tools

- **Triage:** `python3 scripts/factory_triage.py "<request>" [--dry-run]` — score without spawning
- **Validate:** `python3 scripts/factory_validate.py schema.json doc.yaml [--strict]`
- **Secret scan:** `python3 scripts/factory_secretscan.py handoff.yaml`
- **Audit writes:** `python3 scripts/factory_audit_writes.py <run-id> <holder> --locks src/**`

## Documentation

- `docs/TROUBLESHOOTING.md` — common failures and fixes
- `.aidlc-orchestrator/contracts/REFERENCE.md` — all handoff schemas
- `ORCHESTRATOR-PLAN.md` — full design doc (phases, decisions, ACs)
