from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from .base import DesignSourceAdapter, snap_value, snap_color, normalize_hex


_INLINE_STYLE_RE = re.compile(r'style="([^"]*)"')
_CSS_DECL_RE = re.compile(r"([a-z-]+)\s*:\s*([^;{}]+)")
_DESIGN_MD_TOKEN_RE = re.compile(r"\|\s*`([^`]+)`\s*\|\s*`?([^`|\n]+)`?\s*\|")


class StitchAdapter(DesignSourceAdapter):
    """Reads Google Stitch HTML/CSS output and snaps to canonical tokens."""

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
            raise FileNotFoundError(f"Stitch file not found: {path}")
        content = path.read_text(encoding="utf-8")
        ext = path.suffix.lower()
        return {"content": content, "ext": ext, "path": str(path)}

    def snap(self, raw: dict, tokens: dict | None = None) -> dict:
        content = raw.get("content", "")
        ext = raw.get("ext", ".html")

        if ext in (".html", ".htm"):
            return self._snap_html(content)
        elif ext == ".css":
            return self._snap_css(content)
        elif ext == ".md":
            return self._snap_designmd(content)
        else:
            if "<html" in content[:500] or "<div" in content[:500]:
                return self._snap_html(content)
            return self._snap_designmd(content)

    def score(self, raw: dict) -> float:
        content = raw.get("content", "")
        ext = raw.get("ext", ".html")
        score = 0.5

        if ext == ".md":
            tokens_found = len(_DESIGN_MD_TOKEN_RE.findall(content))
            score += min(tokens_found / 10, 0.4)
        elif ext in (".html", ".htm"):
            has_structure = bool(re.search(r"<(html|head|body|main|section)", content))
            if has_structure:
                score += 0.2
            inline_styles = len(_INLINE_STYLE_RE.findall(content))
            if inline_styles < 20:
                score += 0.1
            ids_or_classes = len(re.findall(r'\b(id|class)="', content))
            if ids_or_classes > 3:
                score += 0.1

        return round(min(score, 1.0), 2)

    def archaeologist(self, raw: dict) -> dict:
        content = raw.get("content", "")
        texts = re.findall(r">([^<]{2,})<", content)
        inputs = [
            {"placeholder": m.group(1) or ""}
            for m in re.finditer(r'placeholder="([^"]*)"', content)
        ]
        return {
            "texts": [t.strip() for t in texts if t.strip()],
            "inputs": inputs,
            "reading_order": [t.strip() for t in texts if t.strip()],
        }

    def _snap_html(self, html: str) -> dict:
        corrections: list[dict] = []

        def _replace_style(m: re.Match) -> str:
            block = m.group(1)
            new_decls: list[str] = []
            for decl in block.split(";"):
                decl = decl.strip()
                if not decl or ":" not in decl:
                    new_decls.append(decl)
                    continue
                key, val = decl.split(":", 1)
                snapped = snap_value(key.strip(), val.strip(),
                                     self.spacing, self.radius,
                                     self.font_sizes, self.color_map)
                if snapped["was_corrected"]:
                    corrections.append(snapped)
                new_decls.append(f"{key.strip()}: {snapped['snapped']}")
            return 'style="{}"'.format("; ".join(new_decls))

        snapped_html = _INLINE_STYLE_RE.sub(_replace_style, html)
        return {
            "original": html,
            "snapped": snapped_html,
            "corrections": corrections,
            "correction_count": len(corrections),
        }

    def _snap_css(self, css: str) -> dict:
        corrections: list[dict] = []

        def _replace_decl(m: re.Match) -> str:
            key, val = m.group(1).strip(), m.group(2).strip()
            snapped = snap_value(key, val, self.spacing, self.radius,
                                 self.font_sizes, self.color_map)
            if snapped["was_corrected"]:
                corrections.append(snapped)
            return f"{key}: {snapped['snapped']}"

        snapped_css = _CSS_DECL_RE.sub(_replace_decl, css)
        return {
            "original": css,
            "snapped": snapped_css,
            "corrections": corrections,
            "correction_count": len(corrections),
        }

    def _snap_designmd(self, content: str) -> dict:
        mapped: dict[str, list[dict]] = {
            "spacing": [], "radius": [], "typography": [], "color": [],
        }
        unmapped: list[dict] = []

        for line in content.splitlines():
            m = _DESIGN_MD_TOKEN_RE.search(line)
            if not m:
                continue
            name, value = m.group(1).strip(), m.group(2).strip()
            kl = name.lower()
            if any(k in kl for k in ("padding", "margin", "gap", "spacing")):
                mapped["spacing"].append({"token": name, "value": value})
            elif any(k in kl for k in ("radius", "rounded", "corner")):
                mapped["radius"].append({"token": name, "value": value})
            elif any(k in kl for k in ("font", "size", "typography")):
                mapped["typography"].append({"token": name, "value": value})
            elif any(k in kl for k in ("color", "fill", "stroke", "background")):
                mapped["color"].append({"token": name, "value": value})
            else:
                unmapped.append({"token": name, "value": value})

        return {
            "mapped": {k: v for k, v in mapped.items() if v},
            "unmapped": unmapped,
            "token_count": sum(len(v) for v in mapped.values()),
        }
