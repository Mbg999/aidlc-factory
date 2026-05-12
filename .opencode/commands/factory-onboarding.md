---
description: Walk through the AIDLC orchestrator system. Learn how runs work, what commands to use, and how to recover.
argument-hint: (no arguments needed)
---

# AIDLC Orchestrator — Onboarding

## 1. Two ways to work

**Legacy** — "Using AI-DLC, <your request>" in chat. Works on any tool.

**Orchestrator** — `/factory-spec "<request>"`. Dedicated subagents per stage.
Claude Code only (uses Task() spawning).

Use orchestrator for: multi-component features, brownfield work, budget caps,
crash recovery, parallel reviewer pool.

## 2. Start

```
/factory-spec "add JWT auth to the API gateway"
```

Triage → run-id → workspace-scout → requirements-analyst → questions (maybe).

Result: a `run-id` like `2026-05-12-jwt-auth`.

Fast Path (TINY score 0): skips all stages, goes straight to code-gen + commit.

## 3. Plan → Build → Review → Ship

```
/factory-plan <run-id>     # execution plan + design units
/factory-build <run-id>    # parallel code-gen + build-test per unit
/factory-review <run-id>   # 4 parallel reviewers → merged report
/factory-ship <run-id>     # release notes, ADRs, changelog
```

## 4. Recovery

| Situation | Action |
|-----------|--------|
| Crash | `/factory-resume <run-id>` |
| Bad output | `/factory-replay <run-id> --from <stage>` |
| Stale locks | `python3 scripts/factory_conflict.py release <run-id> --stale --older-than 120` |
| See timeline | `python3 scripts/factory_run.py graph <run-id>` |

## 5. Self-hosting

```
/factory-self "add --stale flag to factory_conflict.py release"
```

Runs the pipeline against the orchestrator's own code.

## Reference

- `/factory-help` — quick command list
- `docs/TROUBLESHOOTING.md` — failures and fixes
- `ORCHESTRATOR-PLAN.md` — full design doc
