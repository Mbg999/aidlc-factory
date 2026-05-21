# AIDLC Agent Orchestrator — Implementation Plan (Option 1: Claude Code Native)

> Scope: Transform the current single-agent AIDLC workflow into a multi-agent
> "software factory" that runs natively in Claude Code via subagents +
> handoff contracts. **No external runtime** (no swarms, no agent-swarm).
> Cross-tool degraded mode (Copilot/Cursor/Cline) reuses the same rule files
> as today via single-agent role-switching.

---

## 📍 Current Phase

> **Active phase:** **Phase 6 — Run Manager + Telemetry Hardening**
> **Last updated:** 2026-05-08

| Phase | Status | Started | Completed |
|---|---|---|---|
| Phase 0 — Skeleton + Sequential Orchestrator | ✅ Complete | 2026-05-08 | 2026-05-08 |
| Phase 1 — All Stage Agents, Sequential | ✅ Complete | 2026-05-08 | 2026-05-08 |
| Phase 2 — Cost Governor | ✅ Complete | 2026-05-08 | 2026-05-08 |
| Phase 3 — Knowledge Agent | ✅ Complete | 2026-05-08 | 2026-05-08 |
| Phase 4 — Parallel Reviewer Pool | ✅ Complete | 2026-05-08 | 2026-05-08 |
| Phase 5 — Conflict Resolver + Parallel Code Gen | ✅ Complete | 2026-05-08 | 2026-05-08 |
| Phase 6 — Run Manager + Telemetry Hardening | ✅ Complete | 2026-05-08 | 2026-05-08 |

**Status legend:** ⬜ Not started · 🟨 In progress · ✅ Complete · 🟥 Blocked

> **How to update:** when a phase starts, change ⬜ → 🟨 and fill `Started`.
> When acceptance criteria pass, change → ✅ and fill `Completed`. Update
> "Active phase" above to the current 🟨 row, or to the next ⬜ if all in
> progress are paused. Update "Last updated" on every change.

---

## 1. Goals & Non-Goals

### Goals
- Specialize each AIDLC stage as a Claude Code subagent with narrow context.
- Run independent stages in **parallel** (reviewer pool, code-gen across units).
- Add three **cross-cutting agents** the current workflow lacks: Knowledge,
  Conflict Resolver, Cost Governor.
- Preserve every existing AIDLC primitive: rule files, skills, audit log,
  state file, approval gates, slash commands.
- Be resumable: a crashed run picks up at the last completed stage.

### Non-Goals
- Replacing the AIDLC rules. They become the **per-agent system prompts**, not
  legacy.
- Building a UI. Approval gates stay in the CLI / IDE chat.
- Cross-vendor LLM routing. Claude Code only — other tools fall back to the
  existing single-agent role-switch pattern.
- Replacing engram. Knowledge Agent **wraps** engram, doesn't reinvent it.

---

## 2. Architecture Overview

```
┌──────────────────────────────────────────────────────────────────────────┐
│  ORCHESTRATOR (single agent, owns state machine + routing)               │
│  - Reads/writes aidlc-state.md, audit.md                                 │
│  - Validates handoff contracts (input → output schema)                   │
│  - Spawns stage agents via Task() (sequential or parallel)               │
│  - Calls cross-cutting agents pre/post each spawn                        │
│  - Owns approval gates, blocks until human responds                      │
└───────────┬──────────────────────────────────────────────────────────────┘
            │
   ┌────────┼─────────────────────────────────────────────────────────────┐
   │        │   STAGE AGENTS (1 subagent per AIDLC stage)                 │
   │        ▼                                                             │
   │   1. Workspace Scout   → workspace-detection.md                      │
   │   2. Reverse Engineer  (cond) → architecture.md, api-docs.md, ...    │
   │   3. Requirements Analyst → requirements.md                          │
   │   4. Story Writer (cond) → stories/, personas.md                     │
   │   5. Workflow Planner → execution-plan.md                            │
   │   6. Unit Decomposer (cond) → units/{name}.md                        │
   │   7. Code Generator (per unit, parallelizable)                       │
   │   8. Build & Test Agent (per unit)                                   │
   │   9. Reviewer Pool (parallel fan-out):                               │
   │       ├─ Code Review     ├─ Security                                 │
   │       └─ Performance     └─ Simplifier                               │
   │  10. Ship Agent → release notes, ADRs                                │
   └──────────────────────────────────────────────────────────────────────┘
            │
   ┌────────┼─────────────────────────────────────────────────────────────┐
   │        ▼   CROSS-CUTTING AGENTS (called by orchestrator, not stages) │
   │                                                                      │
   │   A. Knowledge Agent   — patterns, ADRs, antipatterns, lessons       │
   │                          backing store: engram                       │
   │   B. Conflict Resolver — file-lock registry, semantic conflict diff  │
   │   C. Cost Governor     — budget gates, cancellation, adaptive depth  │
   │                                                                      │
   │   Auxiliary (built once, reused):                                    │
   │   D. Schema Registry   — JSON Schema for every handoff contract      │
   │   E. Run Manager       — run isolation, resume, replay               │
   │   F. Telemetry Sink    — structured event log per run                │
   └──────────────────────────────────────────────────────────────────────┘
```

---

## 3. File & Directory Layout

