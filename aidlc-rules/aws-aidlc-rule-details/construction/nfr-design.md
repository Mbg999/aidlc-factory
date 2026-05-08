# NFR Design

## Purpose
Incorporate NFRs into unit design via patterns and logical components.

## Prerequisites
- NFR requirements complete for unit
- Execution plan indicates this stage

## Agent Skills
- `security-and-hardening/SKILL.md` — Security patterns, auth design, secrets management.
- `performance-optimization/SKILL.md` — Perf budgets, anti-pattern detection, profiling.

## Steps

### Step 1: Analyze NFR Requirements
- Read from `aidlc-docs/construction/{unit-name}/nfr-requirements/`
- Identify scalability, performance, availability, security needs

### Step 2: Create NFR Design Plan
- Focus: design patterns and logical components
- Save to `aidlc-docs/construction/plans/{unit-name}-nfr-design-plan.md`

### Step 3: Generate Questions

**Question categories**:
- **Resilience Patterns** — fault tolerance, retry strategies, failure recovery
- **Scalability Patterns** — scaling mechanisms, load boundaries, growth projections
- **Performance Patterns** — optimization strategy, latency targets, throughput
- **Security Patterns** — security approach, threat model, compliance constraints
- **Logical Components** — infra components (queues, caches, circuit breakers) and integration patterns

### Step 4: Collect Answers and Resolve Ambiguities
*(Per stage-conventions.md protocol)*

### Step 5: Generate Artifacts
- `aidlc-docs/construction/{unit-name}/nfr-design/nfr-design-patterns.md`
- `aidlc-docs/construction/{unit-name}/nfr-design/logical-components.md`

### Step 6: Present Completion (emoji: 🎨)
Artifact path: `aidlc-docs/construction/{unit-name}/nfr-design/`
