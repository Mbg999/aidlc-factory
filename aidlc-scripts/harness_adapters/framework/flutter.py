from __future__ import annotations

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from harness_engine import ComplianceReport, SemanticIntent
from .base import FrameworkAdapter


class FlutterAdapter(FrameworkAdapter):
    """Generates Flutter (Dart) widget code from SemanticIntent."""

    def render(self, intent: SemanticIntent) -> str:
        parts: list[str] = []
        parts.append(self._render_imports())
        parts.append(self._render_widgets(intent))
        return "\n\n".join(parts)

    def validate(self, code: str, intent: SemanticIntent) -> ComplianceReport:
        deviations: list[dict] = []
        warnings: list[str] = []

        if "import" not in code or "flutter" not in code:
            warnings.append("No Flutter import found")

        spacing_vals = set()
        if "spacing" in intent.tokens:
            spacing_vals = set(intent.tokens["spacing"].values())

        for val in spacing_vals:
            if "SizedBox(height: {})".format(val) in code:
                deviations.append({
                    "property": "spacing",
                    "found": "SizedBox(height: {})".format(val),
                    "corrected_to": "SizedBox(height: spacing_{})".format(val),
                    "file": "generated",
                    "element": "layout",
                })

        return ComplianceReport(
            passed=len(deviations) == 0,
            total_elements=len(intent.components),
            deviations=deviations,
            warnings=warnings,
        )

    def _render_imports(self) -> str:
        return "import 'package:flutter/material.dart';"

    def _render_widgets(self, intent: SemanticIntent) -> str:
        widgets: list[str] = []

        if intent.layout:
            for node in intent.layout:
                w = self._render_layout_node(node, intent.tokens, 0, intent)
                widgets.append(w)

            for comp in intent.components:
                widgets.append(self._render_component(comp))

            children = ", ".join(
                c.get("label", "Container()") + "()"
                for c in intent.components
            )
            widgets.append(
                "class App extends StatelessWidget {\n"
                "  const App({super.key});\n\n"
                "  Widget build(BuildContext context) {\n"
                "    return MaterialApp(\n"
                "      home: Scaffold(\n"
                "        body: Column(\n"
                "          children: [{children}],\n"
                "        ),\n"
                "      ),\n"
                "    );\n"
                "  }\n"
                "}"
            )
        else:
            for comp in intent.components:
                widgets.append(self._render_component(comp))
            widgets.append(
                "class App extends StatelessWidget {\n"
                "  const App({super.key});\n\n"
                "  Widget build(BuildContext context) {\n"
                "    return MaterialApp(\n"
                "      home: Scaffold(\n"
                "        body: Column(\n"
                "          children: [\n"
                + ",\n".join(
                    "            {c}()".format(c=comp.get("label", "Container"))
                    for comp in intent.components
                ) + "\n"
                "          ],\n"
                "        ),\n"
                "      ),\n"
                "    );\n"
                "  }\n"
                "}"
            )

        return "\n\n".join(widgets)

    def _render_component(self, comp: dict) -> str:
        ctype = comp.get("type", "text")
        label = comp.get("label", "Component")
        variant = comp.get("variant", "primary")
        size = comp.get("size", "md")

        if ctype == "button":
            height = 36 if size == "md" else (28 if size == "sm" else 44)
            bg = "Colors.blue" if variant == "primary" else "Colors.grey.shade200"
            return (
                "class {c} extends StatelessWidget {{\n"
                "  final VoidCallback? onPressed;\n"
                "  final Widget child;\n"
                "  const {c}({{super.key, this.onPressed, required this.child}});\n\n"
                "  Widget build(BuildContext context) {{\n"
                "    return SizedBox(\n"
                "      height: {h},\n"
                "      child: ElevatedButton(\n"
                "        style: ElevatedButton.styleFrom(backgroundColor: {bg}),\n"
                "        onPressed: onPressed,\n"
                "        child: child,\n"
                "      ),\n"
                "    );\n"
                "  }}\n"
                "}}"
            ).format(c=label, h=height, bg=bg)
        elif ctype == "input":
            return (
                "class {c} extends StatelessWidget {{\n"
                "  final String? placeholder;\n"
                "  final TextEditingController? controller;\n"
                "  const {c}({{super.key, this.placeholder, this.controller}});\n\n"
                "  Widget build(BuildContext context) {{\n"
                "    return TextField(\n"
                "      decoration: InputDecoration(\n"
                "        hintText: placeholder,\n"
                "        border: OutlineInputBorder(),\n"
                "        contentPadding: EdgeInsets.symmetric(horizontal: 12, vertical: 8),\n"
                "      ),\n"
                "      controller: controller,\n"
                "    );\n"
                "  }}\n"
                "}}"
            ).format(c=label)
        elif ctype == "text":
            return (
                "class {c} extends StatelessWidget {{\n"
                "  final String data;\n"
                "  final double fontSize;\n"
                "  const {c}({{super.key, required this.data, this.fontSize = 14}});\n\n"
                "  Widget build(BuildContext context) {{\n"
                "    return Text(\n"
                "      data,\n"
                "      style: TextStyle(fontSize: fontSize),\n"
                "    );\n"
                "  }}\n"
                "}}"
            ).format(c=label)
        elif ctype == "link":
            return (
                "class {c} extends StatelessWidget {{\n"
                "  final String href;\n"
                "  final String label;\n"
                "  const {c}({{super.key, required this.href, required this.label}});\n\n"
                "  Widget build(BuildContext context) {{\n"
                "    return GestureDetector(\n"
                "      onTap: () {{ }},\n"
                "      child: Text(label, style: TextStyle(color: Colors.blue, decoration: TextDecoration.underline)),\n"
                "    );\n"
                "  }}\n"
                "}}"
            ).format(c=label)
        elif ctype == "icon":
            return (
                "class {c} extends StatelessWidget {{\n"
                "  final double size;\n"
                "  const {c}({{super.key, this.size = 24}});\n\n"
                "  Widget build(BuildContext context) {{\n"
                "    return Icon(Icons.star, size: size);\n"
                "  }}\n"
                "}}"
            ).format(c=label)
        return "class {c} extends StatelessWidget {{ final Widget child; const {c}({{super.key, required this.child}}); Widget build(BuildContext context) => child; }}".format(c=label)

    def _render_layout_node(self, node: dict, tokens: dict, depth: int, intent: SemanticIntent | None = None) -> str:
        indent = "  " * (depth + 1)
        ltype = node.get("type", "box")
        gap = node.get("gap", "md")
        gap_val = self._token_to_tailwind(gap, tokens) or 8
        children = node.get("children", [])

        child_widgets: list[str] = []
        for child in children:
            if "type" in child and child["type"] in ("stack", "inline", "box", "grid", "surface"):
                child_widgets.append(self._render_layout_node(child, tokens, depth + 1, intent))
            else:
                child_label = child.get("label", "Container")
                child_widgets.append("{indent}{c}()".format(indent=indent + "  ", c=child_label))

        if ltype == "stack":
            spacers = []
            for i, cw in enumerate(child_widgets):
                if i > 0:
                    spacers.append("{i}SizedBox(height: {g}),".format(i=indent, g=gap_val))
                spacers.append(cw)
            children_str = "\n".join(spacers) if spacers else ""
            return (
                "{i}Column(\n"
                "{children}\n"
                "{i})".format(i=indent, children=children_str)
            )
        elif ltype == "inline":
            spacers = []
            for i, cw in enumerate(child_widgets):
                if i > 0:
                    spacers.append("{i}SizedBox(width: {g}),".format(i=indent, g=gap_val))
                spacers.append(cw)
            children_str = "\n".join(spacers) if spacers else ""
            return (
                "{i}Row(\n"
                "{children}\n"
                "{i})".format(i=indent, children=children_str)
            )
        else:
            if not child_widgets:
                return "{i}Container()".format(i=indent)
            children_str = "\n".join(child_widgets)
            return (
                "{i}Container(\n"
                "{children}\n"
                "{i})".format(i=indent, children=children_str)
            )
