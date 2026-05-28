---
name: factory-onboarding
description: Walk through the AIDLC orchestrator system. Learn how runs work, what commands to use, and how to recover from failures.
---

# factory-onboarding — AIDLC Orchestrator Onboarding

> **PRESENT THE FOLLOWING SECTIONS IN FULL TO THE USER.**
> Do not summarize. Do not assume the user has seen this before.

## 1. How it works

Use `/factory-spec "<request>"`. A dedicated orchestrator agent spawns
specialized subagents (scout, analyst, code-gen, reviewer, etc.) per stage.

**When to use the orchestrator:**
- Multi-component features (several files, services, or modules)
- Brownfield work (needs reverse-engineering existing code)
- Runs where you want budget caps, crash recovery, or a parallel reviewer pool

## 2. Start a run

```
/factory-spec "add JWT auth to the API gateway"
```

The orchestrator:
1. **Triages** your request: TINY (Fast Path) or SMALL/MEDIUM/LARGE (full pipeline)
2. **Generates a run-id**
3. **Spawns workspace-scout** to learn your codebase
4. **Spawns requirements-analyst** to write a spec (may ask you questions)

**Fast Path (TINY):** goes directly to code-generator and commits.

## 3. Plan the work

After `/factory-spec`, run `/factory-plan <run-id>`.

Spawns workflow-planner and optionally unit-decomposer.

## 4. Build

```
/factory-build <run-id>
```

Spawns code-generator x N units in parallel waves, then build-test-agent x N.
Enforces file-glob locks, AST drift detection, and budget gates.

## 5. Review

```
/factory-review <run-id>
```

Fans out 4 reviewers in parallel: code-quality, security, performance, simplifier.
Results merged into `aidlc-docs/operations/<run-id>-review-report.md`.

## 6. Ship

```
/factory-ship <run-id>
```

Release notes, ADRs, CHANGELOG update, CI/CD wiring suggestions.

## 7. Recovery

| Situation | Command |
|-----------|---------|
| Run crashed mid-stage | `/factory-resume <run-id>` |
| Stage produced wrong output | `/factory-replay <run-id> --from <stage>` |
| Stale locks | `factory_conflict.py release <run-id> --stale --older-than 120` |
| Model assignment wrong | Edit `.aidlc-orchestrator/budgets/default.yaml` |

## Reference

- `/factory-state <run-id>` — current stage, next step, budget, timeline
- `/factory-help` — quick command reference
- `docs/TROUBLESHOOTING.md` — failure modes and fixes
