---
name: design-system-composer
description: Design-system-driven UI composition. Never invents primitives — selects from INDEX.md. Composes from Stack, Inline, Box, Button, Input, Text, Surface, Icon. Enforces spacing/radius/typography tokens. Companion to frontend-ui-engineering (generic frontend patterns).
---

# Design System Composer

## Overview

You do NOT generate UI from scratch. You compose from approved primitives
listed in the design system INDEX.md. The design system is the single source
of truth for all visual output.

**Companion to `frontend-ui-engineering`**: That skill provides generic frontend
patterns (component architecture, responsive design, state management). This skill
provides design-system-specific composition: primitive selection, token enforcement,
and Figma resilience.

**Lazy loading**: You only load design system files for the components you need.
Call `factory_design_system_resolve.py resolve <components>` to get exactly the
relevant files — never the full index.

---

## Step 1: Determine needed component types

Read the input handoff. Extract which UI elements are needed from:
- `input.ui_intent[]` (if present) — explicit list of primitives
- The user request and functional design artifacts

Collect unique component types (e.g. `Button`, `Input`, `Stack`).

---

## Step 2: Load design system files (lazy)

Call the resolve tool:
```bash
python3 aidlc-scripts/factory_design_system_resolve.py resolve Button Input Stack
```

This returns ONLY:
- Global token files (`tokens/spacing.md`, `tokens/radius.md`, etc.)
- `design.md` for each requested component
- `anatomy.md` for each requested component
- `do-dont.md` for each requested component (if exists)
- Reference implementation `.tsx` (if exists)
- Capped examples (max 3 per component)

Do NOT load primitives you don't need. Do NOT bulk-load patterns/
unless you hit a composition gap.

---

## Step 3: Compose (never invent)

For each UI element needed:

1. **Check INDEX.md** — does a matching primitive exist?
   - YES → use it with token-compliant props
   - NO → check patterns/ for a composition recipe (call `resolve` with `--with-patterns`)
   - STILL NO → compose from existing primitives only

2. **Mapping rules**:
   - Any `<div>` with padding → `Box`
   - Any vertical group → `Stack`
   - Any horizontal group → `Inline`
   - Any button-like element → `Button` (never raw `<button>` unless token-compliant)
   - Any input → `Input` (never raw `<input>`)
   - Any text → `Text` (never raw `<p>`, `<span>`, `<h1>` directly)
   - Any themed container → `Surface`

3. **Resolve all visual properties through tokens**:
   - `padding`, `margin`, `gap` → `spacing.*` token
   - `border-radius` → `radius.*` token
   - `font-size`, `font-weight` → `font-size.*`, `font-weight.*` tokens
   - `color`, `background-color` → `color.*` token
   - `box-shadow` → `elevation.*` token

4. **Never hardcode raw values**. Never use Tailwind arbitrary values
   (`px-[13px]`, `rounded-[5px]`, `gap-[7px]`).

---

## Step 4: Accessibility (mandatory)

| Requirement | Check |
|-------------|-------|
| `data-testid` | Every interactive element (Button, Input, link) |
| Focus ring | Every interactive element |
| `aria-label` | Icon-only buttons, inputs without visible labels |
| `aria-invalid` | Inputs in error state |
| `aria-describedby` | Inputs with error messages |
| Keyboard support | Enter/Space for buttons, Tab for inputs |
| Color contrast | Text meets WCAG 2.1 AA (4.5:1 normal, 3:1 large) |

---

## Step 5: Prohibir geometría absoluta de Figma

Cuando los datos provienen de Figma (directa o indirectamente), aplicar estas reglas:

```
REGLAS ESTRICTAS:
- NUNCA usar position: absolute, top, left, right, bottom basado en coordenadas de Figma
- EXCEPCIÓN ÚNICA: tooltips, modales, popovers (elementos flotantes intencionales)
- En lugar de coordenadas: reconstruir el flujo visual con Stack (vertical) e Inline (horizontal)
- Ignorar la agrupación de capas del diseñador — usar orden de lectura (arriba→abajo, izquierda→derecha)
- Si el Figma no usa Auto Layout: tratar cada elemento como parte de un flujo secuencial, no como un canvas absoluto
```

**Fundamento**: Figma sin Auto Layout produce coordenadas XY flotantes. Replicarlas
destruye la responsividad. Stack/Inline reconstruyen el flujo correcto.

---

## Step 6: Triaje de componentes por similitud

Cuando Figma no usa instancias oficiales de componentes, aplicar este algoritmo:

