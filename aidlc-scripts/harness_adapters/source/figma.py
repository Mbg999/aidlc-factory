from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from .base import DesignSourceAdapter, snap_value

_STYLE_KEYS = [
    "paddingLeft", "paddingRight", "paddingTop", "paddingBottom",
    "padding", "itemSpacing", "gap",
    "marginLeft", "marginRight", "marginTop", "marginBottom",
    "cornerRadius", "borderRadius", "cornerSmoothing",
    "fontSize", "letterSpacing",
    "fills", "strokes", "background", "backgroundColor",
    "color", "borderColor", "strokeColor", "fillColor",
    "effects",
]


class FigmaAdapter(DesignSourceAdapter):
    """Reads Figma JSON node data and snaps values to canonical tokens."""

    def __init__(self, spacing: list[int] | None = None,
                 radius: list[int] | None = None,
                 font_sizes: list[int] | None = None,
                 color_map: dict[str, str] | None = None):
        self.spacing = spacing or [4, 8, 12, 16, 24, 32]
        self.radius = radius or [0, 3, 6, 12, 9999]
        self.font_sizes = font_sizes or [12, 14, 16, 20, 24, 32, 40]
        self.color_map = color_map or {}

    def fetch(self, source: str) -> Any:
        path = Path(source)
        if not path.exists():
            raise FileNotFoundError(f"Figma file not found: {path}")
        return json.loads(path.read_text(encoding="utf-8"))

    def snap(self, raw: Any, tokens: dict | None = None) -> dict:
        if isinstance(raw, list):
            snapped_list = []
            all_corrections = []
            for node in raw:
                sn, corr = self._snap_node(node)
                snapped_list.append(sn)
                all_corrections.extend(corr)
            return {
                "snapped": snapped_list,
                "corrections": all_corrections,
                "correction_count": len(all_corrections),
            }

        snapped_node, corrections = self._snap_node(raw)
        return {
            "snapped": snapped_node,
            "corrections": corrections,
            "correction_count": len(corrections),
        }

    def score(self, raw: Any) -> float:
        """Score based on Auto Layout usage and recognizable structure."""
        nodes = raw if isinstance(raw, list) else [raw]
        total = 0
        auto_layout_count = 0
        named_count = 0

        def _walk(n: dict):
            nonlocal total, auto_layout_count, named_count
            total += 1
            if n.get("layoutMode") in ("HORIZONTAL", "VERTICAL"):
                auto_layout_count += 1
            if n.get("name") and n["name"] not in ("Frame", "Group", "Rectangle"):
                named_count += 1
            for child in n.get("children", []):
                _walk(child)

        for node in nodes:
            _walk(node)

        if total == 0:
            return 0.0

        auto_score = auto_layout_count / total if total > 0 else 0
        named_score = named_count / total if total > 0 else 0
        return round(0.6 * auto_score + 0.4 * named_score, 2)

    def archaeologist(self, raw: Any) -> dict:
        """Extract only text + inputs + reading order from Figma chaos."""
        texts: list[str] = []
        inputs: list[dict] = []
        order: list[str] = []
        seen_y: dict[float, list[str]] = {}

        def _walk(n: dict, depth: int = 0):
            name = n.get("name", "")
            ntype = n.get("type", "")
            y = n.get("y", depth * 100)

            if ntype == "TEXT":
                chars = n.get("characters", "")
                if chars.strip():
                    texts.append(chars.strip())
                    seen_y.setdefault(y // 10, []).append(chars.strip())

            if n.get("placeholder") or "input" in name.lower():
                inputs.append({
                    "placeholder": n.get("placeholder", name),
                    "type": n.get("inputType", "text"),
                })

            for child in n.get("children", []):
                _walk(child, depth + 1)

        for node in (raw if isinstance(raw, list) else [raw]):
            _walk(node)

        reading_order = []
        for y_pos in sorted(seen_y):
            reading_order.extend(seen_y[y_pos])

        return {
            "texts": texts,
            "inputs": inputs,
            "reading_order": reading_order,
        }

    def _snap_node(self, node: dict) -> tuple[dict, list[dict]]:
        result = dict(node)
        corrections: list[dict] = []

        for key in _STYLE_KEYS:
            if key not in node:
                continue
            entry = snap_value(key, node[key], self.spacing, self.radius,
                               self.font_sizes, self.color_map)
            if entry["was_corrected"]:
                result[key] = entry["snapped"]
                corrections.append(entry)

        if "children" in node and isinstance(node["children"], list):
            result["children"] = []
            for child in node["children"]:
                child_result, child_corr = self._snap_node(child)
                result["children"].append(child_result)
                corrections.extend(child_corr)

        return result, corrections
