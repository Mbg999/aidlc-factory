# /factory-code-tour

Read-only. Never modify files or create commits.

## Step 1 — Profile

Ask in English, adapt to the user's role and goal:
- Role: developer / architect / PM / new hire / external contributor
- Goal: understand system / find where to add feature / debug / onboarding

## Step 2 — Tour Generation

Use CodeGraph if available (`codegraph_explore` as primary tool, fall back
to `codegraph_search` + `codegraph_node` for targeted queries).

**If CodeGraph unavailable:** use Glob + Grep to find entry files,
trace 2-3 flows, note `[CodeGraph] not available — run: codegraph init -i`.

## Step 3 — Output format

```
Tour — N layers, M stops

Layer 0 — Foundations (start here)
  1. utils/config.py::load()    — loads env config at boot
  2. utils/db.py::connect()     — initialises connection pool

Layer N — Entry points (read last)
  M. main.py::app               — application bootstrap
```

## Step 4 — Close

Max 4 bullets: non-obvious conventions + one concrete next action.
End with: _"Ask me to expand any stop or trace a specific flow."_
