# Design System Harness V2 — Plan

Supera V1 desacoplando el harness de cualquier tecnología concreta (React/TSX),
uniﬁcando fuentes de diseño (Figma, Stitch, Zeplin, etc.) y cerrando el loop
de detección de drift con un sistema ligero pero efectivo.

> **Filosofía**: El harness NO dicta cómo escribir UI. Interpreta un design
> system, lo valida contra reglas universales, y genera *intento* semántico.
> Cada framework adapter traduce ese intento a su sintaxis nativa. Esto evita
> gobernanza excesiva y mantiene la velocidad.

---

## Problemas de V1 que V2 resuelve

| Problema | Impacto | Solución V2 |
|----------|---------|-------------|
| Primitivas atadas a React/TSX | No sirve para Angular, Flutter, etc. | Modelo de intento abstracto + adapters |
| `ui-constraint-validator` hardcodea CSS properties | Solo valida web | Validación sobre modelo semántico, no sintaxis |
| Figma/Stitch scripts separados con lógica duplicada | Mantenimiento, bugs | `DesignSourceAdapter` uniﬁcado |
| `visual-feedback.md` no implementado | Drift no se detecta | Pipeline de captura + diff real |
| Sin tests para scripts clave | Riesgo de regresión | Tests de integración por adapter |
| Primitivas incompletas (7/8) | Composer no puede operar | Generación automática vía template |
| Quality score inexistente | Diseños malos entran igual al pipeline | Score + archaeologist mode automático |

---

## Arquitectura V2

```
Design Source (Figma / Stitch / Zeplin / custom JSON)
       │
       ▼
┌──────────────────────────────┐
│   DesignSourceAdapter        │ ← unified interface
│   • fetch() → raw            │
│   • snap(token_set) → clean  │
│   • score() → quality        │
│   • archaeologist() → intent │
└──────────┬───────────────────┘
           │ token-snapped intent
           ▼
┌──────────────────────────────┐
│   DesignSystemHarness        │ ← core engine
│   • load_ds(path)            │
│   • validate(tokens)         │
│   • compose(intent)          │
│   • check_drift(baseline)    │
└──────────┬───────────────────┘
           │ semantic intent (framework-agnostic)
           ▼
┌──────────────────────────────┐
│   FrameworkAdapter           │ ← one per target
│   • render(intent) → code    │
│   • validate(code) → report  │
└──────────────────────────────┘
```

### Por qué esta separación

1. **DesignSourceAdapter** → se escribe uno por fuente. El core no cambia.
2. **DesignSystemHarness** → lógica compartida: validación, composición, drift.
   Sin conocimiento de React ni de Figma.
3. **FrameworkAdapter** → se escribe uno por target. Sin conocimiento de tokens
   ni de fuentes de diseño.

---

## Modelo de Intento Semántico (Framework-Agnostic)

El núcleo del sistema. Cualquier framework adapter recibe esto:

```typescript
interface SemanticIntent {
  layout: LayoutNode[];
  tokens: {
    spacing: Record<string, number>;
    radius: Record<string, number>;
    typography: Record<string, { size: number; weight?: string; lineHeight?: number }>;
    color: Record<string, string>;
    elevation: Record<string, { shadow: string; zIndex: number }>;
  };
  components: ComponentIntent[];
}

interface LayoutNode {
  type: "stack" | "inline" | "box" | "grid" | "surface";
  gap?: string;
  padding?: string;
  radius?: string;
  children: LayoutNode[] | ComponentIntent[];
}

interface ComponentIntent {
  type: "button" | "input" | "text" | "icon" | "link";
  variant?: string;
  size?: string;
  label?: string;
  // framework-specific props pasan por aquí sin validación
  framework_props?: Record<string, unknown>;
}
```

**Ventaja**: El mismo intento genera UI en React, Angular, Flutter, SwiftUI, etc.
Cada adapter mapea `stack` → `Stack( gap: .sm )` o `<div class="stack">` o
`Column( spacing: 8 )`.

**framework_props**: escape hatch para cosas especíﬁcas del framework. El
harness no las valida — el adapter decide cómo manejarlas. Esto evita que el
modelo semántico se convierta en un cuello de botella.

---

## Plan de Implementación

### Fase 1: Core Harness Engine

**Objetivo**: Extraer la lógica compartida de V1 a un engine agnóstico.

| Item | Descripción | Criterio de éxito | Estado |
|------|-------------|-------------------|--------|
| 1.1 | `SemanticIntent` model en JSON Schema (`contracts/harness/semantic-intent.v1.json`) | Schema publicado, 3 ejemplos válidos | ✅ |
| 1.2 | `DesignSystemHarness` clase en `aidlc-scripts/harness_engine.py` | Carga tokens desde `design-system/tokens/`, valida cobertura (4 de 5 categorías), emite `quality_score` | ✅ |
| 1.3 | `validate_tokens()` — reglas universales | Spacing multiplos de 4, radius documentados, colores semánticos vs raw | ✅ |
| 1.4 | `compose_intent()` — de componentes a SemanticIntent | Reemplaza Step 3 de `design-system-composer/SKILL.md` | ✅ |
| 1.5 | `project-profile.md` actualizado | `tech_stack` → `framework` detectado, adapter seleccionado automáticamente | ✅ |