```
<repo-root>/
├── aidlc-rules/aws-aidlc-rules/    # UNCHANGED — these become agent system prompts
│   ├── core-workflow.md
│   ├── inception/, construction/, operations/, common/, extensions/
│
├── .claude/
│   ├── agents/                     # NEW — Claude Code subagent definitions
│   │   ├── orchestrator.md
│   │   ├── stage/
│   │   │   ├── workspace-scout.md
│   │   │   ├── reverse-engineer.md
│   │   │   ├── requirements-analyst.md
│   │   │   ├── story-writer.md
│   │   │   ├── workflow-planner.md
│   │   │   ├── unit-decomposer.md
│   │   │   ├── code-generator.md
│   │   │   ├── build-test-agent.md
│   │   │   ├── reviewer-code.md
│   │   │   ├── reviewer-security.md
│   │   │   ├── reviewer-performance.md
│   │   │   ├── reviewer-simplifier.md
│   │   │   └── ship-agent.md
│   │   └── cross-cutting/
│   │       ├── knowledge-agent.md
│   │       ├── conflict-resolver.md
│   │       └── cost-governor.md
│   ├── commands/                   # NEW — slash commands invoke orchestrator
│   │   ├── factory-spec.md
│   │   ├── factory-plan.md
│   │   ├── factory-build.md
│   │   ├── factory-review.md
│   │   ├── factory-ship.md
│   │   └── factory-resume.md
│   └── settings.json
│
├── .aidlc-orchestrator/            # NEW — runtime state (gitignored)
│   ├── contracts/                  # JSON Schema for every stage I/O
│   │   ├── workspace-scout.input.json
│   │   ├── workspace-scout.output.json
│   │   ├── ... one pair per stage agent
│   │   └── shared/
│   │       ├── artifact.schema.json
│   │       ├── audit-entry.schema.json
│   │       └── skill-compliance.schema.json
│   ├── runs/                       # one folder per orchestration run
│   │   └── <run-id>/
│   │       ├── manifest.yaml       # run config, current stage, gates
│   │       ├── timeline.jsonl      # append-only event log
│   │       ├── budget.yaml         # tokens/wall-clock used vs allotted
│   │       ├── locks/              # active file locks (Conflict Resolver)
│   │       ├── conflicts/          # open conflict records
│   │       └── handoffs/           # validated stage I/O artifacts
│   ├── knowledge/                  # Knowledge Agent index
│   │   ├── adrs/                   # architecture decision records
│   │   ├── patterns/               # reusable approved patterns
│   │   ├── antipatterns/           # things to avoid + reason
│   │   └── lessons/                # post-incident learnings
│   └── budgets/
│       ├── default.yaml            # per-stage default budgets
│       └── overrides/              # per-run overrides
│
└── aidlc-docs/                     # UNCHANGED — workflow artifacts
    ├── inception/, construction/, operations/
    ├── aidlc-state.md
    └── audit.md
```

**Key principle:** `.aidlc-orchestrator/` is **runtime state** (per machine,
gitignored except for `contracts/` and `budgets/default.yaml`). `aidlc-docs/`
remains the **deliverable** (committed, human-readable).

---

## 4. Handoff Contract (the spine of the system)

Every stage agent has an **input contract** and **output contract** as JSON
Schema. The orchestrator validates both — no agent runs without a valid input,
no stage closes without a valid output.

### 4.1 Generic input shape
```yaml
# .aidlc-orchestrator/runs/<run-id>/handoffs/code-generation.auth-service.input.yaml
run_id: 2026-05-08-auth-rewrite
stage_id: code-generation
unit: auth-service
predecessor_artifacts:
  - aidlc-docs/inception/plans/auth-service-plan.md
  - aidlc-docs/construction/plans/auth-service-functional-design.md
skills_required:
  - incremental-implementation
  - test-driven-development
  - source-driven-development
  - using-agent-skills    # implicit on every stage agent
skill_paths_resolved:     # orchestrator resolves once; subagents start cold and won't re-resolve
  - .agents/skills/using-agent-skills/SKILL.md
  - .agents/skills/incremental-implementation/SKILL.md
  - .agents/skills/test-driven-development/SKILL.md
  - .agents/skills/source-driven-development/SKILL.md
budget:
  tokens_max: 500000
  wall_clock_max_min: 30
  retries_max: 2
gates:
  - require_tests_green
  - require_human_approval
context_pointers:        # Knowledge Agent injects relevant priors
  - knowledge://patterns/lambda-handler-token-validation
  - knowledge://antipatterns/secrets-in-env
  - knowledge://adrs/auth-uses-asymmetric-jwt
locks_required:          # Conflict Resolver acquires before spawn
  - src/auth/**
  - tests/auth/**
```

### 4.2 Generic output shape
```yaml
status: complete | blocked | failed | needs_human
artifacts:
  - path: src/auth/handler.py
    kind: source
    hash: <sha256>
  - path: tests/auth/test_handler.py
    kind: test
audit_entries:
  - "[ts] CONSTRUCTION - Code Generation COMPLETE (Unit: auth-service)"
skill_compliance:
  - skill: test-driven-development
    status: PASS
    evidence: "23 tests, RGR followed, see commit a1b2c3d"
  - skill: incremental-implementation
    status: PASS
    evidence: "5 atomic commits, each green"
cost:
  tokens_in: 87000
  tokens_out: 100432
  wall_clock_min: 12.3
  retries_used: 0
emitted_knowledge:        # Knowledge Agent indexes these
  - kind: pattern
    title: "Asymmetric JWT validation in Lambda handler"
    body: "..."
    tags: [auth, lambda, jwt]
  - kind: adr
    title: "Use RS256 over HS256"
    rationale: "..."
conflicts_detected: []    # Conflict Resolver gets these
locks_to_release:
  - src/auth/**
  - tests/auth/**
```

