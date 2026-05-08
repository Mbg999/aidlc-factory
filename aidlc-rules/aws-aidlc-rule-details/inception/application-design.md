# Application Design

## Purpose
High-level components + service-layer design. Identifies components, defines interfaces (no business logic), designs service orchestration, defines dependencies.

**Note**: Business logic defined later in Functional Design (CONSTRUCTION).

## Prerequisites
- Workspace Detection complete
- Requirements Analysis recommended
- User stories recommended
- Execution plan must mark this stage

## Agent Skills
- `api-and-interface-design/SKILL.md` — Contract-first design, Hyrum's Law, boundary validation.
- `context-engineering/SKILL.md` — Pack prior artifacts, verify context quality before decisions.

## Steps

### Step 1: Analyze Context
- Read `aidlc-docs/inception/requirements/requirements.md` and `aidlc-docs/inception/user-stories/stories.md`
- Identify key business capabilities + functional areas

### Step 2: Create Application Design Plan
- Cover: components, responsibilities, methods, services, dependencies
- Save to `aidlc-docs/inception/plans/application-design-plan.md`

### Step 3: Mandatory Artifacts (include in plan)
- [ ] `components.md` — component definitions + responsibilities
- [ ] `component-methods.md` — method signatures (business rules in Functional Design)
- [ ] `services.md` — service definitions + orchestration patterns
- [ ] `component-dependency.md` — dependency relationships + communication patterns
- [ ] Validate design completeness

### Step 4: Generate Questions

**Question categories**:
- **Component Identification** — boundaries, organization, grouping strategies
- **Component Methods** — signatures, I/O expectations, interface contracts
- **Service Layer Design** — orchestration, boundaries, coordination patterns
- **Component Dependencies** — communication, dependency management, coupling
- **Design Patterns** — architectural style, pattern choices, constraints

### Step 5: Collect Answers and Resolve Ambiguities
*(Per stage-conventions.md protocol — includes mandatory follow-up for vague answers)*

### Step 6: Generate Artifacts
- `aidlc-docs/inception/application-design/components.md`
- `aidlc-docs/inception/application-design/component-methods.md`
- `aidlc-docs/inception/application-design/services.md`
- `aidlc-docs/inception/application-design/component-dependency.md`
- `aidlc-docs/inception/application-design/application-design.md` (consolidated)

### Step 7: Present Completion (emoji: 🏗️)
Artifact path: `aidlc-docs/inception/application-design/`

Extra option in completion message:
- If Units Generation is skipped: offer to add it
