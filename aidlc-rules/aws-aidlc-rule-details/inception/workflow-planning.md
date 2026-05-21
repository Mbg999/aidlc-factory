# Workflow Planning

**Purpose**: Determine which stages to execute; create comprehensive execution plan.

**Always Execute**: Runs after requirements (and optionally stories) are understood.

## Agent Skills (MANDATORY — per stage-conventions.md protocol)
**You MUST load and follow these skills. Skipping is a workflow violation.**

- `planning-and-task-breakdown/SKILL.md` — Decompose execution plan into small, verifiable tasks with acceptance criteria and dependency ordering. **Key process**: vertical slices, not horizontal layers; each task independently verifiable.
- `requirements-intelligence/SKILL.md` — Plan-stage variant only. Runs the pre-mortem rubric against the produced plan artifact: where will this plan break first, which unit boundary forces a re-plan, which task has the weakest acceptance criterion. Emit ≤3 plan-risk questions appended to the approval surface (NOT a separate questions file). Skip on trivial plans (single-unit AND every task has ≥2 acceptance criteria) — emit `status: N/A` in skill_compliance with evidence `"trivial plan: skipped per SKILL.md plan-stage variant rule"`.

**Inline fallback** (if SKILL.md files not installed):
1. Slice work vertically (complete path per task, not layer-by-layer)
2. Each task has: acceptance criteria, verification steps, dependencies
3. Add checkpoints between phases
4. Before approval: run a plan-stage pre-mortem — list where the plan is most likely to break during construction (integration boundaries, weakest acceptance criterion, riskiest unit boundary) and append ≤3 plan-risk questions to the approval surface.
5. Present plan for human review before execution

## Step 1: Load All Prior Context

- **Reverse Engineering** (if brownfield): architecture.md, component-inventory.md, technology-stack.md
- **Requirements Analysis**: requirements.md, requirement-verification-questions.md
- **User Stories** (if executed): stories.md, personas.md

## Step 2: Scope and Impact Analysis

### 2.1 Transformation Scope (Brownfield Only)
- Single component vs architectural transformation
- Infrastructure vs application changes
- Cross-package impact (CDK, shared models, client libraries, tests)

### 2.2 Change Impact Assessment
Evaluate each:
- User-facing changes (UX impact?)
- Structural changes (architecture?)
- Data model changes (schemas?)
- API changes (contracts?)
- NFR impact (performance, security, scalability?)

### 2.3 Component Relationships (Brownfield Only)
Map: primary component, infrastructure, shared, dependent, supporting components.
Per component: change type (Major/Minor/Config), reason, priority (Critical/Important/Optional).

### 2.4 Risk Assessment
- **Low**: Isolated, easy rollback, well-understood
- **Medium**: Multiple components, moderate rollback
- **High**: System-wide, complex rollback, unknowns
- **Critical**: Production-critical, difficult rollback

## Step 3: Phase Determination

| Stage | Execute IF | Skip IF |
|-------|-----------|---------|
| **User Stories** | Multiple personas, UX impact, acceptance criteria needed, team collab | Internal refactor, clear bug fix, infra-only |
| **Application Design** | New components/services, methods/rules definition, service layer needed | Within existing boundaries, no new components |
| **Units Generation** | New data models, API changes, complex logic, multi-package, IaC updates | Simple logic, UI-only, config updates |
| **Functional Design** | Complex business logic, domain models needed | Straightforward implementation |
| **NFR Requirements** | Performance/security/scalability/observability needs | Existing NFR sufficient, no new reqs |
| **NFR Design** | NFR patterns needed (resilience, scaling, caching) | Simple NFRs handled in code |
| **Infrastructure Design** | New infra services, deployment changes | Using existing infra unchanged |

## Step 4: Adaptive Detail
See [depth-levels.md](../common/depth-levels.md). All defined artifacts created; detail level adapts to complexity.

## Step 5: Multi-Module Coordination (Brownfield Only)

If multiple modules/packages affected:
- Analyze dependencies (build-time vs runtime)
- Determine update sequence (critical path)
- Identify parallelization opportunities
- Plan testing strategy and rollback

## Step 6: Generate Workflow Visualization

Create Mermaid flowchart showing all phases with EXECUTE/SKIP/COMPLETED status.

**Styling**:
- Completed/Always: green (`#4CAF50`)
- Conditional EXECUTE: orange (`#FFA726`, dashed)
- Conditional SKIP: gray (`#BDBDBD`, dashed)
- Start/End: purple (`#CE93D8`)
- Containers: light fills (INCEPTION: `#BBDEFB`, CONSTRUCTION: `#C8E6C9`, OPERATIONS: `#FFF59D`)

## Step 7: Create Execution Plan Document

Save to `aidlc-docs/inception/plans/<run-id>-execution-plan.md` with (where `<run-id>` is the current run identifier, e.g. `2026-05-12T14-23-00Z-add-pagination-api`):
- Analysis summary (scope, impact, risk)
- Workflow Mermaid visualization
- Phase checklist with EXECUTE/SKIP + rationale per stage
- Package change sequence (brownfield)
- Success criteria

## Step 8: Initialize State Tracking

Update `aidlc-docs/aidlc-state.md` with: project info, execution plan summary, stage progress checklist, current status.

## Step 9: Skills Discovery (Conditional — Greenfield Only)

**Execute IF**: Skills are not yet installed AND greenfield project.
**Skip IF**: Skills already installed in `.agents/skills/`.

- Check `.agents/skills/` for installed skills
- If missing, recommend running the installer:
  ```bash
  python aidlc-scripts/install_aidlc.py --tool <tool> --with-agent-skills --dest .
  ```
- Write `aidlc-docs/<run-id>-skills-coverage.md` listing installed vs missing skills
- Validate per `common/ascii-diagram-standards.md`; log in audit.md

## Step 10: Present Completion (emoji: 📋)

Include in completion message:
- Request summary, existing system summary (if brownfield)
- Risk level, impact, components affected
- Recommended stages to EXECUTE with rationale
- Stages to SKIP with rationale
- Package update sequence (if brownfield multi-package)
- Estimated timeline

Extra options: offer to add skipped stages.

## Step 11: Handle Response
- Approved → proceed to next stage
- Changes requested → update plan, re-confirm
- Force include/exclude → update accordingly

## Step 12: Log in audit.md
Log approval prompt, user response, timestamp, status.
