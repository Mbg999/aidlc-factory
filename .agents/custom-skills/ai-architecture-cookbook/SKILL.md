---
name: ai-architecture-cookbook
description: Integrates the AI Architecture Cookbook (43 YAML standards) into AIDLC stages for pattern recommendation, checklist verification, and decision tree evaluation via MCP tools or inline YAML fallback.
stages: [workspace-scout, reverse-engineer, requirements-analyst, story-writer, workflow-planner, unit-decomposer, code-generator, reviewer-code, reviewer-security, reviewer-performance, ship-agent]
---

# AI Architecture Cookbook

Integrates 43 machine-readable architectural standards from the AI Architecture
Cookbook into AIDLC factory stages.

## Process (mandatory order)

### Step 0 — Detect MCP availability

Check for `.ai-architecture-cookbook/mcp-server/dist/server.js` at the project
root. If the compiled MCP server exists, flag the MCP tools as available. If
not, use the inline YAML fallback for all steps below.

Log: `[Skill] ai-architecture-cookbook: MCP {detected|unavailable} — using {mcp|yaml-fallback}`

### Step 1 — Stage selection

Each stage maps to specific Cookbook tools:

| Stage | Primary Tool | When to Call | Budget |
|-------|-------------|--------------|--------|
| `workspace-scout` | `recommend_pattern` | When project profile includes `has_auth`, `scale: enterprise`, or `scale: massive` | ≤ 2 calls |
| `reverse-engineer` | `recommend_pattern` + `query_standard` | When brownfield and any domain detected in existing code patterns | ≤ 3 calls |
| `requirements-analyst` | `search_standards` | When user mentions architectural domains (auth, API, infra, security) | ≤ 3 calls |
| `story-writer` | `search_standards` | When stories reference architectural concerns (auth, API, compliance) | ≤ 2 calls |
| `workflow-planner` | `recommend_pattern` | When plan must consider architecture patterns for the feature scope | ≤ 3 calls |
| `unit-decomposer` | `get_decision_tree` | When decomposing into units that span different architectural domains | ≤ 2 calls |
| `code-generator` | `get_decision_tree` → `query_standard` → `get_checklist` | Before writing code in a relevant domain | ≤ 5 calls |
| `reviewer-code` | `get_checklist(severity: high)` | During five-axis review | ≤ 3 calls |
| `reviewer-security` | `get_checklist(severity: critical)` | During OWASP scan | ≤ 3 calls |
| `reviewer-performance` | `query_standard(performance-optimization)` | During hot-path analysis | ≤ 2 calls |
| `ship-agent` | `query_standard(compliance-data-privacy)` + `query_standard(secure-sdlc)` | During release notes compliance section | ≤ 3 calls |

**Total call budget across all stages per run:** ≤ 25 calls.

### Step 2 — Call the MCP tool

When MCP is available, use the tool-specific invocation:

**recommend_pattern:**
```
Call MCP tool `recommend_pattern` with:
- context: { key: value pairs matching context_inputs }
- domains: [optional domain list]
- include_trace: true (optional)
- format: "human" | "machine" | "short"
```

**search_standards:**
```
Call MCP tool `search_standards` with one of:
- query: "search terms"
- tags: ["tag1", "tag2"]
- categories: ["category-id"]
```

**get_decision_tree:**
```
Call MCP tool `get_decision_tree` with:
- domain: "domain-id"
```

**get_checklist:**
```
Call MCP tool `get_checklist` with:
- domain: "domain-id"
- severity: "critical" | "high" | "medium" | "low" (optional)
```

**query_standard:**
```
Call MCP tool `query_standard` with:
- domain: "domain-id"
- category: "category-id" (optional)
```

**Batch calls by domain when possible** — multiple domains in a single `get_checklist`
or `recommend_pattern` call is cheaper than separate calls.

### Step 3 — Apply the result

- **Pattern recommendations** → include in code-generation plan output. Cite the
  Cookbook standard ID (e.g., `foundational/authentication/authentication.yaml`).
- **Decision trees** → evaluate context inputs against the tree. Log the matched
  node. If no match, use the fallback pattern.
- **Checklist items** → include in review reports with severity and Cookbook
  standard ID citations. Filter by severity (critical/high) for reviewers.
- **Standard details** → surface relevant implementation guidelines and anti-patterns.

**Empty recommendation:** if `recommend_pattern` returns no recommendations for
a domain, log `[Skill] ai-architecture-cookbook: no recommendation for <domain>` and
proceed without blocking.

### Step 4 — Audit entries

Emit at least one `[Skill]` audit entry per stage when Cookbook was consulted.
Format: `[Skill] ai-architecture-cookbook: <tool> called for <domain> — <result-summary>`

---

## Inline YAML Fallback (MCP unreachable)

When the MCP server is not available, read YAML standards directly from disk.
This covers the same 5 tools with equivalent functionality.