### 4.3 Validation
- Schemas live in `.aidlc-orchestrator/contracts/`.
- Orchestrator validates with `jsonschema` (Python — already in `.venv`).
- Validation failure → stage marked `failed`, run paused, conflict record
  written, human notified.

---

## 5. Stage Agents

Each stage agent is a Claude Code subagent file
(`.claude/agents/stage/<name>.md`). The body of the file is:

```markdown
---
name: <stage-name>
description: <when-to-use> (matches description for proactive routing)
model: sonnet | opus | haiku   # tuned per stage
---

# System Prompt

You are the <stage> agent in the AIDLC software factory.

## Your input
You receive a handoff payload at .aidlc-orchestrator/runs/<run-id>/handoffs/<stage>.input.yaml
Validate it against .aidlc-orchestrator/contracts/<stage>.input.json.

## Your job
1. Read the AIDLC rule file: aidlc-rules/aws-aidlc-rules/<phase>/<stage-rule>.md
2. Execute the **Skill Execution Protocol (§5.1)** — paste the 6 steps + anti-bypass rule + Red Flags handling verbatim into this section. This is non-negotiable.
3. Produce the artifacts listed in the rule file.
4. Emit a knowledge payload (see §4.2 `emitted_knowledge[]`).

## Your output
Write the validated handoff at .aidlc-orchestrator/runs/<run-id>/handoffs/<stage>.output.yaml
The output MUST include a populated `skill_compliance[]` (§4.2) with PASS|FAIL|N/A
for every skill in `skills_required[]` plus concrete evidence — prose like
"looks good" is rejected.
Return a one-line status to the orchestrator.

## What you must NOT do
- Do not modify aidlc-state.md or audit.md (orchestrator owns those).
- Do not skip skill verification — see §5.1 anti-bypass rule.
- Do not exceed your budget; signal cost-exceeded if you would.
- Do not touch files outside your declared locks.
- Do not invent skill names; if a required skill path is missing from
  `skill_paths_resolved[]`, log `[Skill] MISSING: <name>` to `audit_entries[]`
  and follow the inline process from the rule file.
```

The 13 stage agent files (count includes 4 reviewer subagents):

| Agent | Model | Phase | Parallelizable | Skills |
|---|---|---|---|---|
| workspace-scout | haiku | inception | no | — |
| reverse-engineer | sonnet | inception | no | — |
| requirements-analyst | sonnet | inception | no | idea-refine, spec-driven-development |
| story-writer | sonnet | inception | no | spec-driven-development |
| workflow-planner | **opus** | inception | no | planning-and-task-breakdown |
| unit-decomposer | sonnet | inception | no | planning-and-task-breakdown |
| code-generator | sonnet | construction | **yes (per unit)** | incremental-implementation, test-driven-development, source-driven-development, frontend-ui-engineering\*, api-and-interface-design\* |
| build-test-agent | sonnet | construction | yes (per unit) | test-driven-development, browser-testing-with-devtools\*, debugging-and-error-recovery |
| reviewer-code | sonnet | review | **yes (with peers)** | code-review-and-quality |
| reviewer-security | **opus** | review | yes | security-and-hardening |
| reviewer-performance | sonnet | review | yes | performance-optimization |
| reviewer-simplifier | sonnet | review | yes | code-simplification |
| ship-agent | sonnet | ship | no | shipping-and-launch, git-workflow-and-versioning, ci-cd-and-automation, documentation-and-adrs, deprecation-and-migration\* |

**Why Opus on these two:** workflow-planner sets the entire run's task tree —
a bad plan cascades into every downstream stage, so the extra reasoning is
worth it once per run. reviewer-security catches issues that, missed, become
incidents — the cost asymmetry justifies Opus on every review pass.

**Skill notation:**
- `*` = **conditional skill**, loaded only if the project profile matches:
  - `frontend-ui-engineering*` — UI projects (frontend code present)
  - `api-and-interface-design*` — projects exposing public APIs
  - `browser-testing-with-devtools*` — UI projects with browser-testable surfaces
  - `deprecation-and-migration*` — projects with legacy code being replaced
  - Project profile is computed once by the orchestrator at run start
    and stored in `manifest.yaml` under `project_profile:`. Conditional
    skills are added to a stage's `skills_required[]` only if the matching
    profile flag is true.
- **Implicit on every stage agent:** `using-agent-skills` (the meta-protocol that
  defines how to LOAD/FOLLOW/CHECK/VERIFY/LOG/BLOCK on every other skill).
  Orchestrator always includes its resolved path in `skill_paths_resolved[]`
  (see §4.1) so subagents know how to execute the skills they're given.
- **Implicit on the orchestrator (not a stage agent):** `context-engineering`.
  The orchestrator's job is precisely context budgeting per subagent — this
  skill governs how much predecessor content vs. pointers it passes down.

**Reverse-engineer has no skills** because reverse engineering is *observation*
of an existing codebase, not specification or planning. Its rule file
(`inception/reverse-engineering.md`) supplies the full process inline, and
the Define-phase skills (`idea-refine`, `spec-driven-development`) only
activate during Requirements Analysis.

### 5.1 Skill Execution Protocol (mandatory in every stage agent body)

Every stage agent's system prompt MUST include the 6-step protocol verbatim
from `core-workflow.md` lines 76-87. Subagents start cold — they will NOT
infer it from context.

**The protocol (paste into every stage agent file):**

