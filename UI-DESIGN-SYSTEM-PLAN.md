# UI Design System — Factory Integration Plan

Improve AIDLC's UI generation by composing from approved primitives instead of
inventing from scratch. The factory loads a design system, enforces tokens,
validates constraints, and learns from approved outputs.

> **Status key**: `[ ]` not started · `[~]` in progress · `[x]` completed

---

## [x] Phase 1: Design System Index

The knowledge layer — a living directory of primitives, tokens, and patterns.
Always loaded when `project_profile.ui == true`.

### [x] `design-system/INDEX.md`
Catalog of all available primitives with descriptions and when-to-use/not-use.

### [x] `design-system/tokens/`
| File | Purpose |
|------|---------|
| `spacing.md` | Allowed spacing values (4, 8, 12, 16, 24, 32) |
| `typography.md` | Font sizes, weights, line heights |
| `radius.md` | Border radius tokens (sm=3, md=6, lg=12) |
| `color.md` | Semantic color tokens (brand, neutral, danger, success) |
| `elevation.md` | Shadow / z-index tokens |

### [x] `design-system/primitives/<Component>/`
One directory per primitive (Button, Stack, Inline, Input, Text, Surface, Icon):

| File | Purpose |
|------|---------|
| `design.md` | Purpose, constraints, spacing, sizes, interactions, variants, a11y, when-NOT-to-use |
| `anatomy.md` | Expected children, props, layout structure |
| `do-dont.md` | BAD vs GOOD examples with visual contrast |
| `<Component>.tsx` | Canonical reference implementation |
| `examples/*.md` | Usage examples for each variant |

### [x] `design-system/patterns/`
Composition recipes for common UI patterns:
- `form-layout.md`, `data-table.md`, `navigation.md`, `modal-dialog.md`, `settings-page.md`

### [x] `design-system/anti-patterns/`
Known bad patterns with BAD→GOOD contrast:
- `broken-spacing.md`, `inconsistent-radius.md`, `overflowing-content.md`,
  `no-hierarchy.md`, `giant-forms.md`, `custom-padding.md`

### [x] `design-system/screenshots/<component>/`
Baseline screenshots of approved primitives. Captured at ship time.

### [x] `design-system/examples/<component>/` (directory created, populated by ship-agent)
Approved real-world usages extracted from human-approved codegen outputs.

---

## [x] Phase 2: Skills (Lazy Loading)

The enforcement layer — skills loaded by code-generator when `ui: true`.

**Key optimization**: The agent NEVER loads the full design system. Instead:

1. Agent determines needed components from the UI intent plan (e.g. "Button + Form + Input")
2. Agent calls `design-system-resolve <component-names>` (a tool/script)
3. Tool injects ONLY: global `tokens/` + matching `primitives/<Component>/design.md` + `primitives/<Component>/anatomy.md`
4. Patterns and anti-patterns are loaded **on demand** — only if the agent hits a case where the primitive doesn't fit

This keeps context lean — ~20 lines per primitive instead of hundreds of lines of unused specs.

### [x] `aidlc-scripts/factory_design_system_resolve.py`

Script that accepts component names and returns the relevant design system files:
```bash
python3 aidlc-scripts/factory_design_system_resolve.py Button Input Form
# Returns: tokens/*.md + primitives/Button/design.md + primitives/Button/anatomy.md + ...
```

### [x] `.agents/custom-skills/design-system-composer/SKILL.md`

Process:
1. Read `ui_intent[]` from input handoff → extract unique component types needed
2. Call `design-system-resolve <types>` → get only relevant files
3. For each needed UI element:
   - If matching primitive exists → use it (never reinvent)
   - If no match → scan `patterns/` for a composition recipe (selective, not bulk load)
   - If still no match → compose from existing primitives only
4. Resolve all tokens from injected `tokens/*.md` (never hardcode values)
5. Verify: grep generated code for hardcoded spacing, radius, font-size
6. If hardcoded value found → autocorrect to nearest canonical token

### [x] `.agents/custom-skills/ui-constraint-validator/SKILL.md`

