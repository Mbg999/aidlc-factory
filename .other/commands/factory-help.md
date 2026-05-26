# AIDLC Orchestrator — Help

Start any new feature with:

```
/factory-spec "<request>"
```

## Full pipeline

```
/factory-spec <request>   →  workspace-scout → requirements-analyst
/factory-plan <run-id>     →  workflow-planner → unit-decomposer
/factory-build <run-id>    →  code-generator × N units + build-test-agent
/factory-review <run-id>   →  4 parallel reviewers → merged report
/factory-ship <run-id>     →  release notes, ADRs, changelog, CI/CD
```

Each command waits for your approval before proceeding.

### Fast Path (TINY tier)

For trivial requests, the orchestrator skips all stages:
```
/factory-spec "fix typo in README"
→ triage: TINY (score 0)
→ code-generator → commit
→ done. No manifest, no audit, no multi-agent overhead.
```

## Command reference

| Command | When to use | What happens |
|---------|-------------|-------------|
| `/factory-onboarding` | First time using the orchestrator | Guided tour of the system |
| `/factory-code-tour` | Onboard to any codebase | Architecture map, key flows |
| `/factory-spec "<request>"` | **Start here** for any new feature | Triages request, spawns scout + analyst |
| `/factory-plan <run-id>` | After `/factory-spec` completes | Creates execution plan |
| `/factory-build <run-id>` | After plan is approved | Generates code + runs tests |
| `/factory-review <run-id>` | After build completes | 4 reviewers analyze code |
| `/factory-ship <run-id>` | After review passes | Release notes, ADRs, changelog |
| `/factory-state <run-id>` | Check progress anytime | Current stage, next step, timeline |
| `/factory-resume <run-id>` | Run crashed mid-flight | Picks up from last completed stage |
| `/factory-replay <run-id> --from <stage>` | Wrong output | Rolls back and re-runs |
| `/factory-self "<task>"` | Improve the orchestrator | Runs pipeline against own code |
| `/factory-help [command]` | Remember a command | This page |

## Monitoring

```bash
python3 aidlc-scripts/factory_run.py graph <run-id>
python3 aidlc-scripts/factory_run.py status <run-id> --latency
python3 aidlc-scripts/factory_run.py tail <run-id> --follow
```

## Recovery

| Situation | Solution |
|-----------|----------|
| Run crashed | `/factory-resume <run-id>` |
| Wrong output | `/factory-replay <run-id> --from <stage>` |
| Stale locks | `factory_conflict.py release <run-id> --stale --older-than 120` |
| Need to see what happened | `factory_run.py timeline <run-id> --follow` |

## CLI tools

```bash
python3 aidlc-scripts/factory_triage.py "add healthz" --dry-run
python3 aidlc-scripts/factory_validate.py schema.json doc.yaml --strict
python3 aidlc-scripts/factory_secretscan.py handoff.yaml
```
