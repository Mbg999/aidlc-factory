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
| `.github/agents/orchestrator.md` | Multi-agent orchestrator definition |
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

Add to `.vscode/settings.json` to enable multi-agent orchestration:

```json
{
  "chat.subagents.allowInvocationsFromSubagents": true
}
```

Required for nested subagent spawning (factory orchestrator → stage agents → tools).
Without this, stage agents cannot use their own tools when spawned.

---

## Copilot execution constraints

Copilot differs from Claude Code in two important ways:

### 1. Sequential-only agent calls

Copilot processes one `agent` tool call at a time. The orchestrator MUST:
- Invoke agents sequentially (one at a time, wait for result, then proceed)
- Never attempt to invoke multiple agents in a single response
- Use `agent` tool only — `Task(subagent_type=...)` is Claude Code syntax and will fail

### 2. Spawn budget

Keep total `agent` invocations per command under 8 to avoid context exhaustion:

| Command | Max spawns | Strategy |
|---------|-----------|----------|
| `factory-spec` | 3 | workspace-scout + analyst ×2 (or inline scout for greenfield) |
| `factory-plan` | 2 | workflow-planner + unit-decomposer (skip story-writer unless requested) |
| `factory-build` | 4 units × 3 spawns = 12 max | Cap at 4 units per run; use `merged_plan_generate` for SMALL tier |
| `factory-review` | 1–2 | Default to `reviewer-code` only; add others only when manifest specifies |
| `factory-ship` | 1 | ship-agent only |

**If a `factory-build` run has more than 4 units**, split into multiple invocations or ask the user which units to prioritize.

### 3. Tool availability

Not all tools are available in every Copilot session. Agents MUST handle missing tools gracefully:

- **`engram/*` tools** (`engram/mem_save`, `engram/mem_search`, etc.) are NOT available in Copilot. Skip all Engram operations silently. Log `[Knowledge] DEGRADED: engram unavailable, skipped` at most once per run. Do NOT surface this as a user-facing message or blocker.
- **`edit` tool** is required for all file creation and editing (manifest, handoffs, audit.md, requirements.md, etc.). If missing, the agent cannot proceed — report the missing tool and stop.
- **Terminal execution** is implicit; `read/terminalLastCommand` covers running commands and reading output.

### 4. Reducing spawns

The orchestrator has two inline-execution optimizations available for Copilot:

- **Inline workspace-scout** (greenfield only): If the workspace has no source or manifest files, the orchestrator can perform the scan inline instead of spawning workspace-scout. Log `[Inline] workspace-scout`.
- **Skip story-writer** (default): story-writer is skipped unless the user explicitly requests user stories. Log `[Skipped] story-writer`.

---

## Environment setup

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Installer dry-run
python aidlc-scripts/install_aidlc.py --tool claude --dry-run

# Validate / audit scripts
python3 aidlc-scripts/factory_validate.py
python3 aidlc-scripts/factory_custom_skills.py --dry-run
python3 aidlc-scripts/factory_skill_drift.py --report
```

Env vars: `AIDLC_ROOT` (repo root override), `AIDLC_MODEL_<STAGE>` (per-stage model override).
