# AIDLC Development Repo — Agent Context

This is a **custom fork** of [AWS AI-DLC](https://github.com/awslabs/aidlc-workflows) (v0.2.0).
It extends the upstream with a multi-agent orchestrator, skills enforcement, hallucination
prevention, CodeGraph integration, and persistent memory (Engram).

> This repo IS the AIDLC toolchain itself. When working here you are modifying the workflow
> engine, not running it against an application codebase.

---

## What AIDLC is

AI-DLC (AI-Driven Development Life Cycle) is a methodology + toolchain that guides AI coding
agents through three phases: **Inception** (WHAT to build), **Construction** (HOW to build it),
and **Operations** (deployment/monitoring). It is tool-agnostic by design — the same rule corpus
works in Cursor, Cline, GitHub Copilot, Amazon Q, and Claude Code.

---

## Directory map

| Path | Purpose |
|------|---------|
| `aidlc-rules/aws-aidlc-rules/core-workflow.md` | Stage workflow rules (read by orchestrator stage agents) |
| `aidlc-rules/aws-aidlc-rule-details/` | Stage rule details (inception / construction / operations / common / extensions) |
| `.claude/agents/orchestrator.md` | Multi-agent orchestrator (entry point for /factory-* commands) |
| `.claude/agents/stage/` | 13 stage subagents (workspace-scout, requirements-analyst, code-generator, …) |
| `.claude/agents/cross-cutting/` | conflict-resolver, knowledge-agent |
| `.claude/commands/factory-*.md` | Factory slash command definitions |
| `.aidlc-orchestrator/runtime/` | Runtime architecture docs (index, spawn-loop, fast-path, recovery, …) |
| `.aidlc-orchestrator/contracts/` | JSON Schema handoff contracts for every stage I/O |
| `.aidlc-orchestrator/budgets/default.yaml` | Per-stage model assignments |
| `aidlc-scripts/factory_*.py` | Runtime Python scripts (run manager, conflict, merge-reviews, validate, telemetry, incl. stitch_snap, stitch_mcp, …) |
| `aidlc-scripts/install_aidlc.py` | Installer — copies rules + agents into target projects |
| `.agents/custom-skills/` | Custom skills shipped with this fork (code-review-and-quality, validator-retry, secret-knowledge, …) |
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

CodeGraph builds a semantic knowledge graph of codebases for faster, smarter code exploration.

### If `.codegraph/` exists in the project

**NEVER call `codegraph_explore` or `codegraph_context` directly in the main session.** These tools return large amounts of source code that fills up main session context. Instead, ALWAYS spawn an Explore agent for any exploration question (e.g., "how does X work?", "explain the Y system", "where is Z implemented?").

**When spawning Explore agents**, include this instruction in the prompt:

> This project has CodeGraph initialized (.codegraph/ exists). Use `codegraph_explore` as your PRIMARY tool — it returns full source code sections from all relevant files in one call.
>
> **Rules:**
> 1. Follow the explore call budget in the `codegraph_explore` tool description — it scales automatically based on project size.
> 2. Do NOT re-read files that codegraph_explore already returned source code for. The source sections are complete and authoritative.
> 3. Only fall back to grep/glob/read for files listed under "Additional relevant files" if you need more detail, or if codegraph returned no results.

**The main session may only use these lightweight tools directly** (for targeted lookups before making edits, not for exploration):

| Tool | Use For |
|------|---------|
| `codegraph_search` | Find symbols by name |
| `codegraph_callers` / `codegraph_callees` | Trace call flow |
| `codegraph_impact` | Check what's affected before editing |
| `codegraph_node` | Get a single symbol's details |

### If `.codegraph/` does NOT exist

At the start of a session, ask the user if they'd like to initialize CodeGraph:

"I notice this project doesn't have CodeGraph initialized. Would you like me to run `codegraph init -i` to build a code knowledge graph?"

---

## Skills system

Skills enforce engineering quality at every stage. Resolution order (first found wins):

1. `.agents/custom-skills/<name>/SKILL.md`
2. `.agents/skills/<name>/SKILL.md`
3. `~/.agents/skills/<name>/SKILL.md`

Bundled custom skills in this fork:
- `code-review-and-quality` — linting, building, and five-axis review
- `validator-retry` — static type/lint validation with compile-error-feedback loop
- `environment-detection` — detect runtimes before installing
- `codegraph-aware-exploration` — routes exploration to CodeGraph MCP tools
- `design-system-composer` — composes UI from approved primitives, enforces tokens (Figma + Stitch)
- `ui-constraint-validator` — validates hardcoded spacing/radius/typography/color against tokens

---

## Key rules when modifying this repo

- **Contracts are the interface**: stage I/O is defined by JSON Schema in
  `.aidlc-orchestrator/contracts/`. Agent output changes must be reflected in contracts.
- **Rule files are the source of truth**: stage agents read `aidlc-rules/aws-aidlc-rule-details/`. No duplicate logic between rule files and agent prompts.
- **Installer is distribution**: new orchestrator files must be wired into
  `aidlc-scripts/install_aidlc.py` under the correct flag (`--with-orchestrator`,
  `--with-codegraph`, etc.).
- **Runtime state is gitignored**: `.aidlc-orchestrator/runs/`, `.aidlc-orchestrator/knowledge/`,
  `.codegraph/` — never commit these.
- **Auto-commit fires on explicit approval only** — approval signals: `approve`, `go ahead`,
  `continue`, `lgtm`, `dale`, `sí`, or equivalent. Never on `status: complete` alone.

---

## Environment setup

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

Key env vars:
- `AIDLC_ROOT` — override repo root path for factory scripts
- `AIDLC_MODEL_<STAGE>` — override model per stage (e.g. `AIDLC_MODEL_CODE_GENERATOR=haiku`)

---

## Hallucination prevention stack

| Piece | Mechanism |
|-------|-----------|
| Validator-retry | `tsc --noEmit` / `pyright` / `cargo check` after each code slice; feeds errors back (max 3 retries) |
| Lockfile-aware skills | `workspace-scout` parses lockfiles; only injects skills matching pinned versions |
| Autoskills | `factory_custom_skills.py` fetches community skills with SHA-256 verification |
| Skill drift detector | `factory_skill_drift.py` flags skills whose version range no longer covers latest stable |

---

## Extensions

Extensions layer additional rules on top of the core workflow. Opt-in files live in
`aidlc-rules/aws-aidlc-rule-details/extensions/`. Each extension has a `*.opt-in.md`
(presented during Requirements Analysis) and a rules file (loaded when user opts in).
Extensions without an opt-in file are always enforced.


Keep parity between .opencode/, .cursor, .github and .claude/ files, everytime you change anything in one, do the same for the other.
Skills provide specialized instructions and workflows for specific tasks.
Use the skill tool to load a skill when a task matches its description.
