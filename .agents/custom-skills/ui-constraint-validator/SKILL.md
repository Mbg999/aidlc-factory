---
name: ui-constraint-validator
description: Design token constraint enforcer. Scans generated UI code for hardcoded values and snaps them to the nearest canonical token. Spacing, radius, typography, color, elevation validators with autocorrect.
---

# UI Constraint Validator

## Overview

Post-generation validation that scans generated UI code and corrects any
deviation from the design system token set. Operates as a sub-skill of
`design-system-composer`, invoked per-slice after each Green step.

---

## Step 1: Load token values

Call the resolve tool to get the full token set:
```bash
python3 aidlc-scripts/factory_design_system_resolve.py resolve __tokens__
```

This returns `tokens/spacing.md`, `tokens/radius.md`, `tokens/typography.md`,
`tokens/color.md`, `tokens/elevation.md`.

Extract the canonical value set:
- Spacing: `{4, 8, 12, 16, 24, 32}`
- Radius: `{0, 3, 6, 12, 9999}`
- Font sizes: `{12, 14, 16, 20, 24, 32, 40}`

---

## Step 2: Scan generated files

For each generated UI file (`.tsx`, `.jsx`, `.html`, `.css`):

### 2a. Spacing validator

Search for:
- `padding: <value>`, `padding-*: <value>`
- `margin: <value>`, `margin-*: <value>`
- `gap: <value>`
- Tailwind: `p-[<value>]`, `px-[<value>]`, `py-[<value>]`, `m-[<value>]`, `gap-[<value>]`
- Inline: `style={{ padding: <value> }}`, etc.

For each value found:
1. Parse the numeric value (strip `px`)
2. If value NOT in `{4, 8, 12, 16, 24, 32}`:
   - Find nearest canonical value
   - Replace with canonical value
   - Log deviation

### 2b. Radius validator

Search for:
- `border-radius: <value>`
- `rounded-[<value>]`, `rounded-<sm|md|lg>`
- `style={{ borderRadius: <value> }}`

Snap rules:
| Found | Snap to |
|-------|---------|
| 0-1px | 0 (`radius.none`) |
| 2-4px | 3px (`radius.sm`) |
| 5-9px | 6px (`radius.md`) |
| 10-16px | 12px (`radius.lg`) |
| 17+px | 9999px (`radius.full`) |

### 2c. Typography validator

Search for:
- `font-size: <value>`
- `text-[<value>]`
- `style={{ fontSize: <value> }}`

Snap rules:
| Found | Snap to |
|-------|---------|
| 11-13px | 12px (`font-size.caption`) |
| 13-15px | 14px (`font-size.body`) |
| 15-18px | 16px (`font-size.body-large`) |
| 19-22px | 20px (`font-size.h4`) |
| 23-28px | 24px (`font-size.h3`) |
| 29-36px | 32px (`font-size.h2`) |
| 37+px | 40px (`font-size.h1`) |

### 2d. Color validator

Search for raw hex values in `color`, `background`, `background-color`, `border-color`.

Known hex mapping (from `tokens/color.md`):
| Raw hex | Replace with |
|---------|--------------|
| `#2563EB`, `#1D4ED8`, `#1E40AF`, any blue-700+ | `color.brand.primary` |
| `#EF4444`, `#DC2626`, `#B91C1C` | `color.semantic.danger` |
| `#10B981`, `#059669`, `#047857` | `color.semantic.success` |
| `#F59E0B`, `#D97706` | `color.semantic.warning` |
| `#111827`, `#1F2937`, `#374151` | `color.neutral.text-primary` |
| `#6B7280`, `#9CA3AF` | `color.neutral.text-secondary` |
| `#F9FAFB` | `color.neutral.surface` |
| `#E5E7EB` | `color.neutral.border` |
| `#FFFFFF` | `color.neutral.bg` |

### 2e. Elevation validator

Search for `box-shadow` values.

Snap rules:
| Shadow blur | Snap to |
|-------------|---------|
| 0-2px | `elevation.sm` |
| 3-6px | `elevation.md` |
| 7-15px | `elevation.lg` |
| 16+px | `elevation.xl` |

---

## Step 3: Apply corrections

For each deviation found:
1. Apply the correction (replace value in file)
2. Log to `ui_compliance[].deviations_corrected[]`:
   ```json
   {
     "property": "border-radius",
     "element": ".btn-primary",
     "found": "4px",
     "corrected_to": "radius.sm (3px)",
     "file": "src/components/Button.tsx"
   }
   ```

---

## Step 4: Gate

| Condition | Action |
|-----------|--------|
| 0 deviations | ✅ PASS — clean slice |
| 1-3 deviations | ✅ PASS — autocorrected, logged |
| >3 deviations per slice | 🛑 BLOCK — `status: needs_human`. Too many corrections suggests the model didn't follow the design system |

---

## Verification

Before declaring PASS, confirm:
- [ ] All spacing values are in `{4, 8, 12, 16, 24, 32}`
- [ ] All radius values are in `{0, 3, 6, 12, 9999}`
- [ ] All font sizes are in `{12, 14, 16, 20, 24, 32, 40}`
- [ ] No raw hex colors (all replaced with `color.*` tokens)
- [ ] No arbitrary Tailwind values (`p-[...]`, `px-[...]`, etc.)
- [ ] All corrections logged to `ui_compliance[]`
