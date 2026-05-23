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
| `.claude/agents/orchestrator.md` | Multi-agent orchestrator (Claude Code only) |
| `.claude/agents/stage/` | 13 stage subagents |
| `.claude/agents/cross-cutting/` | conflict-resolver, knowledge-agent |
| `.claude/commands/factory-*.md` | Factory slash command definitions |
| `.aidlc-orchestrator/runtime/` | Runtime architecture docs |
| `.aidlc-orchestrator/contracts/` | JSON Schema handoff contracts (stage I/O) |
| `.aidlc-orchestrator/budgets/default.yaml` | Per-stage model assignments |
| `aidlc-scripts/factory_*.py` | Runtime Python scripts |
| `aidlc-scripts/install_aidlc.py` | Installer — copies rules + agents into target projects |
| `.agents/custom-skills/` | Custom skills: code-review-and-quality, validator-retry, environment-detection, codegraph-aware-exploration, secret-knowledge |
| `aidlc-docs/` | Generated artifacts from AIDLC runs in this repo |
| `src/` | Source library (memory store, adapters) |
| `tests/` | Test suite |
| `docs/` | Supporting docs (WORKING-WITH-AIDLC, TROUBLESHOOTING) |

---

## Multi-agent orchestrator (Claude Code only)

Uses `/factory-*` slash commands.
See `.claude/agents/orchestrator.md` and `.aidlc-orchestrator/runtime/index.md`.

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