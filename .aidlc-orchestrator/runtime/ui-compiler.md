# UI Compiler

PRIORITY: P2

Transforms semantic UI intent into token-compliant code. Runs as a
post-processing step in code-generator's TDD loop, applied after each
Green step.

---

## §1 The model generates intent, the compiler generates code

The LLM should never write arbitrary CSS or Tailwind arbitrary values.
Instead, the LLM writes **intent** using primitives and semantic tokens:

```
Intent (LLM writes)                  → Compiler → Token-compliant code

<Button variant="primary" size="md"> → <button class="btn btn--primary btn--md">
<Stack gap="lg">                     → <div class="stack stack--gap-lg">
<Box padding="md" radius="sm">       → <div class="box box--pad-md box--rad-sm">
<Text variant="h2">                  → <h2 class="text text--h2">
```

---

## §2 Compilation steps

Applied automatically by code-generator after each Green step:

### Step 1: Primitive resolution

Scan generated JSX/TSX for recognized primitives:
- `<Button>`, `<Stack>`, `<Inline>`, `<Box>`, `<Input>`, `<Text>`, `<Surface>`, `<Icon>`

Each primitive maps to a canonical HTML/CSS output defined in its `anatomy.md`.

### Step 2: Token resolution

For each prop that accepts a token value:
1. Look up the token value in the loaded `tokens/*.md` files
2. If the value matches a known token → use the token's CSS value
3. If the value is NOT a known token → run nearest-neighbor snap
4. If no reasonable snap exists → log deviation, use closest token

### Step 3: Style output

When a CSS-in-JS or utility framework is used:

| Framework | Output format |
|-----------|--------------|
| None (plain CSS) | Generate CSS class per anatomy.md with token values inlined |
| Tailwind | Use standard Tailwind classes (`p-3` for 12px, `rounded-sm` for 3px, etc.) |
| Styled Components | Generate styled component with token values |
| CSS Modules | Generate `.module.css` with token values |

When no framework is detected: compile to inline styles with token values
(not ideal, but ensures consistency).

---

## §3 Intent-first vs component-library mode

If the project already has a component library (MUI, Chakra, Ant, shadcn):

```
The compiler maps:
  <Button variant="primary" size="md" label="Save" />
    → <MuiButton variant="contained" size="medium">Save</MuiButton>
```

The mapping is read from `project-profile.md` → `tech_stack[]` and resolved
per-framework. When the framework is unknown, use the generic primitive output.

---

## §4 What the compiler does NOT do

- Does NOT change component logic or state management
- Does NOT modify tests
- Does NOT modify `data-testid` attributes
- Does NOT change component props structure (only visual token values)

---

## §5 Input Snapping — Pre-processing de Figma

Cuando los datos provienen de Figma, se ejecuta `factory_design_system_snap.py`
**ANTES** de que el LLM vea los datos. Esto asegura que Claude nunca reciba valores
caóticos (13.4px, colores sin variable, coordenadas absolutas).

### Pipeline

```
Figma JSON raw
    ↓
factory_design_system_snap.py snap-file --input figma.json
    ↓
JSON limpio (solo tokens, sin raw values)
    ↓
LLM compone con primitivas
    ↓
ui-constraint-validator (post-processing)
```

### Qué hace el snap

| Valor raw Figma | Token resultante | Método |
|----------------|------------------|--------|
| `padding: 13.4px` | `spacing.md` (12px) | Nearest-neighbor con distancia euclídea |
| `border-radius: 4.2px` | `radius.sm` (3px) | Nearest-neighbor, tolerancia ±2px |
| `font-size: 15px` | `font-size.body` (14px) | Nearest-neighbor en set {12,14,16,20,24,32,40} |
| `color: #3c83f6` | `color.brand.primary` | Mapa de hex → token conocido |
| `itemSpacing: 7` | `spacing.sm` (8px) | Snap spacing |

### Cuándo se ejecuta

- Siempre que `project_profile.ui == true` Y hay datos de Figma en el input
- Inyectado por `project-profile.md` como paso previo al code-generator
- El script reporta cuántas correcciones hizo — si >10, sugiere modo "Arqueólogo"