**Standards path:** `./.ai-architecture-cookbook/{category}/{domain}/{domain}.yaml`

**Categories and domains:**

| Category | Domains |
|----------|---------|
| `foundational` | authentication, api-design, error-handling, logging-observability, data-persistence, input-validation, messaging-events, configuration-management, authorization, session-management, secrets-management |
| `application-architecture` | layered-architecture, service-architecture, domain-driven-design, state-management, dependency-injection, repository-pattern, design-patterns, resilience-chaos-engineering, feature-flags |
| `infrastructure` | containerization, orchestration, ci-cd, infrastructure-as-code, cloud-architecture, database-migration, api-gateway-edge-security |
| `security-quality` | encryption, rate-limiting, testing-strategies, code-quality, performance-optimization, accessibility, client-platform-security, secure-sdlc, compliance-data-privacy, security-monitoring |
| `integration-data` | third-party-integration, webhooks, file-storage, search, data-transformation, versioning |

**Fallback for each tool:**

- **recommend_pattern** → Read YAML entries for relevant domains. Parse `decision_tree[]`
  nodes and match against provided context using `context_inputs[]` names. Apply
  `decision_metadata.fallback` when no node matches.

- **search_standards** → Scan `meta.tags[]` and `meta.description` across all entries
  for keyword matches. Sort by tag match count.

- **get_decision_tree** → Read single entry YAML. Return `decision_tree[]` and
  `context_inputs[]`.

- **get_checklist** → Read single entry YAML. Return `checklist[]` array. Optionally
  filter by `severity` field.

- **query_standard** → Read single entry YAML. Return full content with `patterns[]`,
  `anti_patterns[]`, `examples[]`, `prompt_recipes[]`, and `security_hardening`.

**Fallback audit entry:** `[Skill] ai-architecture-cookbook: YAML-fallback used — MCP unreachable`



## When NOT to Use (skip conditions)

Skip the Cookbook when:

- The task is a **trivial single-file change** (typo fix, config tweak, minor refactor)
- **No architectural decisions are involved** (e.g., updating docs, running tests)
- The MCP server is unreachable AND the relevant domain has **no YAML file on disk**
- The task has **already been verified** against Cookbook in a previous stage
- The stage agent's call budget is exhausted (≤ 5 calls per invocation per the budget column in Step 1)

**Defer to the stage agent's judgment:** if the cost of a Cookbook call exceeds
the value it provides for a trivial task, skip it.

---

## Standards Catalog (quick reference)

43 machine-readable YAML standards across 5 categories:

| Category | Count | Key domains |
|----------|-------|------------|
| Foundational | 11 | auth, api-design, error-handling, logging, data-persistence |
| Application Architecture | 9 | layered-architecture, service-architecture, DDD, state-management |
| Infrastructure | 7 | containerization, orchestration, ci-cd, IaC, cloud-architecture |
| Security & Quality | 10 | encryption, rate-limiting, testing-strategies, code-quality |
| Integration & Data | 6 | third-party-integration, webhooks, file-storage, search |

Each entry contains: patterns, anti-patterns, decision tree, checklist, examples,
prompt recipes, security hardening, compliance considerations.

---

## Verification (objective gates)

- [ ] `[Skill]` audit entry emitted for every stage that consulted Cookbook
- [ ] Call budget respected (≤ 5 per invocation, ≤ 25 per run)
- [ ] Empty MCP recommendation → logged, not blocking
- [ ] MCP unreachable → inline YAML fallback used (not crashed)
- [ ] Cookbook standard ID cited in code-generation plan or review report
- [ ] Checklist items filtered by severity for reviewer stages
- [ ] Skip conditions documented when Cookbook is explicitly not used

## Common Rationalizations (reject these)

- "The standard is too generic for this specific case" → Decision trees handle
  context-specific branching. Apply your context inputs before concluding.
- "I already know this pattern" → Cookbook provides anti-patterns and checklists
  that catch edge cases you might miss.
- "The MCP call might fail" → Inline YAML fallback exists for exactly this reason.
  Always attempt the MCP call first.
- "This task is too small" → Check the skip conditions in Step 1 before deciding.
  Single-file typos are valid skips. Feature work is not.
- "I'll batch later" → Batching by domain within one call is correct. Deferring
  to a later stage is NOT — each stage has its own call budget.

## Red Flags (escalate)

- **MCP server unreachable for 3+ consecutive calls** → report as `[Skill] ai-architecture-cookbook: MCP degraded — 3+ consecutive failures. Switching to YAML fallback for remainder of run.`
- **Recommendation contradicts another source** → log both recommendations and
  set `status: needs_human` with the conflict described.
- **Decision tree returns no match AND no fallback** → log the missing domain and
  proceed with minimal guidance.
- **Call budget exceeded** → log warning and skip remaining Cookbook calls for this stage.
- **Cross-domain mismatch** — if a recommendation references a domain that doesn't
  match the task context, log and skip. Use domain metadata to validate.
