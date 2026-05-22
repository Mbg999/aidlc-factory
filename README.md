# AIDLC — AI-Driven Development Life Cycle

A multi-agent software-development workflow that takes a feature request from
specification → plan → code → review → ship, with human approval gates between
every stage and traceable artifacts at every step.

> [!IMPORTANT]
> Generative AI can make mistakes. Review every AI-generated artifact and
> associated cost before approving a stage.

This repository has its base in **[AWS Labs aidlc-workflows](https://github.com/awslabs/aidlc-workflows)**
(v0.2.0) that adds a multi-agent orchestrator, a skills enforcement layer,
hallucination prevention, CodeGraph integration, persistent memory, and a
contract-validated stage pipeline. The upstream rules remain unchanged; all
extensions live in new files.

---

## Table of Contents

- [Quick Start](#quick-start)
- [What This Is](#what-this-is)
- [Third-Party Components](#third-party-components)
- [Slash Commands Reference](#slash-commands-reference)
- [Installation](#installation)
- [Repository Layout](#repository-layout)
- [Adding Custom Skills](#adding-custom-skills)
- [Adding Custom Agents](#adding-custom-agents)
- [Configuration](#configuration)
- [Keeping the Fork in Sync with Upstream](#keeping-the-fork-in-sync-with-upstream)
- [Troubleshooting](#troubleshooting)
- [License](#license)

---

## Quick Start

```bash
# 1. Clone and enter the repo
git clone <this-fork-url>
cd <repo>

# 2. Install AIDLC into your target project (Claude Code recommended)
python3 aidlc-scripts/install_aidlc.py \
    --tool claude \
    --dest /path/to/your/project \
    --with-agent-skills \
    --with-codegraph \
    --with-engram

# 3. In your project, start an AIDLC run
cd /path/to/your/project
# Inside Claude Code:
/factory-spec "Build a user authentication service with JWT"
```

The orchestrator will walk you through:
**Spec → Plan → Code → Review → Ship**, halting at each approval gate.

---

## What This Is

The orchestrator is activated through `/factory-*` slash commands and executes
**13 specialized stage subagents** with:

- **Contract-validated handoffs** — every stage input/output is JSON-Schema-validated against `.aidlc-orchestrator/contracts/*.v1.json`.
- **Parallel-safe codegen** — layered units run in parallel with file-glob locks and Python AST symbol-drift detection.
- **Parallel reviewer pool** — code / security / performance / simplifier reviewers run concurrently.
- **Persistent memory** — Engram captures decisions, ADRs, and conventions across sessions.
- **Codebase intelligence** — CodeGraph provides a semantic knowledge graph for impact analysis and dead-code detection.
- **Skills enforcement** — engineering process skills (testing, security, ADRs, etc.) are auto-attached per stage.
- **Auto-commit on approval** — explicit user approvals trigger git commits with stage-tagged messages.
- **Kill & resume** — interrupted runs resume from the last completed stage.

The legacy single-agent AIDLC workflow from upstream still works on every supported tool.
The multi-agent orchestrator is **Claude Code only** (it relies on the `Task()`
spawn primitive); other tools fall back to the legacy flow automatically.

---

## Third-Party Components

This fork integrates several upstream and external projects. All are **opt-in**
at install time.

| Component | Source | What it provides | How it's installed |
|---|---|---|---|
| **AWS Labs AI-DLC** | [awslabs/aidlc-workflows](https://github.com/awslabs/aidlc-workflows) v0.2.0 | Core workflow rules in `aidlc-rules/` — the spec → plan → code → review → ship pipeline that this fork extends | Bundled in `aidlc-rules/` |
| **Agent Skills** | [addyosmani/agent-skills](https://github.com/addyosmani/agent-skills) | Engineering-process skills (TDD, security, ADRs, deprecation, performance, etc.) auto-attached per stage | `--with-agent-skills` (default on) |
| **CodeGraph MCP** | [@colbymchenry/codegraph](https://www.npmjs.com/package/@colbymchenry/codegraph) (npm) | Local semantic code knowledge graph + MCP tools (`codegraph_search`, `codegraph_callers`, `codegraph_impact`, etc.) for 92% fewer tool calls and 71% faster context retrieval | `--with-codegraph` (requires Node ≥ 18) |
| **Engram** | Local persistent memory (MCP) | Cross-session memory: decisions, conventions, bug fixes, discoveries. Used by stage agents via `mem_save`, `mem_search`, etc. | `--with-engram` |
| **Claude Code** | Anthropic CLI / IDE extension | The harness for the multi-agent orchestrator. The `Task()` primitive backs every stage spawn. | User-installed; the installer wires `.claude/` configuration |
| **Custom Skills (this fork)** | `.agents/custom-skills/` | 21 project-specific skills: `validator-retry`, `codegraph-aware-exploration`, `secret-knowledge`, `design-system-composer`, etc. | Bundled, copied automatically when the orchestrator is installed |
| **Design System (optional)** | `design-system/` + `design-system-composer` skill | Token-driven UI composition with hardcoded-value detection | `--with-design-system` (default on for UI projects) |

> Every external dependency degrades gracefully. The orchestrator still runs
> if CodeGraph or Engram is missing — those stages just lose the corresponding
> intelligence.

---

## Slash Commands Reference

All commands are invoked inside Claude Code. They live in `.claude/commands/`
and route through the orchestrator agent at `.claude/agents/orchestrator.md`.

| Command | Phase | What it does |
|---|---|---|
| `/factory-onboarding` | Setup | Interactive walkthrough of the AIDLC orchestrator. Recommended first command for new users. |
| `/factory-help` | Setup | Full command reference and getting-started instructions. |
| `/factory-spec <feature>` | 0. Inception | Workspace detection + adaptive requirements analysis (two-pass — Q&A → spec). Produces `aidlc-docs/<run-id>-requirements.md`. |
| `/factory-plan <run-id>` | 1. Planning | Generates the execution plan, optional user stories/personas, and per-unit decomposition. |
| `/factory-product <feature>` | 0–1. Product | Combined run: workspace scout + requirements + personas + stories + execution plan. **Stops before code generation.** Useful for product-only iterations. |
| `/factory-build <run-id>` | 5. Construction | Per-unit code generation + build/test. Layer-parallel (independent units run concurrently, layers sequential). Includes file-glob locks and AST symbol-drift checks. |
| `/factory-review <run-id>` | 4. Review | Spawns the parallel reviewer pool: code quality, security, performance, simplification. Merges findings into a single report. |
| `/factory-ship <run-id>` | 6. Ship | Release notes, ADRs, CHANGELOG, version proposal, optional CI/CD wiring, deprecation/migration plan. |
| `/factory-state <run-id>` | Utility | Show run status: completed stages, current stage, next steps, budget, any blocking issues. |
| `/factory-resume <run-id>` | Recovery | Resume an interrupted run from its last checkpoint. |
| `/factory-replay <run-id> --from <stage>` | Recovery | Re-run from a specific stage. Rolls the manifest back and archives prior output handoffs. |
| `/factory-code-tour` | Exploration | Dependency-ordered tour of an unfamiliar codebase: foundations → entry points. |
| `/factory-self` | Meta | Run the AIDLC orchestrator **on its own codebase**. Use this to add features, fix bugs, or refactor the orchestrator scripts themselves. |

A complete spec → ship sequence typically looks like:

```
/factory-spec "<feature>"        → review + approve requirements
/factory-plan   <run-id>          → review + approve execution plan
/factory-build  <run-id>          → review + approve per-unit code
/factory-review <run-id>          → review + approve findings, apply fixes
/factory-ship   <run-id>          → release notes + ADRs
```

---

## Installation

### Prerequisites

- **Python 3.10+** (a `.venv` is created automatically by the installer)
- **Git** (auto-commit on approval requires a git repo in the destination)
- **Node ≥ 18** — only if installing CodeGraph (`--with-codegraph`)
- **Claude Code** — required for the multi-agent orchestrator. Other tools (Kiro, Cursor, Cline, Amazon Q, GitHub Copilot, OpenCode, Codex, Windsurf) fall back to the legacy single-agent flow.

### One-line install

```bash
python3 aidlc-scripts/install_aidlc.py \
    --tool claude \
    --dest /path/to/your/project \
    --with-agent-skills \
    --with-codegraph \
    --with-engram \
    --yes
```

### Installer flags

| Flag | Default | What it controls |
|---|---|---|
| `--tool <name>` | required | `kiro`, `amazonq`, `cursor`, `cline`, `claude`, `copilot`, `opencode`, `codex`, `windsurf`, `other`. Comma-separate for multiple. |
| `--dest <path>` | `.` (cwd) | Project to install into. |
| `--source <path>` | packaged | Override the rules source (advanced). |
| `--with-agent-skills` | on | Install the 19 engineering-process skills from `addyosmani/agent-skills`. |
| `--agent-skills-path <path>` | — | Use a local clone instead of cloning fresh. |
| `--custom-skills-path <path>` | — | Add project-specific skills. Each subdirectory needs a `SKILL.md`. Overrides agent-skills with the same name. |
| `--with-orchestrator` / `--no-orchestrator` | prompt | Install the multi-agent orchestrator (Claude Code only effective). |
| `--with-codegraph` | off | Install CodeGraph npm package + write `.mcp.json`. |
| `--with-engram` | off | Set up Engram persistent memory. CLI tools get the tool-specific command; MCP tools get an `.mcp.json` entry. |
| `--with-design-system` | on | Install design-system tokens + UI skills. |
| `--force` | off | Re-install / upgrade. Overwrites orchestrator files; preserves run state (`runs/`, `knowledge/`). |
| `--no-venv` | off | Skip creating `.venv` and installing `requirements.txt`. |
| `--dry-run` | off | Print planned actions without writing files. |
| `--yes` | off | Skip all interactive prompts. |

### What gets installed (Claude Code path)

```
<project>/
├── aidlc-rules/                       # Upstream AWS AIDLC workflow rules
├── .agents/skills/                    # Engineering skills (agent-skills + custom)
├── .claude/
│   ├── agents/
│   │   ├── orchestrator.md            # Multi-agent orchestrator entry point
│   │   ├── stage/                     # 13 stage subagents
│   │   ├── cross-cutting/             # conflict-resolver, knowledge-agent
│   │   └── custom/                    # Your custom agents (commit to repo)
│   └── commands/                      # 13 /factory-* slash commands
├── .aidlc-orchestrator/
│   ├── runtime/                       # Runtime architecture docs
│   ├── contracts/                     # JSON Schema handoff contracts
│   ├── budgets/default.yaml           # Per-stage model assignments
│   ├── runs/                          # Per-run state (gitignored)
│   └── knowledge/                     # Project-scoped knowledge store (gitignored)
├── aidlc-scripts/
│   ├── install_aidlc.py               # The installer itself
│   ├── factory_run.py                 # Run manager (manifest + timeline)
│   ├── factory_conflict.py            # File-glob lock + AST drift detection
│   ├── factory_merge_reviews.py       # Reviewer pool merger
│   ├── factory_validate.py            # Handoff contract validator
│   └── factory_*.py                   # ~33 runtime scripts
├── .codegraph/                        # CodeGraph index (gitignored, regenerated)
├── .mcp.json                          # MCP server registrations (codegraph, engram)
├── CLAUDE.md                          # Project instructions (with /factory-* pointers)
└── .venv/                             # Python virtual environment
```

### Verify the install

```bash
# Check orchestrator is wired
python3 aidlc-scripts/factory_validate.py

# List discovered agents (built-in + custom)
python3 aidlc-scripts/factory_agent_discover.py list

# Verify autoskills resolver
python3 aidlc-scripts/factory_autoskills.py --dry-run

# In Claude Code:
/factory-help
/factory-onboarding
```

---

## Repository Layout

| Path | Purpose |
|---|---|
| `aidlc-rules/aws-aidlc-rules/core-workflow.md` | Stage workflow rules read by all stage agents |
| `aidlc-rules/aws-aidlc-rule-details/` | Detailed per-stage rules (inception / construction / operations / extensions) |
| `aidlc-rules/adapters/` | Tool-specific adapter docs (Claude Code, Cursor, Copilot, Cline, generic) |
| `.claude/agents/orchestrator.md` | Multi-agent orchestrator entry point |
| `.claude/agents/stage/` | 13 stage subagents (workspace-scout, requirements-analyst, workflow-planner, story-writer, unit-decomposer, code-generator, build-test-agent, reviewer-{code,security,performance,simplifier}, ship-agent, reverse-engineer) |
| `.claude/agents/cross-cutting/` | `conflict-resolver`, `knowledge-agent` |
| `.claude/agents/custom/` | Your custom subagents (auto-discovered) |
| `.claude/commands/` | 13 `/factory-*` slash command definitions |
| `.aidlc-orchestrator/runtime/` | Architecture docs (`index.md`, `spawn-loop.md`, `fast-path.md`, `recovery.md`, etc.) |
| `.aidlc-orchestrator/contracts/` | JSON Schema input/output handoffs per stage |
| `.aidlc-orchestrator/budgets/default.yaml` | Per-stage model assignments (haiku / sonnet / opus) |
| `.agents/custom-skills/` | 21 fork-specific skills (highest priority in skill resolution) |
| `aidlc-scripts/` | ~33 runtime Python scripts (`factory_*.py`) + the installer |
| `aidlc-scripts/executors/` | Executor adapter implementations per the `executor.v1` contract |
| `aidlc-docs/` | Generated artifacts from AIDLC runs |
| `tests/` | Pytest suite (543 tests at time of writing) |

---

## Adding Custom Skills

A **skill** is a reusable, scoped instruction set that stage agents auto-attach.
Examples: enforce TDD, run a specific linter, follow a security checklist,
validate design tokens.

### Resolution order

When a stage requests a skill, the resolver checks (first found wins):

1. `.agents/custom-skills/<name>/SKILL.md` — project-specific (highest priority)
2. `.agents/skills/<name>/SKILL.md` — installed via `--with-agent-skills`
3. `~/.agents/skills/<name>/SKILL.md` — user-global fallback

### Built-in custom skills (this fork)

| Skill | What it does |
|---|---|
| `code-review-and-quality` | Multi-axis code review with auto-fix and build |
| `validator-retry` | Static type/lint validator with compile-error feedback retry loop — eliminates hallucinated APIs |
| `codegraph-aware-exploration` | Prefer `codegraph_*` MCP tools over grep/glob when `.codegraph/` exists |
| `design-system-composer` | Compose UIs from `INDEX.md` primitives; never invent tokens |
| `ui-constraint-validator` | Scan generated UI for hardcoded values and snap to design tokens |
| `environment-detection` | Detect-before-install discipline for runtimes and package managers |
| `requirements-intelligence` | Adaptive elicitation engine for the Requirements Analyst stage |
| `secret-knowledge` | Curated reference catalog of CLI tools, security toolkits, one-liners |
| `security-and-hardening` | OWASP-aware security review patterns |
| `performance-optimization` | Hot-path analysis, allocation review, complexity checks |
| `test-driven-development` | TDD enforcement: tests first, then code |
| `documentation-and-adrs` | ADR templates + documentation conventions |
| `shipping-and-launch` | Release notes, CHANGELOG, version-bump rules |
| `deprecation-and-migration` | Safe deprecation patterns + migration plans |
| `debugging-and-error-recovery` | Recovery patterns for failed stages |
| `git-workflow-and-versioning` | Conventional commits, branch strategy, rebase rules |
| `ci-cd-and-automation` | CI/CD pipeline patterns |
| `code-simplification` | Anti-over-engineering review patterns |
| `spec-driven-development` | Spec-first methodology |
| `planning-and-task-breakdown` | Decomposition heuristics |
| `browser-testing-with-devtools` | Chrome DevTools MCP patterns |

### Create a new custom skill

```bash
mkdir -p .agents/custom-skills/my-skill
cat > .agents/custom-skills/my-skill/SKILL.md <<'EOF'
---
name: my-skill
description: One-line description used by the resolver to match relevance.
type: process
---

# My Skill

## When to use
- Trigger condition 1
- Trigger condition 2

## How to apply
1. Step one
2. Step two

## Reference
- Link to internal doc or external standard
EOF
```

The skill is picked up automatically on the next stage run. To verify:

```bash
python3 aidlc-scripts/factory_autoskills.py --dry-run | grep my-skill
```

### Commit custom skills to the repo

```gitignore
# In .gitignore — keep these committed
!.agents/custom-skills/
```

---

## Adding Custom Agents

Custom agents are subagents the orchestrator can spawn alongside the built-in
stages. Examples: lint auditor, compliance reviewer, legal-doc checker,
performance profiler.

### Create a custom agent

```bash
mkdir -p .claude/agents/custom
cat > .claude/agents/custom/my-agent.md <<'EOF'
---
description: One-line description of what the agent does.
model: sonnet
---

# My Custom Agent

## Role
Describe the agent's responsibility.

## Inputs
- What it reads from the input handoff.

## Outputs
- What it writes to the output handoff.

## Process
1. Step one
2. Step two
EOF
```

The filename (without `.md`) becomes the agent name. Frontmatter requirements
differ per platform:

- **Claude Code:** `description`, `model` (`haiku` / `sonnet` / `opus`)
- **OpenCode:** add `mode: subagent` and a `permission` block
- **Cursor:** `model: inherit`, plus `readonly` / `is_background` flags

### Discover and invoke

```bash
# List all discovered agents (built-in + custom)
python3 aidlc-scripts/factory_agent_discover.py list

# Show one agent's metadata
python3 aidlc-scripts/factory_agent_discover.py show my-agent
```

Inside the orchestrator, the agent is spawned with generic contracts at
`.aidlc-orchestrator/contracts/custom-agent.input.v1.json` and
`custom-agent.output.v1.json`:

```python
Task(subagent_type="custom/my-agent", prompt="<input-handoff-yaml-path>")
```

### Default model assignment

Custom agents default to `sonnet` (configured in `.aidlc-orchestrator/budgets/default.yaml`
under the `custom-agent` key). Override per-agent by adding an explicit entry.

### Built-in custom agent example

`lint-audit` ships in `.claude/agents/custom/` — it runs the project's linter
and reports violations without modifying files. Use it as a template.

### Commit custom agents to the repo

```gitignore
# In .gitignore — keep these committed
!.claude/agents/custom/
!.opencode/agents/custom/
```

---

## Configuration

### Environment variables

| Variable | Purpose | Example |
|---|---|---|
| `AIDLC_ROOT` | Override the repo root used by factory scripts. Defaults to the parent of `aidlc-scripts/`. | `AIDLC_ROOT=/path/to/repo python3 aidlc-scripts/factory_validate.py` |
| `AIDLC_MODEL_<STAGE>` | Override the model for a specific stage. Uppercase stage name with dashes → underscores. | `AIDLC_MODEL_CODE_GENERATOR=opus` |

### Per-stage model assignments

Edit `.aidlc-orchestrator/budgets/default.yaml`:

```yaml
stages:
  workspace-scout:        haiku
  requirements-analyst:   opus     # Two-pass; needs deep reasoning
  workflow-planner:       opus
  story-writer:           sonnet
  unit-decomposer:        sonnet
  code-generator:         opus
  build-test-agent:       sonnet
  reviewer-code:          sonnet
  reviewer-security:      opus     # Security misses become incidents
  reviewer-performance:   sonnet
  reviewer-simplifier:    sonnet
  ship-agent:             sonnet
  custom-agent:           sonnet   # Default for custom agents
```

### Auto-commit on approval

When the user explicitly approves a stage (signals: `approve`, `go ahead`,
`continue`, `lgtm`, `dale`, `sí`, etc.), the orchestrator stages and commits
the produced artifacts with a stage-tagged message. Commits never fire on a
stage's internal `status: complete` — only on explicit user approval.

To opt out, remove the `auto_commit_on_approval: true` line from
`.aidlc-orchestrator/runtime/run-manager.md`.

---

## Keeping the Fork in Sync with Upstream

To pull new releases from AWS Labs upstream while keeping this fork's
extensions:

```bash
# One-time setup
git remote add upstream https://github.com/awslabs/aidlc-workflows

# Pull upstream changes
git fetch upstream
git merge upstream/main
git push origin main
```

The merge will only touch `aidlc-rules/` (upstream-owned). Conflicts in
fork-specific paths (`.claude/`, `.aidlc-orchestrator/`, `aidlc-scripts/`,
`.agents/custom-skills/`) shouldn't occur — upstream doesn't ship those.

---

## Troubleshooting

### `python3 -m pytest` returns "No tests collected"

A shell wrapper may be intercepting `python3`. Invoke the venv binary directly:

```bash
./.venv/bin/python -m pytest tests/
```

### CodeGraph tools time out or return "index not ready"

```bash
# Re-index the workspace
codegraph init -i

# Verify status
codegraph_status   # via MCP inside the agent
```

### `/factory-resume` says "no run to resume"

Runs are stored in `.aidlc-orchestrator/runs/<run-id>/manifest.yaml`. List them:

```bash
ls .aidlc-orchestrator/runs/
python3 aidlc-scripts/factory_run.py list
```

### Stage spawn fails with "contract validation failed"

The stage produced an output handoff that doesn't validate against its
`.v1.json` schema. Read the validator output, then either:

- Re-run the stage: `/factory-replay <run-id> --from <stage>`
- Edit the output handoff manually and re-validate: `python3 aidlc-scripts/factory_validate.py <run-id>`

### Skill not being applied

Check resolution order and the autoskills resolver:

```bash
python3 aidlc-scripts/factory_autoskills.py --dry-run
python3 aidlc-scripts/factory_skill_drift.py --report
```

### Engram memory tools not found

```bash
# Reinstall with --with-engram
python3 aidlc-scripts/install_aidlc.py --tool claude --dest . --with-engram --force
```

---

## License

This library is licensed under the MIT-0 License. See [LICENSE](LICENSE).

The upstream [AWS Labs aidlc-workflows](https://github.com/awslabs/aidlc-workflows)
core rules retain their original MIT-0 license. Third-party components
([`agent-skills`](https://github.com/addyosmani/agent-skills),
[`codegraph`](https://www.npmjs.com/package/@colbymchenry/codegraph), Engram)
are governed by their respective upstream licenses.
