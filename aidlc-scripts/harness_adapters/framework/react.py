from __future__ import annotations

import re

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from harness_engine import ComplianceReport, SemanticIntent

from .base import FrameworkAdapter


class ReactAdapter(FrameworkAdapter):
    """Generates React (TSX) code from SemanticIntent."""

    def render(self, intent: SemanticIntent) -> str:
        parts: list[str] = []
        parts.append(self._render_imports())

        if intent.layout:
            parts.append(self._render_layout_component(intent.layout, intent.tokens))

        for comp in intent.components:
            parts.append(self._render_component(comp, intent.tokens))

        if intent.layout:
            parts.append(self._render_app_component(intent))
        else:
            parts.append(self._render_standalone_page(intent))

        return "\n\n".join(parts)

    def validate(self, code: str, intent: SemanticIntent) -> ComplianceReport:
        deviations: list[dict] = []
        warnings: list[str] = []

        spacing_vals = set()
        if "spacing" in intent.tokens:
            spacing_vals = set(intent.tokens["spacing"].values())
        radius_vals = set()
        if "radius" in intent.tokens:
            radius_vals = set(v for v in intent.tokens["radius"].values() if v < 9999)

        for token_cat, values, label in [
            ("spacing", spacing_vals, "spacing"),
            ("radius", radius_vals, "radius"),
        ]:
            for val in values:
                for unit in ("px", "rem", "em"):
                    pattern = rf"{val}{unit}\b"
                    matches = re.findall(pattern, code)
                    if matches:
                        deviations.append({
                            "property": label,
                            "found": "{}{}".format(val, unit),
                            "corrected_to": "token ({})".format(label),
                            "file": "generated",
                            "element": "inline style",
                        })

        return ComplianceReport(
            passed=len(deviations) == 0,
            total_elements=len(intent.components),
            deviations=deviations,
            warnings=warnings,
        )

    # ── Internal render helpers ─────────────────────────────────────────

    def _render_imports(self) -> str:
        return 'import React from "react";'

    def _render_component(self, comp: dict, tokens: dict) -> str:
        ctype = comp.get("type", "text")
        label = comp.get("label", "")
        variant = comp.get("variant", "default")
        size = comp.get("size", "md")

        if ctype == "button":
            return self._button_component(label, variant, size)
        elif ctype == "input":
            return self._input_component(label)
        elif ctype == "text":
            return self._text_component(label)
        elif ctype == "link":
            return self._link_component(label)
        elif ctype == "icon":
            return self._icon_component(label)
        return ""

    def _button_component(self, label: str, variant: str, size: str) -> str:
        props = "{{ variant = '{}', size = '{}', disabled = false, children, onClick, dataTestid }}: {}Props".format(
            variant, size, label
        )
        return (
            "interface {}Props {{\n"
            "  variant?: '{}' | 'secondary';\n"
            "  size?: 'sm' | 'md' | 'lg';\n"
            "  disabled?: boolean;\n"
            "  children: React.ReactNode;\n"
            "  onClick?: () => void;\n"
            "  dataTestid?: string;\n"
            "}}\n\n"
            "export function {}({}) {{\n"
            "  const variantCls = variant === 'secondary' ? 'bg-gray-200 text-gray-900' : 'bg-blue-600 text-white hover:bg-blue-700';\n"
            "  const sizeCls = size === 'sm' ? 'px-3 py-1.5 text-sm' : size === 'lg' ? 'px-6 py-3 text-lg' : 'px-4 py-2 text-base';\n"
            "  const cls = 'inline-flex items-center justify-center font-medium rounded focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed '.concat(variantCls, ' ', sizeCls);\n"
            "  return <button className={{cls}} disabled={{disabled}} data-testid={{dataTestid}} onClick={{onClick}}>{{children}}</button>;\n"
            "}}"
        ).format(label, variant, label, props)

    def _input_component(self, label: str) -> str:
        return (
            "interface {}Props {{\n"
            "  placeholder?: string;\n"
            "  value?: string;\n"
            "  onChange?: (e: React.ChangeEvent<HTMLInputElement>) => void;\n"
            "  error?: string;\n"
            "  dataTestid?: string;\n"
            "}}\n\n"
            "export function {}({{ placeholder = '', value, onChange, error, dataTestid }}: {}Props) {{\n"
            "  return (\n"
            "    <div>\n"
            "      <input\n"
            "        className={{\n"
            "          'block w-full rounded border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500' +\n"
            "          (error ? ' border-red-500' : '')\n"
            "        }}\n"
            "        placeholder={{placeholder}}\n"
            "        value={{value}}\n"
            "        onChange={{onChange}}\n"
            "        data-testid={{dataTestid}}\n"
            "      />\n"
            "      {{error && <p className='mt-1 text-xs text-red-500'>{{error}}</p>}}\n"
            "    </div>\n"
            "  );\n"
            "}}"
        ).format(label, label, label)

    def _text_component(self, label: str) -> str:
        return (
            "interface {}Props {{\n"
            "  children: React.ReactNode;\n"
            "  as?: 'p' | 'h1' | 'h2' | 'h3' | 'h4' | 'span';\n"
            "  className?: string;\n"
            "}}\n\n"
            "export function {}({{ children, as: Tag = 'p', className = '' }}: {}Props) {{\n"
            "  return <Tag className={{className}}>{{children}}</Tag>;\n"
            "}}"
        ).format(label, label, label)

    def _link_component(self, label: str) -> str:
        return (
            "interface {}Props {{\n"
            "  href: string;\n"
            "  children: React.ReactNode;\n"
            "  className?: string;\n"
            "  dataTestid?: string;\n"
            "}}\n\n"
            "export function {}({{ href, children, className = '', dataTestid }}: {}Props) {{\n"
            "  return (\n"
            "    <a\n"
            "      href={{href}}\n"
            "      className={{'text-blue-600 hover:text-blue-800 underline ' + className}}\n"
            "      data-testid={{dataTestid}}\n"
            "    >{{children}}</a>\n"
            "  );\n"
            "}}"
        ).format(label, label, label)

    def _icon_component(self, label: str) -> str:
        return (
            "interface {}Props {{\n"
            "  name?: string;\n"
            "  size?: number;\n"
            "  className?: string;\n"
            "}}\n\n"
            "export function {}({{ name, size = 24, className = '' }}: {}Props) {{\n"
            "  return (\n"
            "    <svg\n"
            "      width={{size}} height={{size}}\n"
            "      className={{className}}\n"
            "      fill='none' stroke='currentColor' viewBox='0 0 24 24'\n"
            "      data-testid={{name ? 'icon-' + name : 'icon'}}\n"
            "    >\n"
            "      <path strokeLinecap='round' strokeLinejoin='round' strokeWidth={{2}} "
            "d='M13 10V3L4 14h7v7l9-11h-7z' />\n"
            "    </svg>\n"
            "  );\n"
            "}}"
        ).format(label, label, label)

    def _render_layout_component(self, layout: list[dict], tokens: dict) -> str:
        def _render_node(node: dict, depth: int = 0) -> str:
            indent = "  " * (depth + 1)
            ltype = node.get("type", "box")
            gap = node.get("gap", "md")
            padding = node.get("padding", "md")
            children = node.get("children", [])

            tw_gap = self._token_to_tailwind(gap, tokens) or 4
            tw_pad = self._token_to_tailwind(padding, tokens) or 4

            if ltype == "stack":
                cls = "flex flex-col gap-{}".format(tw_gap)
            elif ltype == "inline":
                cls = "flex flex-row gap-{}".format(tw_gap)
            elif ltype == "grid":
                cls = "grid grid-cols-3 gap-4"
            elif ltype == "surface":
                bg = node.get("background", "gray-100")
                cls = "rounded bg-{} p-{}".format(bg, tw_pad)
            else:
                cls = "p-{}".format(tw_pad)

            if not children:
                return "{}<div className='{}' />".format(indent, cls)

            child_lines = []
            for child in children:
                if "type" in child and child["type"] in ("stack", "inline", "box", "grid", "surface"):
                    child_lines.append(_render_node(child, depth + 1))
                else:
                    comp_name = child.get("label", "div")
                    child_lines.append("{}  <{} />".format(indent, comp_name))

            children_str = "\n".join(child_lines)
            return "{indent}<div className='{cls}'>\n{children}\n{indent}</div>".format(
                indent=indent, cls=cls, children=children_str
            )

        nodes = "\n".join(_render_node(n, 0) for n in layout)
        return (
            "interface PageLayoutProps {{\n"
            "  children?: React.ReactNode;\n"
            "}}\n\n"
            "export function PageLayout({{ children }}: PageLayoutProps) {{\n"
            "{}\n"
            "}}"
        ).format(nodes)

    def _render_app_component(self, intent: SemanticIntent) -> str:
        comp_names = [c.get("label", "div") for c in intent.components]
        children = "\n".join("        <{} />".format(c) for c in comp_names)
        return (
            "export default function App() {{\n"
            "  return (\n"
            "    <PageLayout>\n"
            "{}\n"
            "    </PageLayout>\n"
            "  );\n"
            "}}"
        ).format(children)

    def _render_standalone_page(self, intent: SemanticIntent) -> str:
        comps = "\n".join(
            "      <{} />".format(c.get("label", "div"))
            for c in intent.components
        )
        return (
            "export default function App() {{\n"
            "  return (\n"
            "    <div className='p-4 space-y-4'>\n"
            "{}\n"
            "    </div>\n"
            "  );\n"
            "}}"
        ).format(comps)
