# Project-Profile Classification & Reverse-Engineer Routing

PRIORITY: P3

Orchestrator runtime spec for **Step 3.5** of `/factory-spec`. Runs after `workspace-scout` completes, before any further stage spawns. Both decisions read from `workspace-scout.output.yaml`.

## A. Classify `project_profile` (Bug #8 fix — gates conditional-skill loading)

Read `workspace-scout.output.yaml.workspace_state` and the original `user_request`. Apply each flag independently:

**`ui = true` iff** EITHER:
- `workspace_state.programming_languages` contains `TypeScript|JavaScript|TSX|JSX` AND `workspace_state.project_structure` matches `/SPA|frontend|React|Vue|Svelte|Angular|Next|Nuxt|web/i`, OR
- the workspace's `package.json` declares a UI framework dependency (`react`/`vue`/`svelte`/etc.)

**`api = true` iff** EITHER:
- the user_request matches `/endpoint|route|REST|GraphQL|API|webhook|\/[a-z][a-z0-9_-]+/i`, OR
- the workspace has `express`/`fastify`/`hono`/`nestjs`/`fastapi`/`flask`/`django` in `package.json`/`pyproject.toml`/etc.

**`has_legacy = true` iff** EITHER:
- `workspace_state.reverse_engineering_artifacts_present == true`, OR
- the user_request matches `/migrat|refactor|deprecat|legacy|rewrite|port/i`

**`design_system_path`** — when `ui: true`:
1. Check if `design-system/` exists at repo root
2. If yes: set `design_system_path = "design-system/"`
3. If no: set `design_system_path = null` (skill still runs with inline fallback)

**`has_figma_data`** — when `ui: true`:
1. Check if `figma/` directory exists OR any `*.figma.json` files exist in the workspace
2. Check `workspace-scout.output.yaml.workspace_state` for figma references in `project_structure`
3. If yes: set `has_figma_data = true`
4. If no: set `has_figma_data = false`

**Figma input snap** — when `has_figma_data == true`:
1. Before code-generator runs, execute the snap step:
   ```bash
   python3 aidlc-scripts/factory_design_system_snap.py snap-file \
       --input figma/raw-data.json \
       --output figma/snapped.json
   ```
2. Set `figma_snapped_path = "figma/snapped.json"` in the code-generator input
3. The snap script reports correction count. If >10 corrections, set flag
   `figma_archaeologist_mode: true` — triggers "Arqueólogo" fallback in
   `design-system-composer` skill §7.

**`has_stitch_data`** — when `ui: true`:
1. Check if `stitch/` directory exists OR any `*.stitch.json` files exist in the workspace
2. Check if `.stitch-project.json` exists (created by Stitch MCP workspace persistence)
3. Check `workspace-scout.output.yaml.workspace_state` for stitch references in `project_structure`
4. If yes: set `has_stitch_data = true`
5. If no: set `has_stitch_data = false`

**Stitch MCP setup** — when `has_stitch_data == true`:
1. Before code-generator runs, run health check:
   ```bash
   python3 aidlc-scripts/factory_stitch_mcp.py doctor
   ```
2. If healthy, optionally fetch Stitch designs for pre-processing:
   ```bash
   python3 aidlc-scripts/factory_stitch_snap.py snap-file \
       --input stitch/export.html \
       --output stitch/snapped.json
   ```
3. Set `stitch_snapped_path = "stitch/snapped.json"` in the code-generator input
4. If Stitch DESIGN.md is present:
   ```bash
   python3 aidlc-scripts/factory_stitch_snap.py snap-design \
       --input stitch/DESIGN.md \
       --repo-root <repo-root>
   ```
5. The snap script reports correction count. If >10 corrections, set flag
   `stitch_archaeologist_mode: true` — triggers "Arqueólogo" fallback in
   `design-system-composer` skill §7 (same fallback as Figma).