**Anti-governanza**: El engine valida pero NO bloquea. Emite `warnings[]` y
`suggestions[]`. El code-generator decide si detenerse. Solo >5 warnings
críticos (`no_spacing_tokens`, `all_colors_raw`) elevan a `needs_human`.

### Fase 2: Design Source Adapters

**Objetivo**: Uniﬁcar Figma, Stitch y fuentes futuras bajo una interfaz común.

```
DesignSourceAdapter (src/harness/adapters/source/base.py)
├── FigmaAdapter     (src/harness/adapters/source/figma.py)
├── StitchAdapter    (src/harness/adapters/source/stitch.py)
├── ZeplinAdapter    (futuro)
└── RawJsonAdapter   (src/harness/adapters/source/raw_json.py)
```

| Item | Descripción | Criterio de éxito | Estado |
|------|-------------|-------------------|--------|
| 2.1 | `BaseAdapter` con `fetch()`, `snap()`, `score()`, `archaeologist()` | Interface definida en `base.py`, tests de contrato | ✅ |
| 2.2 | `FigmaAdapter` — refactor de `factory_design_system_snap.py` | Misma salida que V1, + tests | ✅ |
| 2.3 | `StitchAdapter` — refactor de `factory_stitch_snap.py` | Misma salida que V1, + tests | ✅ |
| 2.4 | `quality_score()` en cada adapter | Figma sin Auto Layout → 0.2; Stitch con DESIGN.md → 0.9 | ✅ |
| 2.5 | `RawJsonAdapter` | Cualquier JSON con keys `padding`, `cornerRadius`, etc. → snap | ✅ |

**Anti-governanza**: Si `score()` es bajo (< 0.4), el logger dice
`[DS] Low quality input (0.2) — archaeologist mode auto-activated`. Sin
fricción, sin gates.

### Fase 3: Framework Adapters

**Objetivo**: Traducir `SemanticIntent` a código real en cada tecnología.

| Item | Descripción | Criterio de éxito | Estado |
|------|-------------|-------------------|--------|
| 3.1 | `FrameworkAdapter` base en `aidlc-scripts/harness_adapters/framework/base.py` | `render(intent) -> code`, `validate(code) -> ComplianceReport` | ✅ |
| 3.2 | `ReactAdapter` — JSX + Tailwind/CSS-in-JS | Reemplaza el actual `ui-compiler.md` S1-4 | ✅ |
| 3.3 | `AngularAdapter` — templates + componentes | Componente Angular generado desde el mismo intento | ✅ |
| 3.4 | `FlutterAdapter` — Widget tree | Widget tree desde el mismo intento | ✅ |
| 3.5 | `HtmlAdapter` — HTML semantico + CSS classes | Fallback universal para cualquier proyecto web | ✅ |
| 3.6 | `ui-constraint-validator` V2 | Valida sobre `SemanticIntent`, no sobre sintaxis | ✅ |

**Anti-governanza**: Cada adapter se autoveriﬁca con `validate()`. Sin
validación cruzada, sin procesos manuales. `framework_props` escape hatch
para lo que no cubre el modelo.

### Fase 4: Drift Detection Real

**Objetivo**: Implementar el `visual-feedback.md` de verdad.

| Item | Descripción | Criterio de éxito | Estado |
|------|-------------|-------------------|--------|
| 4.1 | `factory_drift_detect.py` | Screenshot (Playwright) -> diff con baseline (pixelmatch) -> `DiffReport` | ✅ |
| 4.2 | Baseline manager | Guarda/recupera screenshots por `component+variant` en `design-system/screenshots/` | ✅ |
| 4.3 | Pipeline hook en `build-test-agent` | Si `ui: true` y Playwright disponible, captura screenshot post-build | ⬜ |
| 4.4 | Drift gate con umbral configurable | `diff > 5%` -> log; `diff > 15%` -> `needs_human` con diff image | ⬜ |
| 4.5 | Knowledge reinforcement | Approval -> `factory_design_system_learn.py approve` conectado en ship-agent | ⬜ |

**Anti-governanza**: Drift nunca bloquea por defecto. Solo log. Umbral
`needs_human` conﬁgurable en `project-profile.md`. Sin Playwright → skip
silencioso.

### Fase 5: Template Engine for Primitives

**Objetivo**: Completar las 7 primitivas faltantes sin trabajo manual tedioso.

