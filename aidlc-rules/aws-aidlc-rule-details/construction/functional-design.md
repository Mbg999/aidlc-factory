# Functional Design

## Purpose
Detailed business logic design per unit (technology-agnostic).

Focus: business logic & algorithms, domain models, business rules & validation, data flow.

**Note**: Builds on Application Design (INCEPTION phase).

## Prerequisites
- Units generation complete; unit of work artifacts available
- Application Design recommended
- Execution plan must include this stage

## Agent Skills (MANDATORY — per stage-conventions.md protocol)
**You MUST load and follow these skills. Skipping is a workflow violation.**

- `api-and-interface-design/SKILL.md` — Contract-first design + boundary validation for interfaces. **Key process**: define contracts before implementation, apply Hyrum's Law, validate at boundaries.

**Inline fallback** (if SKILL.md files not installed):
1. Define API contracts (request/response schemas) before any implementation
2. Apply boundary validation rules at every interface
3. Document assumptions — anything not in the contract is not guaranteed

## Steps

### Step 1: Analyze Unit Context
- Read unit definition from `aidlc-docs/inception/application-design/<run-id>-unit-of-work.md`
- Read assigned stories from `aidlc-docs/inception/application-design/<run-id>-unit-of-work-story-map.md`

### Step 2: Create Functional Design Plan
- Focus: business logic, domain models, business rules
- Save to `aidlc-docs/construction/plans/<run-id>-{unit-name}-functional-design-plan.md`

### Step 3: Generate Questions

**Question categories**:
- **Business Logic Modeling** — core entities, workflows, data transforms, processes
- **Domain Model** — domain concepts, entity relations, data structures
- **Business Rules** — decision rules, validation logic, constraints, policies
- **Data Flow** — inputs, outputs, transforms, persistence needs
- **Integration Points** — external system interactions, APIs, data exchange
- **Error Handling** — error scenarios, validation failures, exception handling
- **Business Scenarios** — edge cases, alternative flows
- **Frontend Components** (if applicable) — UI components, interactions, state, forms

### Step 4: Collect Answers and Resolve Ambiguities
*(Per stage-conventions.md protocol)*

### Step 5: Generate Artifacts
- `aidlc-docs/construction/{unit-name}/functional-design/<run-id>-business-logic-model.md`
- `aidlc-docs/construction/{unit-name}/functional-design/<run-id>-business-rules.md`
- `aidlc-docs/construction/{unit-name}/functional-design/<run-id>-domain-entities.md`
- If UI unit: `aidlc-docs/construction/{unit-name}/functional-design/<run-id>-frontend-components.md`
  - Component hierarchy, props/state, interaction flows, form validation, API integration

### Step 6: Present Completion (emoji: 🔧)
Artifact path: `aidlc-docs/construction/{unit-name}/functional-design/`