**Inject into downstream handoffs:**
When building input handoffs for code-generator, reviewers, build-test-agent, and ship-agent, add:
- `design_system_path` from the resolved value
- `has_figma_data` from the resolved value
- `figma_snapped_path` when figma snapping ran
- `figma_archaeologist_mode` when >10 corrections
- `has_stitch_data` from the resolved value
- `stitch_snapped_path` when stitch snapping ran
- `stitch_archaeologist_mode` when >10 corrections
- `skills_required[]` adds `frontend-ui-engineering`, `design-system-composer`, AND `ui-constraint-validator` when `ui: true`

**Persist:**
```bash
python3 aidlc-scripts/factory_run.py set <run-id> \
    --field project_profile.ui=<true|false> \
    --field project_profile.api=<true|false> \
    --field project_profile.has_legacy=<true|false>
```

**Audit**: append a single bullet to the NEXT stage's audit block (NOT a standalone header):
`[Orchestrator] Classified project_profile: ui=<bool>, api=<bool>, has_legacy=<bool>`

## Conditional-skill injection (downstream consumer)

When building input handoffs for `code-generator`, `build-test-agent`, and `ship-agent`, read `manifest.project_profile` and add to `skills_required[]`:

| Flag | Affected stage(s) | Skill to add |
|---|---|---|
| `ui: true` | `code-generator` | `frontend-ui-engineering` (generic patterns) |
| `ui: true` | `code-generator` | `design-system-composer` (design-system composition) |
| `ui: true` | `code-generator` | `ui-constraint-validator` |
| `ui: true` | `build-test-agent` | `browser-testing-with-devtools` |
| `api: true` | `code-generator` | `api-and-interface-design` |
| `has_legacy: true` | `ship-agent` | `deprecation-and-migration` |

Resolve the matching `SKILL.md` path and add to `skill_paths_resolved[]`. If the skill file isn't found, log `[Skill] MISSING: <name> (conditional)` and continue — the stage's rule file has an inline fallback.

## B. Reverse-engineer routing (Bug #9 fix)

**If** `workspace_state.next_phase == "reverse-engineering"` **AND** `workspace_state.reverse_engineering_artifacts_present == false` **→** surface the approval gate (do NOT silently skip):

```
⏸️  Reverse-Engineer Recommendation

Workspace Scout detected:
  - project_type: brownfield (existing code present)
  - reverse_engineering_artifacts_present: false

Running `reverse-engineer` first produces:
  - aidlc-docs/inception/reverse-engineering/<run-id>-business-overview.md  (MUST substitute actual run_id)
  - architecture.md, code-structure.md, api-docs.md, component-inventory.md
  - interaction-diagrams.md, tech-stack.md, dependencies.md

Recommended for: major refactors, new modules touching existing systems,
                 or any change where requirements-analyst would benefit from
                 codebase context.

Skip-OK for: small features (a single endpoint, a config change, doc-only).

Run reverse-engineer now? [Y/n]
```

Use `AskUserQuestion` with options:
- `"Run reverse-engineer first (recommended for big changes)"`
- `"Skip and go straight to requirements-analyst (OK for small features)"`

On user response, call `emit_audit_block` per [`audit-block.protocol.md` § reverse-engineer gate](../contracts/audit-block.protocol.md).

**On approve**: spawn `reverse-engineer` via shared spawn loop. On completion, append to `manifest.completed_stages[]`, set `current_stage: requirements-analyst`.

**On reject**: `factory_run.py set <run-id> --field skipped_stages='[..., "reverse-engineer"]'` (read-modify-write).

**Else** (greenfield, or brownfield-with-RE-artifacts already present): no prompt; proceed directly to Step 4.

## Why this is a separate runtime doc

Project-profile classification runs once per `/factory-spec` invocation (loaded on demand). This contrasts with `spawn-loop.md` which is **load-critical** — read on every spawn. Keeping cold paths in separate runtime files shrank unconditionally-loaded kernel context by ~78%.
