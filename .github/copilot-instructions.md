# AIDLC Development Repo

Custom fork of [AWS AI-DLC](https://github.com/awslabs/aidlc-workflows) (v0.2.0).
Extends upstream with a multi-agent orchestrator, skills enforcement, hallucination
prevention, CodeGraph integration, and persistent memory (Engram).

> This repo IS the AIDLC toolchain itself. Modifying it means modifying the workflow engine,
> not running it against an application codebase.

---

## Directory map

| Path | Purpose |
|------|---------|
| `aidlc-rules/aws-aidlc-rules/core-workflow.md` | Stage workflow rules |
| `aidlc-rules/aws-aidlc-rule-details/` | Detailed stage rule files (inception / construction / operations / extensions) |
| `.github/skills/orchestrator.md` | Multi-agent orchestrator definition |
| `.github/skills/` | All stage agents + custom skills (22 total) |
| `.claude/commands/factory-*.md` | Slash command definitions (Claude Code / OpenCode) |
| `.aidlc-orchestrator/runtime/` | Runtime architecture docs |
| `.aidlc-orchestrator/contracts/` | JSON Schema handoff contracts for every stage I/O |
| `.aidlc-orchestrator/budgets/default.yaml` | Per-stage model assignments |
| `aidlc-scripts/factory_*.py` | Runtime scripts (run manager, conflict, merge-reviews, validate, telemetry) |
| `aidlc-scripts/install_aidlc.py` | Installer — copies rules + agents into target projects |
| `.agents/custom-skills/` | Custom skills (code-review-and-quality, validator-retry, …) |
| `aidlc-docs/` | Generated artifacts from AIDLC runs |
| `src/` | Source library (memory store, adapters) |
| `tests/` | Test suite |
| `docs/` | Supporting documentation (WORKING-WITH-AIDLC, TROUBLESHOOTING) |

---

## Multi-agent orchestrator

The orchestrator routes development requests through specialized stage agents using
JSON Schema handoff contracts. Stage agents own domain cognition; the orchestrator
owns the state machine.

| Command / Phase | What it does |
|-----------------|-------------|
| `factory-spec` | Workspace scout + requirements analysis (Phase 0) |
| `factory-plan` | Execution plan + optional unit decomposition (Phase 1) |
| `factory-build` | Parallel code-gen + build/test with file-glob locks (Phase 5) |
| `factory-review` | Parallel reviewer pool: code / security / performance / simplifier |
| `factory-ship` | Release notes, ADRs, CHANGELOG, CI/CD wiring |
| `factory-resume` | Resume interrupted run from last checkpoint |
| `factory-replay` | Re-run from a specific stage |
| `factory-state` | Show run status, stage, budget |

All agent definitions are in `.github/skills/`. Runtime spec: `.aidlc-orchestrator/runtime/index.md`.

---

## Key rules when modifying this repo

- **Contracts are the interface**: stage agent I/O defined by JSON Schema in `.aidlc-orchestrator/contracts/`. Changes to agent outputs must update contracts.
- **Rule files are source of truth**: `aidlc-rules/aws-aidlc-rule-details/` is the corpus. Duplicate logic is a bug.
- **Installer is the distribution mechanism**: new orchestrator files must be wired into `aidlc-scripts/install_aidlc.py`.
- **Runtime state is gitignored**: `.aidlc-orchestrator/runs/`, `.aidlc-orchestrator/knowledge/`, `.codegraph/` — never commit these.

---

## VS Code Copilot setup

Add to `.vscode/settings.json` to enable full multi-agent orchestration:

```json
{
  "chat.subagents.allowInvocationsFromSubagents": true
}
```

Required for nested subagent spawning (factory orchestrator → stage agents → tools).
Without this, stage agents cannot use their own tools when spawned.

---

## Environment setup

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Installer dry-run
python aidlc-scripts/install_aidlc.py --tool claude --dry-run

# Validate / audit scripts
python3 aidlc-scripts/factory_validate.py
python3 aidlc-scripts/factory_autoskills.py --dry-run
python3 aidlc-scripts/factory_skill_drift.py --report
```

Env vars: `AIDLC_ROOT` (repo root override), `AIDLC_MODEL_<STAGE>` (per-stage model override).