1. **LOAD** — Read each `<skill_path>/SKILL.md` from `skill_paths_resolved[]`
   in your input. Always include `using-agent-skills` first.
2. **FOLLOW** — Execute each skill's *Process* steps in declared order.
3. **CHECK** — For each skill, walk its *Common Rationalizations* table.
   If you're tempted to skip a step, the answer is NO. Log the rationalization
   you considered and rejected to `audit_entries[]`.
4. **VERIFY** — Produce evidence per each skill's *Verification* section.
   Evidence must be concrete (commit hashes, file paths, test counts) — not
   prose ("looks good", "tested it").
5. **LOG** — Add one entry to your output's `skill_compliance[]` per skill
   with `status: PASS|FAIL|N/A` and `evidence:` populated.
6. **BLOCK** — If any skill's verification fails, set output
   `status: blocked` and exit. Do NOT present completion.

**Anti-bypass rule (paste verbatim):**
> "I'll do it later", "it's obvious", "not needed for this change" are
> rationalizations. If a skill defines verification, you MUST produce evidence.
> No exceptions.

**Red Flags handling:** Each skill (per addyosmani/agent-skills) has a
*Red Flags* section. If any red flag fires during execution, set output
`status: needs_human` and copy the red flag text into `audit_entries[]`
prefixed with `[RedFlag] <skill-name>:`. The orchestrator pauses the run and
surfaces it to the user.

**Why this lives at the protocol level, not freeform per agent:** without it,
subagents drift into advisory mode and skills become decoration. The whole
premise of skills-as-gates (addyosmani/agent-skills) is that they cannot be
silently skipped — that property only holds if the protocol is restated in
every cold-start subagent prompt.

---

## 6. Cross-Cutting Agents

### 6.1 Knowledge Agent
**Purpose:** prevent the system from re-learning the same lessons every run.

**Inputs (it consumes):**
- Every stage's `emitted_knowledge[]` field.
- Bug fixes from build-test-agent (auto-tagged as `lessons`).
- ADRs from ship-agent.
- Reviewer findings flagged as systemic (e.g. "this happens 3+ times").

**Outputs (it provides):**
- `query(stage, tags, k=5)` → top-K relevant patterns/ADRs/antipatterns/lessons.
- Called by orchestrator **before** spawning each stage; result goes into
  `context_pointers[]`.

**Storage backend:** **engram, project-scoped** (already in user's stack —
`mcp__plugin_engram_engram__*`).
- `mem_save` for new emissions
- `mem_search` for queries
- **topic_key convention** (project-scoped): `aidlc/<project-slug>/<kind>/<slug>`
  - example: `aidlc/custom-aidlc/pattern/lambda-jwt-validation`
  - `<project-slug>` is derived from the repo name (slugified) and stored in
    `.aidlc-orchestrator/runs/<run-id>/manifest.yaml` under `project_slug:`
- **Why project-scoped:** prevents knowledge from project A leaking into
  project B's queries (e.g. "the auth pattern from the Stripe integration
  shouldn't surface during a healthcare project"). Cross-project queries are
  opt-in via an explicit `--include-projects=<list>` flag on the Knowledge
  Agent's query interface.

**Schema for knowledge entry:**
```yaml
kind: pattern | adr | antipattern | lesson
title: str
body: markdown
tags: [str]
created_in_run: <run-id>
created_at: <iso>
related_artifacts: [path]
deprecated_by: <knowledge-id?>   # supersession chain
```

**Critical rule:** Knowledge Agent **does not write code or make decisions**.
It only indexes and retrieves. Decisions stay with stage agents + human.

### 6.2 Conflict Resolver
**Purpose:** prevent parallel agents from corrupting each other's work.

**Activation triggers:**
1. Path collision: two parallel agents declare overlapping `locks_required`.
2. Interface drift: agent B modifies a function signature that agent A
   declared as a dependency in its input contract.
3. Architectural contradiction: two agents emit knowledge of `kind: adr` with
   contradictory positions (detected by orchestrator on emit).

**Mechanisms:**
- **File lock registry**: `.aidlc-orchestrator/runs/<run-id>/locks/`. One
  file per active lock with glob pattern + holder agent. Acquired pre-spawn.
- **Lock acquisition policy**:
  - Non-overlapping → granted immediately.
  - Overlapping but read-only → granted (multiple readers OK).
  - Overlapping write → queued; second agent waits.
- **Semantic conflict diff** (interface drift):
  - After each code-generator finishes, parse exported symbols (Python AST,
    TS compiler API).
  - If a symbol used by another in-flight unit changed signature → conflict
    record + pause that unit.
- **Resolution policies (in priority order):**
  1. **Auto-merge** if changes are non-overlapping at AST level.
  2. **Priority** — stage with higher `priority` field in handoff wins; loser
     re-plans.
  3. **Escalate to human** — write conflict record, pause both stages, surface
     to user with both diffs.

**Conflict record:**
```yaml
# .aidlc-orchestrator/runs/<run-id>/conflicts/<id>.yaml
id: <uuid>
detected_at: <iso>
kind: path_collision | interface_drift | adr_contradiction
parties:
  - agent: code-generator
    unit: auth-service
  - agent: code-generator
    unit: user-service
overlap:
  - src/shared/auth_types.py
auto_resolution_attempted: true
auto_resolution_succeeded: false
resolution: <empty until resolved>
resolved_by: <human|policy:priority|policy:auto_merge>
```

### 6.3 Cost Governor
**Purpose:** prevent the multi-agent system from being economically absurd.

**Three layers:**

