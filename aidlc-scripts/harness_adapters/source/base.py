from __future__ import annotations

import re
from abc import ABC, abstractmethod
from typing import Any


class DesignSourceAdapter(ABC):
    """Unified interface for reading and snapping design source data.
    
    Implementations: FigmaAdapter, StitchAdapter, RawJsonAdapter, etc.
    """

    @abstractmethod
    def fetch(self, source: str) -> Any:
        """Read raw data from the source file or string."""
        ...

    @abstractmethod
    def snap(self, raw: Any, tokens: dict) -> dict:
        """Snap raw values to canonical tokens.
        
        Returns {'snapped': ..., 'corrections': [...], 'correction_count': int}.
        """
        ...

    def score(self, raw: Any) -> float:
        """Quality score (0..1) of the raw input.
        
        Lower score = more chaotic data. Triggers archaeologist mode when < 0.4.
        Override per adapter for source-specific heuristics.
        """
        return 1.0

    def archaeologist(self, raw: Any) -> dict:
        """Extract only text content and reading order from chaotic input.
        
        Discards all style, coordinates, colors, sizes.
        Returns {'texts': [...], 'inputs': [...], 'reading_order': [...]}.
        """
        return {"texts": [], "inputs": [], "reading_order": []}


# ── Shared snap helpers (used by FigmaAdapter, StitchAdapter) ──────────────

_SNAPPABLE_CSS = ("padding", "margin", "gap", "radius", "rounded", "corner",
                  "font-size", "fontsize", "font_size", "color", "background",
                  "fill", "stroke")


def nearest(value: float, candidates: list[int]) -> int:
    return min(candidates, key=lambda c: abs(c - value))


def parse_px(raw: str | float | int) -> float:
    if isinstance(raw, (int, float)):
        return float(raw)
    m = re.search(r"([-+]?\d*\.?\d+)", str(raw))
    return float(m.group(1)) if m else 0.0


def normalize_hex(hex_str: str) -> str:
    h = hex_str.strip().lower().lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    return "#" + h


def hex_to_rgb(hex_str: str) -> tuple[int, int, int] | None:
    h = hex_str.strip().lower().lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    if len(h) != 6:
        return None
    try:
        return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))
    except ValueError:
        return None


COLOR_DISTANCE_THRESHOLD = 60.0


def snap_color(raw: str, color_map: dict[str, str]) -> tuple[str, str | None]:
    """Snap a raw hex to nearest known token. Returns (token, original) or (raw, None)."""
    normalized = normalize_hex(raw)
    for known_hex, token in color_map.items():
        if normalize_hex(known_hex) == normalized:
            return token, raw
    raw_rgb = hex_to_rgb(normalized)
    if raw_rgb:
        best_dist = float("inf")
        best_token = None
        for known_hex, token in color_map.items():
            known_rgb = hex_to_rgb(known_hex)
            if known_rgb:
                dist = sum((a - b) ** 2 for a, b in zip(raw_rgb, known_rgb)) ** 0.5
                if dist < best_dist:
                    best_dist = dist
                    best_token = token
        if best_token and best_dist < COLOR_DISTANCE_THRESHOLD:
            return best_token, raw
    return raw, None


_SPACING_NAMES = {4: "xs", 8: "sm", 12: "md", 16: "lg", 24: "xl", 32: "xxl"}
_RADIUS_NAMES = {0: "none", 3: "sm", 6: "md", 12: "lg", 9999: "full"}
_FONT_NAMES = {12: "caption", 14: "body", 16: "body-large", 20: "h4",
               24: "h3", 32: "h2", 40: "h1"}


def snap_value(key: str, raw_value: str | float | int,
               spacing: list[int], radius: list[int],
               font_sizes: list[int],
               color_map: dict[str, str]) -> dict:
    """Snap a single key-value pair to canonical tokens."""
    result = {
        "key": key, "raw": str(raw_value), "snapped": str(raw_value),
        "token_category": None, "was_corrected": False,
    }
    kl = key.lower()
    is_spacing = any(k in kl for k in ("padding", "margin", "gap", "inset", "itemspacing"))
    is_radius = any(k in kl for k in ("radius", "rounded", "corner"))
    is_font = any(k in kl for k in ("font-size", "fontsize", "font_size"))
    is_color = any(k in kl for k in ("color", "background", "fill", "stroke", "border-color"))

    try:
        px = parse_px(raw_value)
    except (ValueError, TypeError):
        px = 0.0

    if is_spacing and spacing:
        snapped = nearest(px, spacing)
        name = _SPACING_NAMES.get(snapped, f"_{snapped}px")
        result["snapped"] = f"{snapped}px"
        result["token_category"] = f"spacing.{name}"
        if abs(snapped - px) > 0.01:
            result["was_corrected"] = True

    elif is_radius and radius:
        snapped = nearest(px, radius)
        name = _RADIUS_NAMES.get(snapped, f"_{snapped}px")
        val_str = "9999px" if snapped >= 9999 else f"{snapped}px"
        result["snapped"] = val_str
        result["token_category"] = f"radius.{name}"
        if abs(snapped - px) > 0.01:
            result["was_corrected"] = True

    elif is_font and font_sizes:
        snapped = nearest(px, font_sizes)
        name = _FONT_NAMES.get(snapped, f"_{snapped}px")
        result["snapped"] = f"{snapped}px"
        result["token_category"] = f"font-size.{name}"
        if abs(snapped - px) > 0.01:
            result["was_corrected"] = True

    elif is_color and color_map:
        snapped_token, _ = snap_color(str(raw_value), color_map)
        if snapped_token != str(raw_value):
            result["snapped"] = snapped_token
            result["token_category"] = "color"
            result["was_corrected"] = True

    return result
