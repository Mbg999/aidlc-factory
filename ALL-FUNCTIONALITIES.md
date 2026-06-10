# AIDLC — Complete Functionality Inventory

> **Auto-generated** — Last updated: 2026-06-10

This document lists **all** functional capabilities of the AIDLC (AI-Driven Development Life Cycle) orchestrator system. It is the single source of truth for "what this system does."

---

## 1. Orchestrator Commands (Factory Commands)

Multi-platform slash commands (Claude Code, Cursor, GitHub Copilot, OpenCode, Codex).

| Command | Phase | What it does |
|---------|-------|-------------|
| `/factory-spec` | Phase 0 (Inception) | Workspace detection + requirements analysis. Creates run, initializes manifest, runs workspace-scout + requirements-analyst. |
| `/factory-plan` | Phase 1 (Inception) | Execution planning + optional unit decomposition. Story-writer → application-designer → workflow-planner → unit-decomposer. |
| `/factory-build` | Phase 2 (Construction) | Per-unit code generation + build/test. Layer-parallel execution with file-glob locks and AST drift detection. |
| `/factory-review` | Phase 3 (Quality) | Post-generation reviewer pool (code, security, performance, simplification) in parallel. |
| `/factory-ship` | Phase 4 (Operations) | Release notes, ADRs, CHANGELOG, CI/CD wiring, version proposal. |
| `/factory-product` | Phase 0-1 (Combined) | Full product harness: workspace scout + requirements + personas + stories + execution plan. |
| `/factory-context` | Utility | Build and display contextual snapshot from traceability files (audit, state, manifest, timeline). |
| `/factory-state` | Utility | Show current state of a run — completed stages, current stage, budget, issues. |
| `/factory-resume` | Utility | Resume interrupted run from last checkpoint. |
| `/factory-replay` | Utility | Re-run from a specific stage. Rolls back manifest, archives handoffs. |
| `/factory-self` | Meta | Run AIDLC on its own codebase (orchestrator self-improvement). |
| `/factory-code-tour` | Utility | Dependency-ordered codebase tour — foundations → entry points. |
| `/factory-help` | Utility | Help reference for all commands. |
| `/factory-onboarding` | Utility | Interactive walkthrough of the AIDLC system. |

**Platform adaptations** (thin wrappers):
- **Claude Code / OpenCode**: `Task()` + `python3`
- **Cursor**: `delegate` (no `Task()`), cross-cutting agents at `.cursor/agents/cross-cutting/`
- **GitHub Copilot**: `agent` tool (no `Task()`), sequential execution, `python` (not `python3`), human gates mandatory
- **Codex**: Similar to Claude Code

---

## 2. Runtime Protocols (Single Source of Truth)

All command logic lives in `.aidlc-orchestrator/runtime/*.md`.

| Protocol | File | Purpose |
|----------|------|---------|
| **Spawn Loop** | `spawn-loop.md` | 10-step full spawn protocol (Task() + validation) and post-execution inline loop. Context compaction mandatory. |
| **Fast Path** | `fast-path.md` | TINY prefilter bypass for small tasks (≤200 lines, single file). Decision table: what it skips vs. full pipeline. |
| **Recovery** | `recovery.md` | Resume/replay from checkpoints. Critical vs non-critical stage failure handling. |
| **Compaction** | `compaction.md` | Context compaction rules — discard transient reasoning, preserve structured outputs. |
| **Validation** | `validation.md` | Handoff validation rules (lightweight for inline, JSON Schema for full spawn). |
| **Conflict Resolution** | `conflict-resolver.md` | Path collision + interface drift escalation protocol. |
| **Knowledge Agent** | `knowledge-agent.md` | Pre-spawn query (project + shared priors) + post-return save with judgment heuristics. |
| **Audit Lifecycle** | `audit-lifecycle.md` | Audit block protocol (START, COMPLETE, non-spawn blocks). |
| **Run Manager** | `run-manager.md` | Run directory structure, manifest lifecycle, state transitions. |
| **Contextualization** | `contextualization.md` | Context snapshot generation, depth modes (minimal/standard/comprehensive/auto). |
| **Core Workflow** | `core-workflow.md` | AIDLC constitution — distributed to installed projects via installer. |
| **Extension Loading** | `extension-loading.md` | How `.opt-in.md` extensions are loaded and enforced. |
| **Custom Subagents** | `custom-subagents.md` | How to register custom subagents. |
| **Project Profile** | `project-profile.md` | Project classification, UI detection, design system, legacy detection, tech stack. |
| **Design System** | `design-system.md` | Design system token pipeline, Figma integration, Stitch MCP. |
| **UI Compiler** | `ui-compiler.md` | Token → CSS/Tailwind compilation, brownfield extraction. |
| **Visual Feedback** | `visual-feedback.md` | ASCII diagrams, status indicators, progress bars. |
| **Skill Protocol** | `skill-protocol.md` | Skill resolution order, autoskills, SHA verification, drift detection. |