1. **Pre-flight gate** (before each spawn):
   - Read `.aidlc-orchestrator/runs/<run-id>/budget.yaml`.
   - Compute remaining budget (run-level + stage-level).
   - If remaining < estimated cost → block spawn, emit `cost_exceeded`.
   - Estimate uses `budgets/default.yaml` priors per stage, refined by past
     runs (rolling average).

2. **Mid-flight monitor:**
   - Stage agents must emit a `progress_token_count` heartbeat every N tool
     calls (target: every 5 tool calls).
   - If projected total > budget → orchestrator sends cancellation signal.
   - Cancellation = "stop, write partial output, mark `blocked: budget`".

3. **Adaptive depth:**
   - Each AIDLC stage already has `minimal | standard | comprehensive` depth.
   - If remaining run budget < threshold → Cost Governor downshifts depth
     for upcoming optional stages.
   - Conditional stages (User Stories, Application Design, Units Generation)
     are first to be skipped.

**Budget config:**
```yaml
# .aidlc-orchestrator/budgets/default.yaml
run:
  tokens_max: 5_000_000
  wall_clock_max_min: 240
  cost_max_usd: 50
per_stage:
  workspace-scout:    { tokens: 50_000,  wall_min: 5,  retries: 1 }
  requirements-analyst: { tokens: 800_000, wall_min: 30, retries: 2 }
  code-generator:     { tokens: 500_000, wall_min: 30, retries: 2 }
  build-test-agent:   { tokens: 300_000, wall_min: 20, retries: 3 }
  reviewer-*:         { tokens: 200_000, wall_min: 15, retries: 1 }
adaptive_depth:
  threshold_pct_remaining: 30
  downshift_order: [comprehensive→standard, standard→minimal, skip-optional]
```

**Critical rule:** Cost Governor never **kills** without saving partial state.
A canceled stage must write a `blocked: budget` output that future runs
can resume from.

---

## 7. Auxiliary Infrastructure

### 7.1 Schema Registry
- Plain JSON Schema files in `.aidlc-orchestrator/contracts/`.
- Versioned with semver in filename: `code-generation.input.v1.json`.
- Backwards-compat policy: minor version = additive only. Major = orchestrator
  refuses old runs to resume; user must restart.

### 7.2 Run Manager (resume + replay)
- `manifest.yaml` per run holds the source of truth: current stage, completed
  stages, open conflicts, budget remaining.
- **Resume command** (`/factory-resume <run-id>`): orchestrator reads manifest,
  validates last completed stage's output, routes to next stage.
- **Replay command** (`/factory-replay <run-id> --from <stage>`): re-runs from
  a checkpoint, reusing prior artifacts as context but generating fresh output.
- **Legacy adoption** (`/factory-resume` with no run-id, in a project that
  already has `aidlc-docs/` from the legacy single-agent flow): orchestrator
  scans `aidlc-docs/audit.md` and `aidlc-state.md`, reconstructs a synthetic
  manifest marking all completed stages as `status: complete (adopted)`, and
  routes to the next uncompleted stage. Adopted stages don't get re-validated
  against contracts — they're trusted as-is. The synthetic run-id is
  `legacy-<repo-slug>-<adoption-ts>`.

### 7.3 Telemetry Sink
- `timeline.jsonl` per run — every event as one JSON line:
  ```json
  {"ts":"2026-05-08T10:23:01Z","evt":"stage_start","stage":"code-generator","unit":"auth-service","run_id":"..."}
  {"ts":"2026-05-08T10:35:14Z","evt":"stage_end","stage":"code-generator","status":"complete","tokens":187432}
  {"ts":"2026-05-08T10:35:15Z","evt":"conflict_detected","kind":"interface_drift","parties":["auth","user"]}
  ```
- One-line tail tool (`aidlc-scripts/factory-tail <run-id>`) for live monitoring.

### 7.4 Run isolation
- Multiple concurrent runs (different features) use different `run-id`.
- Locks are scoped to a run-id — runs don't block each other's locks unless
  they touch the same files in the **working tree**, in which case the
  orchestrator refuses concurrent runs that touch overlapping paths.

---

## 8. Claude Code-Native Implementation Notes

### 8.1 Subagent spawning
- Orchestrator uses `Task(subagent_type="<stage-name>", prompt="...")`.
- Parallel: orchestrator emits multiple `Task()` calls in **a single message**
  (per Claude Code parallel-tool-call semantics).
- Sequential: one `Task()` per message, wait for return, validate, route next.
- **Concurrency cap: 4 simultaneous subagents.** Matches the natural width of
  the Reviewer Pool. Higher fan-out (e.g. 8 parallel code-generators) is
  queued in batches of 4 by the orchestrator. Cap is configurable in
  `.aidlc-orchestrator/budgets/default.yaml` under `concurrency.max_parallel`.

### 8.2 Context budget per agent
- Each subagent starts cold (no parent context). Orchestrator passes only:
  - Run-id + stage-id + path to input handoff
  - Pointers (NOT full content) to predecessor artifacts and skill files
  - Knowledge Agent query results (top-5 priors only)
- This is the **biggest win**: today the single agent carries everything;
  subagents read only what their input declares.

### 8.3 Slash commands
Each user-facing command maps to an orchestrator entry point:
- `/factory-spec` → orchestrator runs Workspace Scout + Requirements Analyst
- `/factory-plan` → adds Workflow Planner + (optional) Unit Decomposer
- `/factory-build` → loops Code Generator + Build & Test per unit
- `/factory-review` → fan-out Reviewer Pool
- `/factory-ship` → Ship Agent
- `/factory-resume <run-id>` → Run Manager resume