```
ALGORITMO DE TRIAJE (orden de preferencia):
1. ¿Es instancia oficial?
   → El nodo Figma refiere a un ID de componente conocido
   → Usar la primitiva equivalente sin cuestionar

2. ¿Se comporta como algo conocido? (Heurísticas)
   → Texto 1 línea + fondo contrastado + dimensiones pequeñas (< 60px height)
     → TRATAR COMO: Button (ignorar vector raw)
   → Borde visible + padding + hijos en vertical
     → TRATAR COMO: Stack
   → Borde visible + padding + hijos en horizontal
     → TRATAR COMO: Inline
   → Input type + label + borde
     → TRATAR COMO: Input (usar anatomy.md, ignorar raw Figma)
   → Texto largo + sin fondo + sin borde
     → TRATAR COMO: Text (con variant apropiada)

3. ¿Nada coincide?
   → Componer de primitivas existentes, ignorar todos los estilos custom
   → Usar patterns/ como blueprint de layout

4. DESTRUIR ESTILOS CUSTOM:
   → Si el nodo intenta CSS que no existe en INDEX.md (e.g. border-radius: 7, padding: 11)
   → Forzar la primitiva más cercana con sus tokens correctos
   → NO preservar valores "artísticos" del diseñador si no están en el token set
```

---

## Step 7: Modo "Arqueólogo" (Fallback para Figma caótico)

Si los datos de Figma son un espagueti de capas sin estructura reconocible:

```
CUANDO ACTIVAR:
- Auto Layout ausente en todos los nodos
- Coordenadas superpuestas (elementos en la misma XY)
- Sin instancias de componentes reconocibles
- Más de 50% de los valores necesitan corrección

PROTOCOLO:
1. EXTRAER SOLO:
   - Texto visible de cada nodo
   - Inputs requeridos (placeholders, tipos)
   - Orden de lectura (Y ascendente, luego X ascendente)

2. IGNORAR COMPLETAMENTE:
   - Posiciones absolutas (top, left)
   - Tamaños de contenedor (width, height)
   - Colores específicos
   - Paddings, margins, gaps
   - Bordes, radios de esquina
   - Sombras, efectos

3. GENERAR DESDE CERO usando design-system/patterns/:
   - Seleccionar el patrón que mejor se ajuste a los contenidos extraídos
   - El layout lo dicta el patrón, no Figma
   - Todos los valores visuales vienen de tokens/

4. PRIORIDAD: funcionalidad sobre fidelidad visual
   - Los textos e inputs son correctos
   - El layout puede diferir del Figma original
   - El diseñador corrige el Figma, no al revés
```

**Esto convierte a Figma en un "plano de ideas" — el sistema local construye la UI real.**

---

## Verification (mandatory — BLOCKING if fails)

After code generation for each slice:

1. **Primitive audit**: Scan generated files for HTML elements that should be
   primitives (raw `<div>`, `<button>`, `<input>`, `<p>`, `<h1-6>` with styling).
   If found → flag as deviation.

2. **Token audit**: Search for hardcoded spacing, radius, font-size, color, shadow.
   If found → log each as a deviation in `ui_compliance[]`.

3. **data-testid audit**: Grep for all interactive elements, confirm each has
   `data-testid`. If missing → flag.

4. **Autocorrect**: Run `ui-constraint-validator` skill on all generated UI files.
   **Precondition:** `tokens/color.md` (and the rest of `tokens/*.md`) must be
   present and non-empty. If missing, the validator emits `status: blocked` —
   do NOT proceed with codegen until tokens are resolved. See
   `ui-constraint-validator/SKILL.md` § 2d for the hard-fail rule and the
   project-specific snap-table requirement (the hex values in that skill are
   illustrative, not defaults).

5. **Log deviations**: Add to output `ui_compliance[]`:
   ```json
   {
     "element": "button.save-btn",
     "primitive_used": "Button",
     "token_compliance": true,
     "deviations_corrected": [
       { "property": "border-radius", "found": "4px", "corrected_to": "radius.sm (3px)" }
     ]
   }
   ```

---

## Common Rationalizations (REJECT these)

| Rationalization | Why it's rejected |
|----------------|-------------------|
| "This padding is slightly different, it's fine" | Every deviation breaks systemic consistency |
| "I'll use a raw div here, it's just a wrapper" | Use Box or Stack — that's what they're for |
| "The token doesn't have 13px, but 13px looks better" | The token set is the source of truth |
| "I'll add data-testid later" | It's a generation requirement, not optional |
| "This inline style is temporary" | There is no temporary — code lives forever |

---

## Red Flags

- More than 3 token deviations in a single slice → `status: needs_human`
- Any interactive element missing `data-testid` → `status: blocked`
- Raw HTML elements replacing primitives (e.g. raw `<button>` when `Button` exists) → flag
- Arbitrary Tailwind values (`px-[...]`, `rounded-[...]`) → autocorrect, flag if repeated
