# Infrastructure Design

## Purpose
Map logical components to infrastructure services for deployment.

## Prerequisites
- Functional Design complete for unit
- NFR Design recommended (maps logical components)
- Execution plan indicates this stage

## Agent Skills (MANDATORY — per stage-conventions.md protocol)
**You MUST load and follow these skills. Skipping is a workflow violation.**

- `ci-cd-and-automation/SKILL.md` — Shift Left, feature flags, quality-gate pipeline patterns. **Key process**: design pipeline with quality gates, feature flags for safe rollout.

**Inline fallback** (if SKILL.md files not installed):
1. Design CI pipeline: lint → test → build → deploy
2. Include quality gates that block deployment on failures
3. Plan feature flag strategy for safe rollout
4. Shift security/testing left (run early in pipeline)

## Steps

### Step 1: Analyze Design Artifacts
- Read functional design from `aidlc-docs/construction/{unit-name}/functional-design/`
- Read NFR design from `aidlc-docs/construction/{unit-name}/nfr-design/` (if exists)
- Identify logical components needing infrastructure

### Step 2: Create Infrastructure Design Plan
- Map components to services (AWS, Azure, GCP, on-premise)
- Save to `aidlc-docs/construction/plans/{unit-name}-infrastructure-design-plan.md`

### Step 3: Generate Questions

**Question categories**:
- **Deployment Environment** — cloud provider, environment setup, deployment targets
- **Compute** — service choices, sizing, scaling requirements
- **Storage** — database selection, storage patterns, data lifecycle
- **Messaging** — queuing services, event-driven patterns, async processing
- **Networking** — load balancing, API gateway, network topology
- **Monitoring** — observability tooling, alerting, logging
- **Shared Infrastructure** — sharing strategy, multi-tenancy, resource isolation

### Step 4: Collect Answers and Resolve Ambiguities
*(Per stage-conventions.md protocol)*

### Step 5: Generate Artifacts
- `aidlc-docs/construction/{unit-name}/infrastructure-design/infrastructure-design.md`
- `aidlc-docs/construction/{unit-name}/infrastructure-design/deployment-architecture.md`
- If shared infra: `aidlc-docs/construction/shared-infrastructure.md`

### Step 6: Present Completion (emoji: 🏢)
Artifact path: `aidlc-docs/construction/{unit-name}/infrastructure-design/`