| Validator | Rule | Autocorrect |
|-----------|------|-------------|
| Spacing | `padding`, `margin`, `gap` must match `spacing.md` | 13→12, 5→4 |
| Radius | `border-radius` must match `radius.md` | 4→3 |
| Typography | `font-size` must match `typography.md` | 15→14 |
| Color | Use semantic tokens, not raw hex | `#3B82F6` → `color.brand.primary` |
| Elevation | `box-shadow` must match `elevation.md` | arbitrary→token |

Max 3 autocorrections per slice. If >3 deviations: `status: blocked`.

---

## [x] Phase 3: Runtime Docs

Architectural specs for the UI pipeline.

### [x] `.aidlc-orchestrator/runtime/ui-compiler.md`

The model generates **intent**; the compiler generates **code**.

Instead of:
```tsx
<div className="px-[13px] rounded-[5px]">
```

The model writes:
```tsx
<Box padding="md" radius="sm">
```

Compiler maps intent tokens → actual values per `tokens/`. Post-processing step
in code-generator's TDD loop, applied after each Green step:
1. Scan generated TSX/HTML for raw style values
2. Match against `tokens/` via nearest-neighbor snap
3. Rewrite to canonical token references
4. Log deviations corrected to `ui_compliance[]`

### [x] `.aidlc-orchestrator/runtime/design-system.md`

Reference doc. Defines:
- Directory layout (mirrors this plan)
- How code-generator loads design system context
- Versioning strategy (design system version in manifest)
- Contribution rules (who adds primitives, how)

### [x] `.aidlc-orchestrator/runtime/visual-feedback.md`

Screenshot-based feedback loop:
1. After codegen, if Playwright/Chrome is available: capture screenshot
2. Compare against `design-system/screenshots/` baseline
3. Detect: spacing drift, size drift, alignment drift, color drift
4. Emit drift report in `audit_entries[]`
5. On human approval: save screenshot to `examples/`
6. On human rejection: save to `anti-patterns/live/`

---

## [x] Phase 4: Contract Changes

### [x] `code-generator.input.v1.json` — add fields

```json
"design_system_path": { "type": "string" },
"ui_intent": {
  "type": "array",
  "items": {
    "type": "object",
    "properties": {
      "component": { "type": "string" },
      "primitive": { "type": "string" },
      "props": { "type": "object" },
      "pattern": { "type": "string" }
    }
  }
}
```

### [x] `code-generator.output.v1.json` — add field

```json
"ui_compliance": {
  "type": "array",
  "items": {
    "type": "object",
    "properties": {
      "element": { "type": "string" },
      "primitive_used": { "type": "string" },
      "token_compliance": { "type": "boolean" },
      "deviations_corrected": {
        "type": "array",
        "items": {
          "type": "object",
          "properties": {
            "property": { "type": "string" },
            "found": { "type": "string" },
            "corrected_to": { "type": "string" }
          }
        }
      },
      "screenshot_path": { "type": "string" }
    }
  }
}
```

---

## [x] Phase 5: Pipeline Integration

### [x] `.aidlc-orchestrator/runtime/project-profile.md`

Add:
- `profile.ui` → also resolve `design_system_path` and add to code-generator input
- Inject `design-system-composer` and `ui-constraint-validator` alongside `frontend-ui-engineering`

### [x] `.claude/agents/stage/code-generator.md` (+ `.opencode/agents/stage/code-generator.md` parity)

Add to sub-stage 2 (Generate):
- Before TDD loop: load `design_system_path` from input
- Per-slice: after Green, run UI compiler pass + constraint validator
- Emit `ui_compliance[]` in output handoff
- On >3 deviations per slice: emit `status: blocked` with reasons

### [x] `.aidlc-orchestrator/contracts/reviewer.input.v1.json`

Add `design_system_path` field (all 4 reviewers share this contract).

### [x] `.aidlc-orchestrator/runtime/cmd-factory-review.md`

Step 2.5: inject `design_system_path` into all reviewer handoffs when `project_profile.ui == true`.

### [x] `aidlc-rules/aws-aidlc-rule-details/construction/functional-design.md`

Extend Step 5 for UI units:
- In addition to `frontend-components.md`, produce semantic UI intent plan
- Each UI element maps to a primitive from INDEX.md or a pattern from patterns/

