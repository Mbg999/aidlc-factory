# AIDLC Development Repo — Claude Code Context

This is a **custom fork** of [AWS AI-DLC](https://github.com/awslabs/aidlc-workflows) (v0.2.0).
It extends the upstream with a multi-agent orchestrator, skills enforcement, hallucination
prevention, CodeGraph integration, and persistent memory (Engram).

> This repo IS the AIDLC toolchain itself. When working here you are modifying the workflow
> engine, not running it against an application codebase.

---

## Directory map

| Path | Purpose |
|------|---------|
| `aidlc-rules/aws-aidlc-rules/core-workflow.md` | Stage workflow rules (read by orchestrator stage agents) |
| `aidlc-rules/aws-aidlc-rule-details/` | Detailed stage rule files (inception / construction / operations / extensions) |
| `.claude/agents/orchestrator.md` | Multi-agent orchestrator (entry point for /factory-* commands) |
| `.claude/agents/stage/` | 13 stage subagents (workspace-scout, requirements-analyst, code-generator, …) |
| `.claude/agents/cross-cutting/` | conflict-resolver, knowledge-agent |
| `.claude/commands/factory-*.md` | Slash command definitions |
| `.aidlc-orchestrator/runtime/` | Runtime architecture docs (index, spawn-loop, fast-path, recovery, …) |
| `.aidlc-orchestrator/contracts/` | JSON Schema handoff contracts for every stage I/O |
| `.aidlc-orchestrator/budgets/default.yaml` | Per-stage model assignments |
| `aidlc-scripts/factory_*.py` | Runtime scripts (run manager, conflict, merge-reviews, validate, telemetry, …) |
| `aidlc-scripts/install_aidlc.py` | Installer — copies rules + agents into target projects |
| `.agents/custom-skills/` | Custom skills shipped with this fork (code-review-and-quality, validator-retry, …) |
| `aidlc-docs/` | Generated artifacts from any AIDLC run executed in this repo |
| `src/` | Source library (memory store, adapters) |
| `tests/` | Test suite |
| `docs/` | Supporting documentation (WORKING-WITH-AIDLC, TROUBLESHOOTING, …) |

---

## Multi-agent orchestrator (Claude Code only)

Activated via `/factory-*` slash commands.
Entry point: `.claude/agents/orchestrator.md`.
Runtime spec: `.aidlc-orchestrator/runtime/index.md`.

| Command | What it does |
|---------|-------------|
| `/factory-spec <feature>` | Workspace scout + requirements analysis (Phase 0) |
| `/factory-plan <run-id>` | Execution plan + optional unit decomposition (Phase 1) |
| `/factory-build <run-id>` | Parallel code-gen + build/test with file-glob locks (Phase 5) |
| `/factory-review <run-id>` | Parallel reviewer pool: code / security / performance / simplifier |
| `/factory-ship <run-id>` | Release notes, ADRs, CHANGELOG, CI/CD wiring |
| `/factory-resume <run-id>` | Resume interrupted run from last completed stage |
| `/factory-replay <run-id> --from <stage>` | Re-run from a specific stage |
| `/factory-state <run-id>` | Show run status, stage, budget |
| `/factory-help` | Full command reference |

Stage execution modes: **Full spawn** (`Task()` + JSON Schema validation) for build/review;
**post-execution inline** for all other stages. See `runtime/spawn-loop.md`.

---

## CodeGraph

`.codegraph/` is initialized in this repo. Rules (from `~/.claude/CLAUDE.md`):

- **Never** call `codegraph_explore` or `codegraph_context` in the main session — they flood context.
- **Always** spawn an `Explore` agent for exploration questions.
- Lightweight tools allowed directly in main session: `codegraph_search`, `codegraph_callers`,
  `codegraph_callees`, `codegraph_impact`, `codegraph_node`.

---

## Skills

Skills enforce quality at every stage. Resolution order (first found wins):

1. `.agents/custom-skills/<name>/SKILL.md` — project-specific (highest priority)
2. `.agents/skills/<name>/SKILL.md` — installed by the installer
3. `~/.agents/skills/<name>/SKILL.md` — user-global fallback

Bundled custom skills: `code-review-and-quality`, `validator-retry`,
`environment-detection`, `codegraph-aware-exploration`.

---

## Key rules when modifying this repo

- **Contracts are the interface**: stage agent I/O is defined by JSON Schema files in
  `.aidlc-orchestrator/contracts/`. Changes to agent outputs must be reflected in contracts.
- **Rule files are the source of truth**: both workflows read the same
  `aidlc-rules/aws-aidlc-rule-details/` corpus. Duplicate logic is a bug.
- **Installer is the distribution mechanism**: any new file added to the orchestrator must
  be wired into `aidlc-scripts/install_aidlc.py` under the correct install flag.
- **Runtime state is gitignored**: `.aidlc-orchestrator/runs/`, `.aidlc-orchestrator/knowledge/`,
  `.codegraph/` — never commit these.
- **Auto-commit fires on explicit approval only** — never on `status: complete` from a stage.
  Approval signals: `approve`, `go ahead`, `continue`, `lgtm`, `dale`, `sí`, etc.

---

## Environment

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Installer dry-run
python aidlc-scripts/install_aidlc.py --tool claude --dry-run

# Run the factory scripts
python3 aidlc-scripts/factory_validate.py
python3 aidlc-scripts/factory_autoskills.py --dry-run
python3 aidlc-scripts/factory_skill_drift.py --report
```

Env vars: `AIDLC_ROOT` (repo root override), `AIDLC_MODEL_<STAGE>` (per-stage model override).

<!-- AIDLC-ORCHESTRATOR-POINTER -->
## AIDLC Orchestrator (multi-agent factory mode)

This project ships with the AIDLC orchestrator:
- `/factory-onboarding`, `/factory-help`, `/factory-state`
- `/factory-spec <feature>` — workspace scout + requirements + plan
- `/factory-plan <run-id>` — decompose plan into per-unit specs
- `/factory-build <run-id>` — layer-parallel code generation with locks + AST checks
- `/factory-review <run-id>` — parallel reviewer pool
- `/factory-ship <run-id>` — release notes, ADRs, CI/CD, CHANGELOG
- `/factory-resume <run-id>` — resume interrupted run from last completed stage
- `/factory-replay <run-id> --from <stage>` — re-run from a specific stage

See `.claude/agents/orchestrator.md`, `.aidlc-orchestrator/runtime/index.md`, `.aidlc-orchestrator/contracts/`.

Keep parity between .opencode/ and .claude/ files, everytime you change anything in one, do the same for the other.