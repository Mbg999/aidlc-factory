# NFR Requirements

## Purpose
Define non-functional requirements and tech-stack decisions per unit.

## Prerequisites
- Functional design complete for unit
- Execution plan indicates this stage

## Agent Skills (MANDATORY — per stage-conventions.md protocol)
**You MUST load and follow these skills. Skipping is a workflow violation.**

- `performance-optimization/SKILL.md` — Measure-first: Core Web Vitals targets, profiling, performance budgets. **Key process**: define measurable targets before designing solutions.
- `security-and-hardening/SKILL.md` — OWASP Top 10 prevention, three-tier boundary system, threat checklist. **Key process**: identify threat surfaces, apply boundary rules.

**Inline fallback** (if SKILL.md files not installed):
1. Define measurable NFR targets (response times, throughput, error rates)
2. Identify security threat surfaces (OWASP Top 10 checklist)
3. Specify boundary validation rules for each interface
4. Document performance budgets with specific metrics

## Steps

### Step 1: Analyze Functional Design
- Read from `aidlc-docs/construction/{unit-name}/functional-design/`
- Assess business logic complexity

### Step 2: Create NFR Requirements Plan
- Focus: scalability, performance, availability, security
- Save to `aidlc-docs/construction/plans/{unit-name}-nfr-requirements-plan.md`

### Step 3: Generate Questions

**Question categories**:
- **Scalability** — expected load, growth patterns, scaling triggers, capacity
- **Performance** — response times, throughput, latency, benchmarks
- **Availability** — uptime, disaster recovery, failover, business continuity
- **Security** — data protection, compliance, auth, authorization, threat models
- **Tech Stack** — preferences, constraints, existing systems, integrations
- **Reliability** — error handling, fault tolerance, monitoring, alerting
- **Maintainability** — code quality, documentation, testing, operations
- **Usability** — UX, accessibility, interface requirements

### Step 4: Collect Answers and Resolve Ambiguities
*(Per stage-conventions.md protocol)*

### Step 5: Generate Artifacts
- `aidlc-docs/construction/{unit-name}/nfr-requirements/nfr-requirements.md`
- `aidlc-docs/construction/{unit-name}/nfr-requirements/tech-stack-decisions.md`

### Step 6: Present Completion (emoji: 📊)
Artifact path: `aidlc-docs/construction/{unit-name}/nfr-requirements/`