### [x] `aidlc-rules/aws-aidlc-rule-details/construction/code-generation.md`

Add to Generation Rules:
- **Design system compliance**: Every UI element must map to a primitive in INDEX.md
- **Token enforcement**: No hardcoded spacing/radius/font-size/color
- **Verification**: Before completion, run ui-constraint-validator across all generated UI files

### [x] Reviewers (code, security, simplifier, performance)

- **reviewer-code**: Checks UI primitives match INDEX.md, `data-testid` presence, token compliance
- **reviewer-security**: Checks `data-testid`, a11y (aria-label, focus management, XSS surface)
- **reviewer-simplifier**: Flags primitive bypass, custom CSS overrides, redundant wrappers
- **reviewer-performance**: Flags excessive DOM nesting, inline style re-renders, missing virtualization

### [x] `aidlc-scripts/install_aidlc.py`

Wire `design-system/` into the installer:
- `--with-design-system` flag (default when interactive)
- Copies `design-system/` into target project
- Installs `design-system-composer` and `ui-constraint-validator` skills

---

## [x] Phase 6: Knowledge Reinforcement Loop (Capped)

When human **approves** generated UI:
1. Extract JSX → token map → spacing/radius/typography measurements
2. Save as `design-system/examples/<component>/approved-<timestamp>.md`
3. **Memory cap**: max 3 examples per component. If 3 exist, new one replaces oldest.
4. Update INDEX.md with usage count (most-used primitives)

When human **rejects** generated UI:
1. Capture rejection reason
2. Save as `design-system/anti-patterns/live/<issue>.md`
3. Emit `emitted_knowledge[]` entry `kind: antipattern`

**Enforcement**: `factory_design_system_resolve.py` trims examples/ on each write.
Keeps `design-system/` file sizes predictable — no unbounded growth.

Knowledge agent cross-references:
- On subsequent runs, load relevant `examples/` (max 3 per component) and `anti-patterns/live/` entries
- Prevents repeating previous mistakes
- Converges visual output toward what humans actually approve

### [x] `aidlc-scripts/factory_design_system_learn.py`

Script with subcommands:
- `approve` — save approved example, extract tokens, trim to cap
- `reject` — save rejection reason as antipattern in `anti-patterns/live/`
- `update-index` — rebuild INDEX.md usage counts from examples

### [x] `.claude/agents/stage/ship-agent.md` (+ `.opencode/` parity)

Add step 7: UI example capture after shipping.

### [x] `.aidlc-orchestrator/runtime/cmd-factory-review.md`

Step 6 approval gate: on rejection with UI, save antipattern via `factory_design_system_learn.py reject`.

### [x] `.claude/agents/cross-cutting/knowledge-agent.md` (+ `.opencode/` parity)

Add "Design system cross-reference" section: when `ui: true` AND `design_system_path` is set,
query for examples + antipatterns. Injects relevant priors into code-generator context.

### [x] `aidlc-scripts/factory_design_system_resolve.py`

Resolve already loads examples (capped at 3). Updated to also load `anti-patterns/live/` files.

---

---

## [x] Phase 7: Resilience Against Poorly Designed Figma Files

Shields the system from Figma files without Auto Layout, floating pixels (13.4px),
colors without variables, and layers without structure. Figma proposes the
**intent**; the design system **dictates the law**.

### [x] `factory_design_system_snap.py` — Input Snapping

New script that runs **before** Claude sees Figma data.
Reads raw Figma JSON and applies "semantic rounding":

| Raw Figma value | Resulting token | Rule |
|----------------|------------------|------|
| `14px`, `17px`, `13.4px` | `spacing.md` (16px) | Euclidean distance to nearest token |
| `#3c83f6`, `#1d4ed8` | `color.brand.primary` | Known color map |
| `4.2px` border-radius | `radius.sm` (3px) | Nearest-neighbor with ±2px tolerance |
| Any float | Nearest integer, then snap to token | `13.7 → 14 → 16 → spacing.md` |

**Output**: Clean JSON with only tokens, no raw values. Claude never sees the chaos.