---

## 3. Stage Agents (14 Subagents)

All agents in `.claude/agents/stage/` (mirrored to `.cursor/`, `.github/`, `.opencode/`, `.codex/`).

| Agent | Type | What it does |
|-------|------|-------------|
| **workspace-scout** | Inline | Detects project type, tech stack, existing code, CodeGraph state. Greenfield shortcut for empty projects. |
| **requirements-analyst** | Inline | Two-pass requirements analysis (Pass 1: questions → human gate → Pass 2: requirements.md). |
| **story-writer** | Inline | Generates user stories and personas (conditional — multi-component only). |
| **application-designer** | Inline | Two-pass design (questions → artifacts). Produces 5 design artifacts. |
| **workflow-planner** | Inline | Creates execution plan (Mermaid diagram + task tree + acceptance criteria). |
| **unit-decomposer** | Task | Decomposes plan into units with dependencies (when ≥2 units). |
| **code-generator** | Task | Per-unit code generation (plan → generated → approved). Three sub-stages. |
| **build-test-agent** | Task | Per-unit build + test execution. Parallel per layer. |
| **reviewer-code** | Task | Code quality review (lint, build, complexity). |
| **reviewer-security** | Task | Security review (OWASP-aware, runs on Sonnet). |
| **reviewer-performance** | Task | Performance review (hot-path analysis, allocation). |
| **reviewer-simplifier** | Task | Simplification review (flags over-engineering, dead code). |
| **ship-agent** | Inline | Release notes, ADRs, CHANGELOG, CI/CD wiring, version proposal. |
| **reverse-engineer** | Inline | Reverse-engineers brownfield codebases (conditional). |

---

## 4. Python Scripts (50+ Scripts)

All in `aidlc-scripts/`. Core scripts grouped by function.

### 4.1 Run Management & Orchestration

