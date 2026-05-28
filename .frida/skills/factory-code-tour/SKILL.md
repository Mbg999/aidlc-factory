---
name: factory-code-tour
description: Dependency-ordered codebase tour — foundations to entry points. Works in any AIDLC-installed project.
---

# factory-code-tour — AIDLC Codebase Tour

Read-only. Never modify files or create commits.

## Step 1 — Profile

Ask the user:
1. Role: developer / architect / PM / new hire / external contributor
2. Goal: understand the system / find where to add a feature / debug / onboarding

Adapt emphasis: PM -> top-layer flows only; new hire -> full tour + "why" per layer;
architect -> extension points.

## Step 2 — Tour Generation

Use `codegraph-aware-exploration` skill if CodeGraph is available (T1->T2->T3->T4->T5).

**If CodeGraph unavailable:** use Glob + Grep to find entry files
(`main.*`, `app.*`, `index.*`), trace 2-3 flows manually as linear chains,
note `[CodeGraph] not available -- run: codegraph init -i`.

## Step 3 — Output format

```
Tour -- N layers, M stops

Layer 0 -- Foundations (start here)
  1. utils/config.py::load()    -- loads env config at boot
  2. utils/db.py::connect()     -- initialises connection pool

Layer N -- Entry points (read last)
  M. main.py::app               -- application bootstrap
```

One-line description per stop.

## Step 4 — Close

Max 4 bullets: non-obvious conventions + one concrete next action per their role.

End with: _"Ask me to expand any stop or trace a specific flow."_
