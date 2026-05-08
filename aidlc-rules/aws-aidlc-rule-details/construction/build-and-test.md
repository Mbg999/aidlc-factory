# Build and Test

**Purpose**: Build units and run tests to validate code generation output.

## Prerequisites
- Code generation complete for all units
- Project ready for build & testing

## Agent Skills
(Per stage-conventions.md protocol)
- `debugging-and-error-recovery/SKILL.md` — Scientific debugging for build/test failures
- `browser-testing-with-devtools/SKILL.md` *(UI projects only)* — DevTools visual/network/console testing
- `test-driven-development/SKILL.md` — Test pyramid 80/15/5, mutation testing, coverage thresholds

---

## Steps

### Step 1: Analyze Testing Requirements
Determine strategy per project needs:
- **Unit tests**: Already generated during code generation
- **Integration tests**: Cross-unit/service interactions
- **Performance tests**: Load, stress, scalability (if NFRs require)
- **Contract tests**: API contracts between services (microservices)
- **Security tests**: Vulnerability scanning, auth testing
- **E2E tests**: Complete user workflows

### Step 2: Generate Build Instructions
Create `aidlc-docs/construction/build-and-test/build-instructions.md`:
- Prerequisites (tool, deps, env vars, system reqs)
- Build steps (install deps → configure env → build all → verify success)
- Troubleshooting (dependency errors, compilation errors)

### Step 3: Generate Unit Test Instructions
Create `aidlc-docs/construction/build-and-test/unit-test-instructions.md`:
- Run command, expected results, coverage target, fix procedure for failures

### Step 4: Generate Integration Test Instructions
Create `aidlc-docs/construction/build-and-test/integration-test-instructions.md`:
- Test scenarios (unit interactions), env setup, execution, cleanup

### Step 5: Generate Performance Test Instructions (If Applicable)
Create `aidlc-docs/construction/build-and-test/performance-test-instructions.md`:
- Requirements (response time, throughput, concurrency, error rate)
- Load tests, stress tests, analysis, optimization steps

### Step 6: Generate Additional Tests (As Needed)
Based on project requirements, generate:
- Contract tests (microservices)
- Security tests
- E2E tests

### Step 7: Generate Test Summary
Create `aidlc-docs/construction/build-and-test/build-and-test-summary.md`:
- Build status + artifacts
- Results per test category (unit, integration, performance, contract, security, e2e)
- Overall status: ready for Operations?

### Step 8: Update State
Mark Build and Test complete in `aidlc-state.md`.

### Step 9: Present Completion (Per stage-conventions.md protocol, emoji: 🔨)
Summary includes: build status, test results by category, generated instruction files.
Next stage options: Request Changes / Approve & Continue to Operations

### Step 10: Log in audit.md
Build status, test status, files generated.
