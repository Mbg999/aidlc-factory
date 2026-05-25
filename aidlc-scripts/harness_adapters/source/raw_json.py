from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from .base import DesignSourceAdapter, snap_value


class RawJsonAdapter(DesignSourceAdapter):
    """Snaps any JSON with style-like keys (padding, cornerRadius, etc.)
    to canonical tokens. Useful for Zeplin, custom design tools, or API output."""

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
            try:
                return json.loads(source)
            except json.JSONDecodeError:
                raise FileNotFoundError(f"File not found and not valid JSON: {source}")
        return json.loads(path.read_text(encoding="utf-8"))

    def snap(self, raw: Any, tokens: dict | None = None) -> dict:
        corrections: list[dict] = []

        def _snap_obj(obj: Any) -> Any:
            if isinstance(obj, dict):
                snapped = {}
                for k, v in obj.items():
                    entry = snap_value(k, v, self.spacing, self.radius,
                                       self.font_sizes, self.color_map)
                    if entry["was_corrected"]:
                        corrections.append(entry)
                        snapped[k] = entry["snapped"]
                    else:
                        snapped[k] = _snap_obj(v)
                return snapped
            elif isinstance(obj, list):
                return [_snap_obj(item) for item in obj]
            return obj

        snapped = _snap_obj(raw)
        return {
            "snapped": snapped,
            "corrections": corrections,
            "correction_count": len(corrections),
        }

    def score(self, raw: Any) -> float:
        """Score based on how many recognized style keys exist."""
        style_keys = {"padding", "margin", "gap", "radius", "cornerRadius",
                      "fontSize", "color", "background", "border"}
        found = 0

        def _walk(obj: Any):
            nonlocal found
            if isinstance(obj, dict):
                for k in obj:
                    if k.lower() in style_keys:
                        found += 1
                for v in obj.values():
                    _walk(v)
            elif isinstance(obj, list):
                for item in obj:
                    _walk(item)

        _walk(raw)
        return round(min(found / 10, 1.0), 2)