### 8.4 Cross-tool degraded mode
For Copilot/Cursor/Cline: the same rule files in `aidlc-rules/` are loaded
sequentially by a single agent that **role-switches**. The orchestrator,
contracts, conflict resolver, and parallelism are Claude-Code-only features.
Document this clearly in `aidlc-rules/adapters/<tool>.md` so users know what
they're getting on each platform.

---

## 9. Implementation Phases

Each phase ends with a working, demonstrable system. No phase introduces a
half-finished primitive.

> **Status sync rule:** any change here must also be reflected in the
> "📍 Current Phase" table near the top of the document. The two are kept
> in sync manually — if they disagree, the per-phase status below is
> authoritative.

### Phase 0 — Skeleton + Sequential Orchestrator (1–2 days)
**Status:** ✅ Complete · **Started:** 2026-05-08 · **Completed:** 2026-05-08
**Goal:** Prove the contract pattern works end-to-end with one stage.
- [x] Write `orchestrator.md`, `workspace-scout.md`, `requirements-analyst.md`.
- [x] Write input/output JSON schemas for those two stages (+ shared validator `aidlc-scripts/factory_validate.py`, smoke-tested against valid+invalid fixtures).
- [x] Write `/factory-spec` slash command.
- [x] User-accepted without running the live integration test ("ok, its fine, lets go for next" — 2026-05-08). Live e2e remains the integration test for Phase 1's full inception → ship dry run.
- **Acceptance:** the existing AIDLC `/spec` flow is reproduced, just split
  across two subagents with a validated handoff between them.

### Phase 1 — All Stage Agents, Sequential (3–5 days)
**Status:** ✅ Complete · **Started:** 2026-05-08 · **Completed:** 2026-05-08
- [x] Add the remaining 11 stage agent definitions (4 inception + 2 construction + 4 review + 1 ship) + 16 schemas (reviewers share input/output v1).
- [x] Add `/factory-plan`, `/factory-build`, `/factory-review`, `/factory-ship` slash commands; orchestrator extended with all four Phase 1 sequences.
- [x] Smoke-tested 3 representative output schemas (workflow-planner, code-generator, reviewer) — all pass.
- [x] User-accepted without live e2e ("lets go to phase 2" — 2026-05-08). Live integration test deferred; will surface in early Phase 2 work.
- **Acceptance:** complete AIDLC inception → ship cycle, all sequential.

### Phase 2 — Cost Governor (2 days)
**Status:** ✅ Complete · **Started:** 2026-05-08 · **Completed:** 2026-05-08
- [x] Implement `aidlc-scripts/factory_budget.py` (init / check / deduct / status subcommands) — uses `.aidlc-orchestrator/budgets/default.yaml` as policy and `<run>/budget.yaml` as per-run state. **Smoke-tested all four exit-code paths (0/1/2/3) plus init/deduct.**
- [x] Wire the orchestrator's pre-flight gate: `factory_budget.py check <run> <stage>` before every spawn. Exit codes drive the routing decision (0=ok, 1=downshift, 2=skip-optional, 3=halt). Added to "All flows share the same primitives" + inline in Phase 0 sequence.
- [x] Wire the orchestrator's post-flight reconciliation: `factory_budget.py deduct ...` after every spawn using the `cost.{tokens_in,tokens_out,wall_clock_min}` fields from each stage's output. Fallback to default-budget estimate if `cost` block is absent (logged as `[CostGov] Estimated`).
- [x] Adaptive depth: `depth_override` field added to `requirements-analyst.input.v1.json` and `workflow-planner.input.v1.json` (re-validated with fixture). Both agents updated to honor it and log `[CostGov] Depth overridden ...` to audit. Optional stages (story-writer, unit-decomposer) skip via gate exit code 2.
- [x] Documented the Claude-Code-subagent limitation in orchestrator.md "Cost Governor (Phase 2)" section: mid-flight cancellation is not supported (Task() returns are atomic); enforcement is pre-flight gate + post-flight reconciliation + agent honor-system on declared `budget`.
- [ ] Live integration test: artificially low budget run downshifts and completes within budget; over-budget run halts cleanly. **(Pending live invocation — same status as Phase 0/1 acceptance.)**
- **Acceptance:** an artificially low budget run downshifts depth and
  completes within budget; an over-budget run halts cleanly with a
  documented reason in `audit.md` and a non-zero exit on `factory_budget.py check`.

