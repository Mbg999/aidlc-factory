# 🏭 AIDLC Orchestrator — Onboarding

This guide walks through the multi-agent factory.

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
1. **Triages** your request: TINY (Fast Path) or full pipeline
2. **Generates a run-id** like `2026-05-12T14-23-00Z-jwt-auth`
3. **Spawns workspace-scout** to learn your codebase
4. **Spawns requirements-analyst** to write a spec

At the end, you get a `run-id`. Keep it for subsequent commands.

## 3. Plan the work

```
/factory-plan <run-id>
```

Spawns:
- **workflow-planner** — designs the execution plan
- **unit-decomposer** — splits into parallel units

## 4. Build

```
/factory-build <run-id>
```

Spawns **code-generator** × N units in parallel, then **build-test-agent** × N.
Enforces file-glob locks, AST drift detection, and budget gates.

## 5. Review

```
/factory-review <run-id>
```

Fans out 4 reviewers: code-quality, security, performance, simplifier.

## 6. Ship

```
/factory-ship <run-id>
```

Release notes, ADRs, CHANGELOG, CI/CD wiring.

## 7. Recovery

| Situation | Command |
|-----------|---------|
| Run crashed | `/factory-resume <run-id>` |
| Wrong output | `/factory-replay <run-id> --from <stage>` |
| Stale locks | `factory_conflict.py release <run-id> --stale --older-than 120` |
| View timeline | `factory_run.py graph <run-id>` |

## 8. Self-hosting

```
/factory-self "add --stale flag to factory_conflict.py release"
```

Runs the pipeline against the orchestrator's own codebase.

## Reference

- `/factory-state <run-id>` — current stage, next step, budget
- `/factory-help` — quick command reference