### [x] Update `.agents/custom-skills/design-system-composer/SKILL.md`

Add 3 new sections:

#### Section 5: Ban Figma Absolute Geometry

```
STRICT RULES:
- NEVER use position: absolute, top, left, right, bottom based on Figma data
- EXCEPTION: tooltips, modals, popovers (intentionally floating elements)
- Instead of coordinates: reconstruct visual flow with Stack (vertical) and Inline (horizontal)
- Ignore designer's layer grouping — use reading order (top→bottom, left→right)
```

#### Section 6: Component Triage by Similarity

```
TRIAGE ALGORITHM (by preference order):
1. Is it an official instance? → Figma node refers to known ID → use equivalent primitive
2. Does it behave like something known? → Heuristics:
   - Single-line text + contrasted background + small dimensions → Button
   - Border + padding + vertical children → Stack
   - Border + padding + horizontal children → Inline
   - Input type + label → Input
3. Nothing matches? → Compose from existing primitives, ignore custom styles
4. DESTROY custom styles: if it uses CSS not in INDEX.md → force nearest primitive
```

#### Section 7: "Archaeologist" Mode (Fallback)

```
IF Figma data is a structureless tangle:
1. EXTRACT ONLY: visible text, required inputs, reading order
2. IGNORE: absolute positions, sizes, colors, paddings, borders
3. GENERATE from scratch using design-system/patterns/ as blueprint
4. The pattern dictates the layout, not Figma

This turns Figma into an "idea sketch" — the local system builds the real UI.
```

### [x] Integrate Input Snapping into the Pipeline

- [x] `project-profile.md`: add `has_figma_data` detection and snap step injection
- [x] `code-generator.md`: Pre-Figma step before Pre-TDD to load snapped data
- [x] `ui-compiler.md`: §5 "Input snapping — Figma pre-processing"

---

## Implementation order

```
Phase 1 (Design index)   ✅ completed
Phase 2 (Skills)         ✅ completed
Phase 3 (Runtime docs)   ✅ completed
Phase 4 (Contracts)      ✅ completed
Phase 5 (Integration)    ✅ completed
Phase 6 (Feedback loop)  ✅ completed
Phase 7 (Figma res.)     ✅ completed
Phase 8 (Stitch)           ✅ completed
```

Each phase is independent — ship and iterate.

---

## [x] Phase 8: Google Stitch Support

Stitch is a design source supported at the same level as Figma.

### [x] `aidlc-scripts/factory_stitch_snap.py`

Snaps Stitch HTML/CSS output and DESIGN.md definitions to our design tokens.

| Subcommand | Purpose |
|-----------|---------|
| `snap-html` | Parse HTML inline styles, snap values to tokens |
| `snap-design` | Parse Stitch DESIGN.md → our token format |
| `snap-file` | Snaps HTML/CSS/DESIGN.md by extension detection |

### [x] `aidlc-scripts/factory_stitch_mcp.py`

MCP registry and health check for `@_davideast/stitch-mcp`.

| Subcommand | Purpose |
|-----------|---------|
| `doctor` | Check Node, npx, Stitch MCP server health |
| `proxy-config` | Print proxy command + env details |
| `config` | Print MCP config fragment for .mcp.json merge |

### [x] Runtime integration

- `project-profile.md`: `has_stitch_data` detection, Stitch MCP setup step, `stitch_snapped_path`, `stitch_archaeologist_mode`
- `ui-compiler.md`: §6 Stitch pipeline (mirrors §5 Figma pipeline)
- `design-system.md`: §5 Stitch integration with DESIGN.md import

### [x] Skill integration

- `design-system-composer/SKILL.md`: §8 Stitch integration, §9 DESIGN.md import

### [x] MCP wiring

Stitch MCP server (`@_davideast/stitch-mcp proxy`) added to:
- `.mcp.json`, `.cursor/mcp.json`, `.vscode/mcp.json`, `opencode.json`

### [x] Installer

- `factory_stitch_snap.py` + `factory_stitch_mcp.py` in `ORCHESTRATOR_FACTORY_SCRIPTS`

### [x] Knowledge agent

- Stitch cross-reference in all 4 tool copies of `knowledge-agent.md`
