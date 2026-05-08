# Functional Design

## Purpose
Detailed business logic design per unit (technology-agnostic).

Focus: business logic & algorithms, domain models, business rules & validation, data flow.

**Note**: Builds on Application Design (INCEPTION phase).

## Prerequisites
- Units generation complete; unit of work artifacts available
- Application Design recommended
- Execution plan must include this stage

## Agent Skills
- `api-and-interface-design/SKILL.md` — Contract-first design + boundary validation for interfaces.

## Steps

### Step 1: Analyze Unit Context
- Read unit definition from `aidlc-docs/inception/application-design/unit-of-work.md`
- Read assigned stories from `aidlc-docs/inception/application-design/unit-of-work-story-map.md`

### Step 2: Create Functional Design Plan
- Focus: business logic, domain models, business rules
- Save to `aidlc-docs/construction/plans/{unit-name}-functional-design-plan.md`

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
- `aidlc-docs/construction/{unit-name}/functional-design/business-logic-model.md`
- `aidlc-docs/construction/{unit-name}/functional-design/business-rules.md`
- `aidlc-docs/construction/{unit-name}/functional-design/domain-entities.md`
- If UI unit: `aidlc-docs/construction/{unit-name}/functional-design/frontend-components.md`
  - Component hierarchy, props/state, interaction flows, form validation, API integration

### Step 6: Present Completion (emoji: 🔧)
Artifact path: `aidlc-docs/construction/{unit-name}/functional-design/`