| Script | Purpose |
|--------|---------|
| `factory_run.py` | Run manager — generate run-id, emit timeline events, complete/fail stages, emit audit blocks, status queries, set fields. |
| `factory_graph.py` | Dependency graph computation (Kahn's algorithm) over unit waves. |
| `factory_triage.py` | Complexity prefilter — TINY/SMALL/MEDIUM/LARGE classification. |
| `factory_stage_registry.py` | Stage registry — stage metadata, execution mode, predecessors. |
| `factory_features.py` | Feature flags — get/is-set/list feature toggles. |
| `factory_project_context.py` | Project context builder — reads manifest, builds context. |
| `factory_project_profile.py` | Project profile classifier — detects UI, design system, legacy, tech stack. |

### 4.2 Validation & Quality

| Script | Purpose |
|--------|---------|
| `factory_validate.py` | JSON Schema validation for handoffs (input/output/approval). |
| `factory_content_validate.py` | Content validation — checks for fabricated content, rogue headers, timestamp validation. |
| `factory_lint_rules.py` | Lint rule management — custom lint rules, severity levels. |
| `factory_contract_strictness.py` | Contract strictness checker — validates schema completeness. |
| `factory_slo_check.py` | SLO (Service Level Objective) checks — auto-runs quality reports. |

### 4.3 Conflict & Safety

| Script | Purpose |
|--------|---------|
| `factory_conflict.py` | File-glob lock manager — acquire, release, check-wave, AST snapshot, drift detection. |
| `factory_drift_detect.py` | Skill drift detection — flags skills whose version range no longer covers latest stable. |
| `factory_secretscan.py` | Secret scanning — detects credentials in generated code. |
| `factory_merge_reviews.py` | Review merge — combines multiple reviewer outputs into unified report. |
| `factory_audit_writes.py` | Audit write validation — verifies audit.md integrity. |

### 4.4 Skills & Knowledge

| Script | Purpose |
|--------|---------|
| `factory_skill_sync.py` | Skill sync — install framework skills (autoskills) with forced tech stack. |
| `factory_custom_skills.py` | Custom skill installer — fetches community skills with SHA-256 verification. |
| `factory_skill_drift.py` | Skill drift detector — checks for outdated skills. |
| `factory_knowledge_dashboard.py` | Knowledge dashboard — displays persistent memory state. |
| `factory_knowledge_promote.py` | Knowledge promotion — promotes observations to long-term memory. |
| `factory_agent_discover.py` | Agent discovery — auto-detects available subagents. |

### 4.5 Design System & UI

| Script | Purpose |
|--------|---------|
| `factory_design_system_harness.py` | Design system harness — orchestrates token pipeline. |
| `factory_design_system_learn.py` | Design system learner — learns from existing UI code. |
| `factory_design_system_extract_brownfield.py` | Brownfield token extraction — extracts tokens from existing CSS. |
| `factory_design_system_resolve.py` | Design system resolver — resolves token references. |
| `factory_design_system_snap.py` | Design system snapshot — captures current state. |
| `factory_ds_bootstrap.py` | Design system bootstrap — initializes new design system. |
| `factory_token_bridge.py` | Token bridge — prepares tokens.css, detects Tailwind, brownfield sources. |
| `factory_token_to_css.py` | Token → CSS compiler. |
| `factory_token_to_tailwind.py` | Token → Tailwind config compiler. |
| `factory_figma_mcp.py` | Figma MCP integration — fetches design tokens from Figma. |
| `factory_stitch_mcp.py` | Stitch MCP integration — connects to Stitch design system. |
| `factory_stitch_snap.py` | Stitch snapshot — captures Stitch state. |
| `factory_primitive_gen.py` | Primitive generator — generates UI primitives from tokens. |

### 4.6 CodeGraph Integration

| Script | Purpose |
|--------|---------|
| `factory_codegraph.py` | CodeGraph manager — check readiness, affected files detection. |
| `factory_context_builder.py` | Context builder — builds contextual snapshots from traceability files. |
| `factory_cookbook_e2e.py` | Architecture cookbook E2E tests. |

### 4.7 Telemetry & Cost

| Script | Purpose |
|--------|---------|
| `factory_telemetry.py` | Telemetry — tracks usage, performance, costs. |
| `factory_cost_estimate.py` | Cost estimation — pre-flight cost estimates per unit. |
| `factory_telemetry.py` | SLO monitoring and metrics collection. |

### 4.8 Testing & Utilities

| Script | Purpose |
|--------|---------|
| `factory_build_cache.py` | Build cache — caches build artifacts. |
| `factory_model.py` | Model resolver — resolves per-stage model assignments. |
| `factory_complexity.py` | Complexity analyzer — estimates task complexity. |
| `factory_evidence_extract.py` | Evidence extraction — pulls evidence from audit trail. |
| `factory_prompt_ab.py` | A/B testing for prompts — compares prompt variants. |
| `factory_quality_report.py` | Quality report generator — generates comprehensive quality reports. |
| `factory_tech_mappings.py` | Technology mappings — maps tech stacks to skills. |
| `factory_validate.py` | Validation utilities — various validation helpers. |
| `factory_install_aidlc.py` | Installer — copies rules + agents into target projects (cross-platform). |

---

## 5. Contracts & Schemas

JSON Schema contracts for every stage I/O in `.aidlc-orchestrator/contracts/`.

| Contract | Purpose |
|----------|---------|
| `code-generator.input.v1.json` | Code generator input handoff schema. |
| `code-generator.output.v1.json` | Code generator output handoff schema. |
| `reviewer.input.v1.json` | Shared reviewer input schema. |
| `reviewer.output.v1.json` | Shared reviewer output schema. |
| `approval.input.v1.json` | Approval gate input schema. |
| `approval.output.v1.json` | Approval gate output schema. |
| `audit-block.protocol.md` | Audit block protocol specification. |
| `shared/unit-graph.schema.json` | Unit dependency graph schema. |
| `shared/quality-gates.schema.json` | Quality gates schema. |

---

## 6. Skills System

### 6.1 Custom Skills (`.agents/custom-skills/`)

| Skill | Purpose |
|-------|---------|
| `ai-architecture-cookbook` | 43 architecture standards via MCP tools or inline YAML fallback. |
| `browser-testing-with-devtools` | Browser testing using Chrome DevTools. |
| `code-review-and-quality` | Linting, building, and five-axis review. |
| `codegraph-aware-exploration` | Routes exploration to CodeGraph MCP tools. |
| `design-system-composer` | Composes UI from approved primitives, enforces tokens (Figma + Stitch). |
| `environment-detection` | Detects runtimes before installing. |
| `library-docs-with-context7` | Library documentation via Context7. |
| `requirements-intelligence` | Requirements analysis intelligence. |
| `secret-knowledge` | Secret management and detection. |
| `ui-constraint-validator` | Validates hardcoded spacing/radius/typography/color against tokens. |
| `validator-retry` | Static type/lint validation with compile-error-feedback loop (max 3 retries). |

### 6.2 Skill Resolution Order

1. `.agents/custom-skills/<name>/SKILL.md`
2. `.agents/skills/<name>/SKILL.md`
3. `~/.agents/skills/<name>/SKILL.md`

### 6.3 Autoskills
- `factory_custom_skills.py` — fetches community skills with SHA-256 verification
- `factory_skill_drift.py` — flags outdated skills
- `factory_skill_sync.py` — syncs framework skills (e.g., `react-best-practices`, `typescript-advanced-types`)

---

## 7. Infrastructure & Integrations

### 7.1 CodeGraph
- Semantic knowledge graph of codebase (tree-sitter parsed)
- `.codegraph/` directory with symbol index, callers, callees, impact analysis
- `codegraph_search`, `codegraph_node`, `codegraph_explore`, `codegraph_impact`, `codegraph_callers`, `codegraph_callees`
- Integration with `factory_codegraph.py` for lockfile-aware skill injection

### 7.2 Engram (Persistent Memory)
- `engram_mem_save` — save observations (bugfix, decision, architecture, pattern, config)
- `engram_mem_search` — search across all sessions
- `engram_mem_context` — get recent session context
- `engram_mem_session_summary` — end-of-session summary
- `engram_mem_judge` — resolve memory conflicts
- `engram_mem_compare` — compare two memories
- `engram_mem_doctor` — diagnostics
- `factory_knowledge_dashboard.py` — knowledge dashboard
- `factory_knowledge_promote.py` — knowledge promotion

### 7.3 Context Builder
- `factory_context_builder.py` — builds snapshots from audit.md, aidlc-state.md, manifest, timeline
- Depth modes: `minimal` (~200 tokens), `standard` (~800 tokens), `comprehensive` (~2000 tokens), `auto`
- Format: `compact` (YAML-like, saves ~40% tokens), `markdown`, `json`
- Caching with checksum-based invalidation

### 7.4 Token Bridge
- `factory_token_bridge.py` — prepares tokens.css, detects Tailwind, detects brownfield sources
- `factory_token_to_css.py` — Token → CSS compiler
- `factory_token_to_tailwind.py` — Token → Tailwind config compiler
- Integrates with design-system-composer skill

### 7.5 Figma & Stitch Integration
- `factory_figma_mcp.py` — Figma MCP integration
- `factory_stitch_mcp.py` — Stitch MCP integration
- `factory_stitch_snap.py` — Stitch snapshot

### 7.6 Context7 (Library Documentation)
- `context7_resolve-library-id` — resolves library names to IDs
- `context7_query-docs` — queries documentation and code examples
- Used by `library-docs-with-context7` skill

---

## 8. Quality Gates & Approval System

### 8.1 Approval Gates
- **Structured Approval Format** — per-unit approval with options: `approve`, `request_changes`, `cancel`
- **Human gates** — mandatory pause points for GitHub Copilot (sequential execution)
- **Command-boundary approval** — commits deferred to command boundary after explicit approval
- **Auto-commit** — only on explicit approval signals (`approve`, `go ahead`, `continue`, `lgtm`)

### 8.2 Validation Layers
- JSON Schema validation for input/output handoffs
- Lightweight validation for inline stages (required fields, artifact paths, structural invariants)
- Content validation (no fabricated timestamps, no rogue headers)
- AST drift detection for Python files (symbol-level changes)
- Wave collision pre-flight (`factory_conflict.py check-wave`)

### 8.3 Budget Management
- **Budget gates** — pre-flight check per unit (ok / downshift / skip / halt)
- **Budget deduct** — post-processing cost deduction
- **Cost estimation** — `factory_cost_estimate.py` pre-flight estimates
- **SLO checks** — `factory_slo_check.py` auto-runs quality reports

### 8.4 Security
- **Secret scanning** — `factory_secretscan.py` detects credentials in generated code
- **Security reviewer** — `reviewer-security` runs on Sonnet, OWASP-aware
- **SHA-256 verification** — for autoskills

---

## 9. Testing System

### 9.1 Test Suite (70+ test files)
- `tests/test_orchestrator_runtime.py` — Spawn loop, fast path, recovery, depth modes, compaction
- `tests/test_factory_context_builder.py` — Context builder (42 tests)
- `tests/test_factory_run.py` — Run manager
- `tests/test_factory_conflict.py` — Conflict resolution
- `tests/test_factory_validate.py` — Validation
- `tests/test_factory_skill_sync.py` — Skill sync
- `tests/test_factory_content_validate.py` — Content validation
- `tests/test_factory_build_cache.py` — Build cache
- `tests/test_factory_telemetry.py` — Telemetry
- `tests/test_install_aidlc.py` — Installer (126 tests)
- `tests/test_multi_tool_parity.py` — Cross-platform parity
- `tests/test_executor_conformance.py` — Executor conformance
- `tests/test_codegraph_integration.py` — CodeGraph integration
- And 50+ more...

### 9.2 Test Infrastructure
- pytest-based
- `conftest.py` — shared fixtures
- `smoke_executor.py` — smoke tests
- Cross-platform testing (Windows, macOS, Linux)

---

## 10. Installer & Distribution

### 10.1 Installation
- `install_aidlc.py` — cross-platform installer
- Copies rules + agents into target projects
- Flags: `--with-orchestrator`, `--with-codegraph`, `--with-architecture-cookbook`
- Virtual environment creation (`python3 -m venv .venv`)
- Windows support: `py` launcher, `cmd /c`, PowerShell fallbacks

### 10.2 Distribution
- Runtime files distributed via installer
- `core-workflow.md` — AIDLC constitution
- Platform-specific adaptations in thin wrappers

---

## 11. Cross-Cutting Agents

| Agent | Purpose |
|-------|---------|
| **conflict-resolver** | Detects path collisions and interface drift. Escalation-only (no auto-merge). |
| **knowledge-agent** | Persistent knowledge layer. Pre-spawn query + post-return save. Confidence/deprecation filtering, antipattern boosting. |

---

## 12. Observability & Telemetry

### 12.1 Audit Trail
- `aidlc-docs/audit.md` — chronological audit log
- Audit blocks: START, COMPLETE, non-spawn blocks
- `factory_run.py emit_audit_block` — atomic append with flock, dedupe, auto-creation
- Timeline events: `spawn_start`, `spawn_end`, `stage_complete`, `stage_failed`, `needs_human`

### 12.2 State Tracking
- `aidlc-docs/aidlc-state.md` — current stage, progress, issues
- `manifest.yaml` — run metadata, completed stages, unit waves, skill paths
- `factory_run.py` — state transitions (complete-stage, fail-stage)

### 12.3 Telemetry
- `factory_telemetry.py` — usage tracking, performance metrics
- `factory_cost_estimate.py` — cost tracking
- `factory_telemetry.py` — SLO monitoring

---

## 13. Multi-Platform Support

### 13.1 Supported Platforms
- **Claude Code** (`.claude/`) — `Task()` + `python3`, full parallel support
- **Cursor** (`.cursor/`) — `delegate` instead of `Task()`, sequential subagents
- **GitHub Copilot** (`.github/`) — `agent` tool, sequential execution, `python` (not `python3`)
- **OpenCode** (`.opencode/`) — `Task()` + `python3`, similar to Claude Code
- **Codex** (`.codex/`) — OpenAI Codex CLI/IDE support

### 13.2 Parity Requirements
- All platforms must have identical command set
- Runtime files are SSOT for protocol logic
- Wrappers contain only platform-specific adaptations
- Changes in one platform must be mirrored to all others

---

## 14. Hallucination Prevention Stack

| Layer | Mechanism |
|-------|-----------|
| **Validator-retry** | `tsc --noEmit` / `pyright` / `cargo check` after each code slice; max 3 retries |
| **Lockfile-aware skills** | `workspace-scout` parses lockfiles; only injects skills matching pinned versions |
| **Autoskills** | `factory_custom_skills.py` fetches community skills with SHA-256 verification |
| **Skill drift detector** | `factory_skill_drift.py` flags skills whose version range no longer covers latest stable |
| **Content validation** | `factory_content_validate.py` checks for fabricated content, rogue headers |
| **AST drift detection** | `factory_conflict.py` detects symbol-level changes in Python files |

---

## 15. Design System Pipeline

1. **Bootstrap** — `factory_ds_bootstrap.py` initializes design system
2. **Learn** — `factory_design_system_learn.py` learns from existing UI code
3. **Extract** — `factory_design_system_extract_brownfield.py` extracts tokens from existing CSS
4. **Resolve** — `factory_design_system_resolve.py` resolves token references
5. **Bridge** — `factory_token_bridge.py` prepares tokens.css, detects Tailwind
6. **Compile** — `factory_token_to_css.py` / `factory_token_to_tailwind.py` compile tokens
7. **Validate** — `ui-constraint-validator` skill validates against hardcoded values
8. **Figma** — `factory_figma_mcp.py` fetches tokens from Figma
9. **Stitch** — `factory_stitch_mcp.py` connects to Stitch design system

---

## 16. Complexity & Triage

- **Triage prefilter** — `factory_triage.py` classifies tasks as TINY/SMALL/MEDIUM/LARGE
- **Complexity analyzer** — `factory_complexity.py` estimates complexity
- **Tier routing** — SMALL tier skips stories + application-designer
- **Fast path** — TINY tasks bypass full pipeline (no unit decomposition, no reviewers)

---

## 17. Browser Testing

- **Chrome DevTools** — `browser-testing-with-devtools` skill
- **Lighthouse audit** — accessibility, SEO, best practices (excludes performance)
- **Performance trace** — `performance_start_trace` / `performance_stop_trace`
- **Heap snapshot** — `take_heapsnapshot` for memory leak detection

---

## 18. Git Workflow

- **Auto-commit** — deferred to command boundary after explicit approval
- **Commit messages** — conventional commits format
- **No auto-push** — user pushes manually after reviewing
- **Gitignore** — `.aidlc-orchestrator/runs/`, `.aidlc-orchestrator/knowledge/`, `.codegraph/` auto-added

---

## 19. Document Management

### Generated Documents
- `requirements.md` — Requirements specification
- `user-stories.md` — User stories and personas
- `execution-plan.md` — Execution plan with Mermaid diagram
- `unit-specs.md` — Unit specifications
- `design.md` — Design artifacts (5 files)
- `RELEASE_NOTES.md` — Release notes
- `CHANGELOG.md` — Updated changelog
- `ADRs/` — Architecture Decision Records
- `audit.md` — Complete audit trail
- `aidlc-state.md` — Current state

---

## 20. Meta-Operations

### 20.1 Self-Improvement
- `/factory-self` — Run AIDLC on its own codebase
- `factory_agent_discover.py` — Auto-discovers available subagents

### 20.2 Recovery
- `/factory-resume` — Resume from last checkpoint
- `/factory-replay` — Replay from specific stage
- **Recovery protocol** — critical vs non-critical stage handling

### 20.3 Context Management
- **Context compaction** — mandatory after inline stages
- **Context snapshots** — minimal/standard/comprehensive/auto depth
- **Knowledge query** — project + shared priors on every spawn
- **Knowledge save** — post-return with judgment heuristics

---

*End of ALL-FUNCTIONALITIES.md*