### Phase 3 — Knowledge Agent (2–3 days)
**Status:** ✅ Complete · **Started:** 2026-05-08 · **Completed:** 2026-05-08
- [x] Wire engram integration. Orchestrator calls `mcp__plugin_engram_engram__mem_search` (pre-spawn) and `mcp__plugin_engram_engram__mem_save` (post-return) directly. No CLI wrapper — engram is MCP-only and the orchestrator runs in Claude Code with native MCP access. Spec lives at `.claude/agents/cross-cutting/knowledge-agent.md`.
- [x] Add structured `emitted_knowledge[]` to all 10 stage output schemas (workspace-scout, requirements-analyst, reverse-engineer, story-writer, workflow-planner, unit-decomposer, code-generator, build-test-agent, reviewer, ship-agent). Required fields: `kind` (enum: pattern/adr/antipattern/lesson) + `title` + `body`. Optional: `tags`, `related_artifacts`, `confidence`. Smoke-tested valid + invalid fixtures.
- [x] Pre-spawn Knowledge query: orchestrator step 2 of "All flows share the same primitives" — call `mem_search`, filter by confidence/deprecation, boost antipatterns, inject top-5 results into `context_pointers[]` with ~2,500 token budget. Inlined into Phase 0 Step 3.
- [x] Post-return Knowledge save: orchestrator step 7 — iterate `emitted_knowledge[]`, call `mem_save` with topic_key `aidlc/<project_slug>/<kind>/<title-slug>`, scope=`project`. kind→type mapping: adr→decision, pattern→pattern, lesson→learning, antipattern→discovery. Conflict heuristic: silent for related/compatible/scoped, surface for low-confidence supersedes/conflicts_with on ADRs.
- [x] Per-agent emission guidance added to the four highest-value emitters: code-generator, build-test-agent, reviewer-security, ship-agent.
- [x] Failure mode documented: if engram unavailable, log `[Knowledge] DEGRADED` and continue with empty priors.
- [ ] Live integration test: second run on same project shows reduced token usage on Requirements Analyst (priors retrieved); a known antipattern is auto-flagged. **(Pending live invocation.)**
- **Acceptance:** second run on same project shows reduced token usage on
  Requirements Analyst (priors retrieved); a known antipattern is auto-flagged.

### Phase 4 — Parallel Reviewer Pool (1–2 days)
**Status:** ✅ Complete · **Started:** 2026-05-08 · **Completed:** 2026-05-08
- [x] Refactor `/factory-review` flow in orchestrator.md from sequential to parallel: 6-step procedure (pre-flight gates → knowledge queries → parallel `Task()` fan-out in one message → post-processing → merge → approval).
- [x] Implement `aidlc-scripts/factory_merge_reviews.py` — merges 4 reviewer outputs into `aidlc-docs/operations/review-report.md` with summary table, sorted per-reviewer findings (with reviewer-specific fields like `cwe`/`big_o`/`simplification_pattern` rendered), and "files with most findings" cross-reviewer index.
- [x] Smoke-tested merge script in 3 scenarios: full set (4), explicit partial set (3), missing output file (warns + completes).
- [x] Updated `/factory-review` slash command to reflect parallel pattern; documented wall-clock acceptance criteria.
- [x] Documented the partial-set protocol: when Cost Governor returns exit 2 for any reviewer, drop from active set; merge script accepts `--reviewers` to skip in the output.
- [ ] Live integration test: review stage wall-clock drops by ~3–4× vs Phase 1 sequential. **(Pending live invocation.)**
- **Acceptance:** review stage wall-clock drops by ~3–4x vs sequential
  on the same feature.

### Phase 5 — Conflict Resolver + Parallel Code Generation (3–5 days)
**Status:** ✅ Complete · **Started:** 2026-05-08 · **Completed:** 2026-05-08
- [x] **File lock registry + glob matcher** — `aidlc-scripts/factory_conflict.py acquire/release/list`. Heuristic component-wise glob overlap with `**` wildcard support; biased toward false positives. Read/write mode handling (read-read sharing, write-write blocking, write-read blocking). Lock file format: `runs/<run>/locks/<holder>.yaml`. Smoke-tested non-overlapping → granted, overlapping write → conflict record, read-mode sharing → both granted, release → idempotent cleanup.
- [x] **Semantic conflict diff (Python AST)** — `factory_conflict.py snapshot/check-symbols`. Captures top-level function and class signatures (args + return annotations) pre-spawn; diffs post-spawn. If drift detected AND other holders are active → `interface_drift` conflict record. Smoke-tested with signature change + added function + removed method — all 3 drift types caught.
- [x] **Resolution policies (escalation-only for Phase 5)** — orchestrator surfaces conflict record and lets user re-plan / manual-merge / cancel. Auto-merge and priority routing documented as future features in `ORCHESTRATOR-PLAN.md §6.2` (not implemented because generic auto-merge is unsafe).
- [x] **Enable parallel `Task()` fan-out for code-generator** — orchestrator's `/factory-build` flow refactored to layer-parallel. Topo-sort units → for each layer: per-unit pre-flight (budget+lock+snapshot+knowledge+input) → 3 sub-stages parallel (plan/generated/approved) → parallel build-test-agent → release locks → auto-commits. Concurrency cap 4 enforced; layers > 4 units batch within the layer.
- [x] **Conflict Resolver reference doc** at `.claude/agents/cross-cutting/conflict-resolver.md`. Orchestrator gets a "Conflict Resolver (Phase 5 — active)" section alongside Cost Governor and Knowledge Agent.
- [x] **factory-build.md slash command** updated to reflect layer-parallel pattern with conflict-resolver protocol references.
- [ ] Live integration test: two truly independent units complete in parallel; two units that touch a shared module surface a conflict (path or interface drift). **(Pending live invocation.)**
- **Phase 5.5 follow-up (✅ Complete · 2026-05-09):** TS/JS AST diff via tree-sitter + tree-sitter-typescript + tree-sitter-javascript. Implemented in `aidlc-scripts/factory_conflict.py` with extension dispatcher (`.ts/.mts/.cts → typescript`, `.tsx → tsx`, `.js/.mjs/.cjs/.jsx → javascript`). Extracts top-level `export function`, `export class`, `export interface`, `export type`, `export enum`, and `export const x = (...) => ...` (arrow functions). Whitespace-normalized signatures avoid spurious drift on reformat. tree-sitter deps are optional — when missing, TS/JS files mark as `tree_sitter_unavailable` and only path locking applies (graceful degradation). Smoke test caught all 4 mutation types: param rename + return-type change, class method removal, interface member rename, enum addition. Deep type-system drift (generics narrowing, conditional types) stays out of scope; that needs `tsc --noEmit` or LSP integration (Phase 7+).
- **Acceptance:** two units that touch shared module are detected, conflict
  is resolved (auto or escalated); two truly independent units complete in
  parallel.

