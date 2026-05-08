# Units Generation

## Purpose
Decompose system into manageable units of work (two parts: Planning → Generation).

**DEFINITION**: Unit of work = logical grouping of stories. For microservices → deployable service. For monoliths → application with logical modules.

**Terminology**: "Service" = deployable component, "Module" = logical grouping inside service, "Unit of Work" = planning context.

## Prerequisites
- Workspace Detection complete
- Requirements Analysis recommended
- User Stories recommended
- Application Design REQUIRED
- Execution plan must indicate this stage

## Steps

---

### PART 1: PLANNING

#### Step 1: Create Unit of Work Plan
- Decompose system into manageable development units
- Save to `aidlc-docs/inception/plans/unit-of-work-plan.md`

#### Step 2: Mandatory Artifacts (include in plan)
- [ ] `unit-of-work.md` — unit definitions and responsibilities
- [ ] `unit-of-work-dependency.md` — dependency matrix
- [ ] `unit-of-work-story-map.md` — story-to-unit mappings
- [ ] **Greenfield only**: Document code organization strategy (see code-generation.md)
- [ ] Validate unit boundaries and dependencies
- [ ] Ensure all stories assigned to units

#### Step 3: Generate Questions

**Question categories**:
- **Story Grouping** — grouping strategy, story affinity, logical clustering
- **Dependencies** — integration approach, shared resources, inter-unit communication
- **Team Alignment** — team structure, ownership boundaries, collaboration
- **Technical Considerations** — scalability/deployment differences across units
- **Business Domain** — domain boundaries, bounded contexts, capability alignment
- **Code Organization (Greenfield multi-unit only)** — deployment model, directory structure

#### Step 4: Collect Answers and Resolve Ambiguities
*(Per stage-conventions.md protocol)*

#### Step 5: Get Plan Approval
- Present: "Unit of work plan complete. Review `aidlc-docs/inception/plans/unit-of-work-plan.md`. Ready to proceed?"
- Do NOT proceed to generation without approval

---

### PART 2: GENERATION

#### Step 6: Execute Plan
- Read plan, identify next unchecked step
- Execute step, generate artifacts per approved decomposition
- Mark `[x]` immediately after each step

#### Step 7: Verify Completion
- All plan steps marked `[x]`
- All unit artifacts generated
- All stories assigned to units

#### Step 8: Present Completion (emoji: 🔧)
Artifact path: `aidlc-docs/inception/application-design/`

---

## Critical Rules

**Planning**: Generate context-relevant questions only; resolve ALL ambiguities; get approval before generation.

**Generation**: Follow plan exactly; no deviations; update checkboxes; use approved approach; verify completion.
