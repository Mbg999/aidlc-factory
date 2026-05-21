# NFR Design

## Purpose
Incorporate NFRs into unit design via patterns and logical components.

## Prerequisites
- NFR requirements complete for unit
- Execution plan indicates this stage

## Agent Skills (MANDATORY — per stage-conventions.md protocol)
**You MUST load and follow these skills. Skipping is a workflow violation.**

- `security-and-hardening/SKILL.md` — Security patterns, auth design, secrets management. **Key process**: design auth/authz, secrets handling, input validation at all boundaries.
- `performance-optimization/SKILL.md` — Perf budgets, anti-pattern detection, profiling. **Key process**: identify hot paths, set budgets, verify no anti-patterns.

**Inline fallback** (if SKILL.md files not installed):
1. Design authentication & authorization flows with least-privilege
2. Specify secrets management approach (no hardcoded secrets)
3. Define input validation at every boundary
4. Identify performance-critical paths and set measurable budgets

## Steps

### Step 1: Analyze NFR Requirements
- Read from `aidlc-docs/construction/{unit-name}/nfr-requirements/`
- Identify scalability, performance, availability, security needs

### Step 2: Create NFR Design Plan
- Focus: design patterns and logical components
- Save to `aidlc-docs/construction/plans/<run-id>-{unit-name}-nfr-design-plan.md`

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
- `aidlc-docs/construction/{unit-name}/nfr-design/<run-id>-nfr-design-patterns.md`
- `aidlc-docs/construction/{unit-name}/nfr-design/<run-id>-logical-components.md`

### Step 6: Present Completion (emoji: 🎨)
Artifact path: `aidlc-docs/construction/{unit-name}/nfr-design/`