| Item | Descripción | Criterio de éxito | Estado |
|------|-------------|-------------------|--------|
| 5.1 | `factory_primitive_gen.py generate <name>` | Genera `design.md`, `anatomy.md`, `do-dont.md` desde template | ✅ |
| 5.2 | Templates multi-framework | `--style web` vs `--style flutter` -> output distinto | ✅ |
| 5.3 | Batch: `generate --all-missing` | Completa Stack, Inline, Box, Input, Text, Surface, Icon en 1 comando | ✅ |
| 5.4 | Eliminar `queprueba/design-system/` | Duplicado fantasma — ya no existe | ✅ |

**Anti-governanza**: Templates sensatos con override total. Se editan a mano
si no sirven. Sin validación obligatoria post-generación.

### Fase 6: Tests de Integración

**Objetivo**: Tests que cubren el pipeline completo, no solo unitarios.

| Item | Descripción | Estado |
|------|-------------|--------|
| 6.1 | Test: Figma JSON -> snap -> SemanticIntent -> React code | ✅ |
| 6.2 | Test: Same SemanticIntent -> Angular / Flutter / HTML code | ✅ |
| 6.3 | Test: Bad Figma (sin Auto Layout) -> archaeologist -> output usable | ✅ |
| 6.4 | Test: Drift detection -> diff report | ✅ |
| 6.5 | Test: Quality score -> token set incompleto -> score bajo | ✅ |

---

## Lo que NO cambia de V1

- `design-system/tokens/` — el formato funciona. No se toca.
- `design-system/patterns/` — los patrones son universales.
- `design-system/anti-patterns/` — válidos para toda UI.
- `factory_design_system_learn.py` — el loop de refuerzo funciona.
- `INDEX.md` — se mantiene como catálogo, se auto-actualiza.

## Lo que se elimina

| Archivo | Motivo |
|---------|--------|
| `design-system/primitives/**/*.tsx` | No hay referencia canónica única. Cada adapter genera su código. |
| `queprueba/design-system/` | Duplicado |

## Lo que se depreca (compatibilidad 1 versión)

| Archivo | Reemplazo |
|---------|-----------|
| `ui-compiler.md` §1-4 (intent→code) | `FrameworkAdapter.render()` |
| `design-system-composer/SKILL.md` Step 3 | `DesignSystemHarness.compose_intent()` |
| `ui-constraint-validator/SKILL.md` Step 2 | `FrameworkAdapter.validate()` |
| `factory_design_system_snap.py` | `FigmaAdapter` |
| `factory_stitch_snap.py` | `StitchAdapter` |

---

## Principios de diseño

### 1. Lazy por defecto

El harness carga tokens + adapters bajo demanda. El proﬁle detecta `ui: true`
+ `tech_stack` y solo entonces selecciona adapter.

### 2. Validación rápida, no bloqueante

Cada fase emite `warnings[]` + `suggestions[]`. Solo errores categóricos
(sin tokens, adapter no encontrado) bloquean. El code-generator decide.

### 3. Sin acoplamiento a framework

`SemanticIntent` no contiene JSX, TSX, ni nada de un framework especíﬁco.
Cada adapter es un plugin (~200 líneas). Añadir un framework = implementar
`render(intent)` + `validate(code)`.

### 4. Sin duplicación de lógica

Validación de tokens en `DesignSystemHarness.validate_tokens()`. Adapters de
fuente solo parsean y snapped. Adapters de framework solo renderizan.

### 5. Drift como dato, no como gate

Se mide siempre que hay Playwright. Se reporta siempre. Solo bloquea si
umbral superado Y proyecto lo conﬁguró. Por defecto: warning.

---

## Roadmap

| Fase | Semana | Depende de |
|------|--------|------------|
| Fase 1: Core Engine | 1 | — |
| Fase 2: Source Adapters | 2 | Fase 1 |
| Fase 3: Framework Adapters | 3 | Fase 1 |
| Fase 4: Drift Detection | 3-4 | Fase 3 |
| Fase 5: Primitive Generator | 4 | — (independiente) |
| Fase 6: Integration Tests | 4-5 | Fases 1-4 |

Cada fase es independiente y shippeable. No hay "big bang".

---

## Métricas de éxito

| Métrica | Objetivo | Cómo se mide |
|---------|----------|--------------|
| Tiempo de generación UI por slice | < 5s overhead sobre V1 | CI benchmark |
| Frameworks soportados en ship | 4 (React, Angular, Flutter, Html) | Adapters implementados + tests | ✅ 4/4 |
| Tests de integración | 12 | `pytest tests/ --harness` |
| Drift detection rate | > 80% | Diff contra baseline en CI |
| Primitivas completas | 8/8 | `resolve list --json` |
| Quality score accuracy | Score bajo ↔ archaeologist mode | Test: Figma caótico |
