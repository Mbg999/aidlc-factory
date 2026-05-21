# Design System Index

Catalog of approved UI primitives, tokens, and composition patterns.
The factory selects from this index — it does not invent new primitives.

---

## Primitives

| Primitive | Description | When to use | When NOT to use |
|-----------|-------------|-------------|-----------------|
| `Button` | Action trigger, clickable | Forms, dialogs, toolbars, any primary action | Navigation links (use `<a>`), non-action text |
| `Stack` | Vertical layout container | arranging children top-to-bottom with consistent gap | Horizontal layouts (use `Inline`), grid layouts |
| `Inline` | Horizontal layout container | Arranging children left-to-right with consistent gap | Vertical layouts (use `Stack`), wrapping lists |
| `Box` | Generic surface with padding + radius | Cards, panels, containers, any styled wrapper | Plain divs without styling (use raw `<div>`) |
| `Input` | Text input field | Forms, search, data entry | Read-only display (use `Text`), multi-line (use `<textarea>`) |
| `Text` | Typography element | Paragraphs, labels, headings, captions | Interactive text (use `Button` or `<a>`) |
| `Surface` | Themed background container | Page sections, modals, sidebars, banners | Inline elements (use `Text`) |
| `Icon` | SVG icon wrapper | Buttons, inputs, empty states, alerts | Decorative images (use `<img>`) |

---

## Patterns (compositions)

| Pattern | Primitives used | When |
|---------|----------------|------|
| `form-layout` | Stack + Input + Button + Text | Data entry forms |
| `data-table` | Surface + Text + Inline + Box | Tabular data display |
| `navigation` | Inline + Button + Icon | Toolbars, nav bars |
| `modal-dialog` | Surface + Stack + Button + Text | Overlay dialogs |
| `settings-page` | Stack + Surface + Input + Text | Configuration UIs |
| `card-grid` | Grid + Surface + Box + Text | Card layouts |

---

## Token categories

| Category | File | Quick ref |
|----------|------|-----------|
| Spacing | `tokens/spacing.md` | 4, 8, 12, 16, 24, 32 |
| Typography | `tokens/typography.md` | 12/14/16/20/24/32px |
| Radius | `tokens/radius.md` | sm=3, md=6, lg=12 |
| Color | `tokens/color.md` | brand/neutral/danger/success |
| Elevation | `tokens/elevation.md` | 0-4 shadow levels |

---

## Anti-patterns (what NOT to do)

See `anti-patterns/`. Quick list:
- `broken-spacing` — arbitrary padding/margin values outside token set
- `inconsistent-radius` — mixing different radii on similar elements
- `overflowing-content` — fixed heights without overflow handling
- `no-hierarchy` — same font-size for heading and body
- `giant-forms` — single-column forms > 8 fields without grouping

---

## Usage stats (auto-updated by ship-agent)

| Primitive | Approved examples | Times used |
|-----------|------------------|------------|
| Button | 0 | 0 |
| Stack | 0 | 0 |
| Inline | 0 | 0 |
| Box | 0 | 0 |
| Input | 0 | 0 |
| Text | 0 | 0 |
| Surface | 0 | 0 |
| Icon | 0 | 0 |