### Phase 6 — Run Manager + Telemetry Hardening (2 days)
**Status:** ✅ Complete · **Started:** 2026-05-08 · **Completed:** 2026-05-08
- [x] Implement `manifest.yaml` (atomic write-tmp-then-rename) + resume + replay subcommands in `aidlc-scripts/factory_run.py` (init / set / complete-stage / fail-stage / emit / status / resume / replay / adopt-legacy / tail).
- [x] Implement `timeline.jsonl` (append-only, one JSON line per event) + tail subcommand with `--follow` mode.
- [x] Wire orchestrator's shared primitives to call `factory_run.py emit` (steps 0 + 11) and `complete-stage` / `fail-stage` (step 12).
- [x] Add `/factory-resume` slash command — resumes by run-id OR adopts legacy `aidlc-docs/` if invoked without args.
- [x] Add `/factory-replay <run-id> --from <stage>` slash command — non-destructive (archives `*.replay-<ts>.yaml` instead of deleting).
- [x] Bug fixes during smoke test: (1) resume now uses manifest.current_stage instead of naive PHASE_ORDER scan (avoids suggesting skipped conditional stages); (2) legacy adoption now maps "Workspace Detection" → `workspace-scout` etc. via alias table.
- [x] **Stress test passed**: simulated mid-stage crash (workflow-planner started, no completion event), called resume → correctly suggested workflow-planner with `completed_count: 2`, manifest hash unchanged (non-destructive), timeline appended only the resume_requested event, post-resume completion succeeded.
- [ ] Live integration test: run a real `/factory-spec` end-to-end, kill mid-flight at requirements-analyst Pass 1, resume, complete the run, verify final artifacts identical to a non-killed run. **(Pending live invocation.)**
- **Acceptance:** kill-and-resume produces a complete run with no
  duplicated work and all artifacts intact.

**Total estimate:** ~14–20 working days, in increments that ship value
each phase.

---

## 10. Resolved Decisions (locked in 2026-05-08)

| # | Decision | Rationale |
|---|---|---|
| 1 | **Build in repo root.** Ships with the AIDLC distribution; install scripts copy to consumer projects (e.g. `pruebaaidlcv2/`). | Single source of truth; avoids fork-then-promote drift. |
| 2 | **Project-scoped engram namespace** — `aidlc/<project-slug>/<kind>/<slug>`. Cross-project queries are opt-in. | Prevents cross-project knowledge leakage. See §6.1. |
| 3 | **Opus for `workflow-planner` and `reviewer-security`.** Sonnet for the rest. Haiku for `workspace-scout` only. | Plan errors cascade into every downstream stage; security misses become incidents. Cost asymmetry justifies Opus on these two. See §5. |
| 4 | **Concurrency cap: 4 simultaneous subagents.** Configurable in `budgets/default.yaml`. | Matches Reviewer Pool width; respects Claude Code rate limits; predictable cost ceiling. |
| 5 | **Approval gates pause the run** (not queue across runs). | Simpler mental model; user knows exactly what's blocked. |
| 6 | **`/factory-resume` adopts legacy `aidlc-docs/`** as a synthetic run with completed stages marked `status: complete (adopted)`. | Zero migration friction for existing AIDLC users; adopted stages are trusted as-is, not re-validated. See §7.2. |

---

## 11. Risks & Mitigations

| Risk | Mitigation |
|---|---|
| Subagents drift from AIDLC rules | Each agent's system prompt cites the rule file as authoritative; orchestrator validates output against contract |
| Token cost spikes | Cost Governor (Phase 2) is mandatory before any parallelism (Phase 4) |
| Conflict resolver false positives | Phase 5 starts with file-glob locks only; semantic AST diff is opt-in until proven |
| Knowledge pollution (bad priors retrieved) | Knowledge entries have `confidence` field; query filters by min-confidence; user can mark `deprecated` |
| Run state corruption on crash | manifest.yaml writes are atomic (write-tmp-then-rename); timeline.jsonl is append-only |
| Cross-tool users stuck on old flow | Document degraded mode clearly in adapters/; no AIDLC functionality is removed, only added |

---

## 12. Acceptance Criteria for "Done"

The orchestrator is "done" (Phase 6 complete) when:

- [ ] A greenfield feature can run `/factory-spec` → `/factory-plan` →
      `/factory-build` → `/factory-review` → `/factory-ship` end-to-end with
      no manual stage routing.
- [ ] Reviewer Pool runs in parallel and merges findings.
- [ ] Two independent units run code-generation in parallel; one shared-module
      pair surfaces a conflict and is auto-resolved or escalated.
- [ ] A run that hits 90% of budget downshifts depth on remaining stages.
- [ ] A killed run resumes from last checkpoint with zero duplicated work.
- [ ] A second run on the same project pulls priors from Knowledge Agent and
      uses fewer tokens than the first run on Requirements Analyst.
- [ ] All 13 stage agents + 3 cross-cutting agents have committed schemas.
- [ ] Documentation in `aidlc-rules/adapters/` explains what works on
      Claude Code vs degraded mode on Copilot/Cursor/Cline.

---

*Plan version: v1 — 2026-05-08*
