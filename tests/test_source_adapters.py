from __future__ import annotations

import json
from pathlib import Path

import pytest

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "aidlc-scripts"))
from harness_adapters.source.base import (
    normalize_hex, hex_to_rgb, snap_color, snap_value, nearest, parse_px,
)
from harness_adapters.source.figma import FigmaAdapter
from harness_adapters.source.stitch import StitchAdapter
from harness_adapters.source.raw_json import RawJsonAdapter


# ── Shared helpers ─────────────────────────────────────────────────────────

class TestHelpers:
    def test_nearest(self):
        assert nearest(13, [4, 8, 12, 16, 24, 32]) == 12
        assert nearest(5, [4, 8, 12]) == 4
        assert nearest(17, [4, 8, 12, 16, 24, 32]) == 16

    def test_parse_px(self):
        assert parse_px("13.4px") == 13.4
        assert parse_px(16) == 16.0
        assert parse_px("4") == 4.0

    def test_normalize_hex(self):
        assert normalize_hex("#FFF") == "#ffffff"
        assert normalize_hex("#2563EB") == "#2563eb"
        assert normalize_hex("fff") == "#ffffff"

    def test_hex_to_rgb(self):
        assert hex_to_rgb("#FF0000") == (255, 0, 0)
        assert hex_to_rgb("000") == (0, 0, 0)
        assert hex_to_rgb("invalid") is None

    def test_snap_color_exact(self):
        cmap = {"#2563EB": "brand.primary", "#EF4444": "danger"}
        token, raw = snap_color("#2563EB", cmap)
        assert token == "brand.primary"

    def test_snap_color_proximity(self):
        cmap = {"#2563EB": "brand.primary", "#FFFFFF": "white"}
        token, raw = snap_color("#1D4ED8", cmap)
        assert token == "brand.primary"

    def test_snap_color_no_match(self):
        cmap = {"#FFFFFF": "white"}
        token, raw = snap_color("#123456", cmap)
        assert token == "#123456"

    def test_snap_value_spacing(self):
        result = snap_value("padding", "13px", [4, 8, 12, 16], [0, 3, 6], [12, 14], {})
        assert result["was_corrected"]
        assert result["snapped"] == "12px"

    def test_snap_value_radius(self):
        result = snap_value("borderRadius", "5px", [4, 8], [0, 3, 6, 12], [12, 14], {})
        assert result["was_corrected"]
        assert "6px" in result["snapped"] or "radius" in result["token_category"]


# ── FigmaAdapter ───────────────────────────────────────────────────────────

class TestFigmaAdapter:
    @pytest.fixture
    def adapter(self) -> FigmaAdapter:
        return FigmaAdapter(
            spacing=[4, 8, 12, 16, 24, 32],
            radius=[0, 3, 6, 12, 9999],
            font_sizes=[12, 14, 16, 20, 24, 32, 40],
            color_map={"#2563EB": "brand.primary", "#FFFFFF": "white"},
        )

    def test_snap_single_node(self, adapter: FigmaAdapter):
        node = {"padding": "13px", "borderRadius": "5px", "fontSize": "15px"}
        result = adapter.snap(node)
        assert result["correction_count"] == 3
        assert result["snapped"]["padding"] == "12px"
        assert result["snapped"]["fontSize"] == "14px"

    def test_snap_with_children(self, adapter: FigmaAdapter):
        node = {
            "padding": "13px",
            "children": [
                {"padding": "7px", "borderRadius": "4px"},
            ],
        }
        result = adapter.snap(node)
        assert result["correction_count"] >= 2
        assert len(result["snapped"]["children"]) == 1

    def test_snap_list(self, adapter: FigmaAdapter):
        nodes = [{"padding": "13px"}, {"gap": "7px"}]
        result = adapter.snap(nodes)
        assert result["correction_count"] == 2
        assert len(result["snapped"]) == 2

    def test_snap_no_corrections(self, adapter: FigmaAdapter):
        node = {"padding": "12px", "borderRadius": "6px"}
        result = adapter.snap(node)
        assert result["correction_count"] == 0

    def test_fetch_missing_file(self, adapter: FigmaAdapter):
        with pytest.raises(FileNotFoundError):
            adapter.fetch("/nonexistent/figma.json")

    def test_score_auto_layout(self, adapter: FigmaAdapter):
        node = {
            "name": "Frame",
            "layoutMode": "VERTICAL",
            "children": [
                {"name": "Button", "layoutMode": "HORIZONTAL"},
                {"name": "Text", "type": "TEXT"},
            ],
        }
        score = adapter.score(node)
        assert score > 0.5

    def test_score_no_auto_layout(self, adapter: FigmaAdapter):
        node = {
            "name": "Frame",
            "children": [
                {"name": "Rectangle", "type": "RECTANGLE"},
                {"name": "Rectangle", "type": "RECTANGLE"},
            ],
        }
        score = adapter.score(node)
        assert score < 0.5

    def test_archaeologist_extracts_text(self, adapter: FigmaAdapter):
        node = {
            "children": [
                {"type": "TEXT", "characters": "Hello", "y": 0},
                {"type": "TEXT", "characters": "World", "y": 100},
            ],
        }
        result = adapter.archaeologist(node)
        assert "Hello" in result["texts"]
        assert "World" in result["texts"]

    def test_archaeologist_reading_order(self, adapter: FigmaAdapter):
        node = {
            "children": [
                {"type": "TEXT", "characters": "Second", "y": 100},
                {"type": "TEXT", "characters": "First", "y": 0},
            ],
        }
        result = adapter.archaeologist(node)
        assert result["reading_order"][0] == "First"
        assert result["reading_order"][1] == "Second"


# ── StitchAdapter ──────────────────────────────────────────────────────────

class TestStitchAdapter:
    @pytest.fixture
    def adapter(self) -> StitchAdapter:
        return StitchAdapter(
            spacing=[4, 8, 12, 16, 24, 32],
            radius=[0, 3, 6, 12, 9999],
            font_sizes=[12, 14, 16, 20, 24, 32, 40],
            color_map={"#2563EB": "brand.primary"},
        )

    def test_snap_html_inline_styles(self, adapter: StitchAdapter):
        html = '<div style="padding:13px;border-radius:5px">content</div>'
        raw = {"content": html, "ext": ".html"}
        result = adapter.snap(raw)
        assert result["correction_count"] >= 1
        assert "12px" in result["snapped"] or "3px" in result["snapped"]

    def test_snap_html_no_corrections(self, adapter: StitchAdapter):
        html = '<div style="padding:12px">content</div>'
        raw = {"content": html, "ext": ".html"}
        result = adapter.snap(raw)
        assert result["correction_count"] == 0

    def test_snap_css(self, adapter: StitchAdapter):
        css = ".card { padding: 13px; border-radius: 5px; }"
        raw = {"content": css, "ext": ".css"}
        result = adapter.snap(raw)
        assert result["correction_count"] >= 1

    def test_snap_designmd(self, adapter: StitchAdapter):
        md = (
            "| Token | Value |\n"
            "|-------|-------|\n"
            "| `color.primary` | `#2563EB` |\n"
            "| `spacing.md` | `12px` |\n"
        )
        raw = {"content": md, "ext": ".md"}
        result = adapter.snap(raw)
        assert result["token_count"] >= 2
        assert "spacing" in result["mapped"]

    def test_score_html_with_structure(self, adapter: StitchAdapter):
        raw = {"content": "<html><body><main>content</main></body></html>", "ext": ".html"}
        score = adapter.score(raw)
        assert score > 0.5

    def test_score_markdown_rich(self, adapter: StitchAdapter):
        md = "| Token | Value |\n|-------|-------|\n| `color.x` | `#000` |\n" * 5
        raw = {"content": md, "ext": ".md"}
        score = adapter.score(raw)
        assert score > 0.5

    def test_archaeologist_extracts_text(self, adapter: StitchAdapter):
        html = "<div>Hello <span>World</span></div>"
        raw = {"content": html, "ext": ".html"}
        result = adapter.archaeologist(raw)
        assert len(result["texts"]) >= 2

    def test_archaeologist_extracts_inputs(self, adapter: StitchAdapter):
        html = '<input placeholder="Email" />'
        raw = {"content": html, "ext": ".html"}
        result = adapter.archaeologist(raw)
        assert any(i["placeholder"] == "Email" for i in result["inputs"])


# ── RawJsonAdapter ─────────────────────────────────────────────────────────

class TestRawJsonAdapter:
    @pytest.fixture
    def adapter(self) -> RawJsonAdapter:
        return RawJsonAdapter(
            spacing=[4, 8, 12, 16, 24, 32],
            radius=[0, 3, 6, 12, 9999],
            font_sizes=[12, 14, 16, 20, 24, 32, 40],
        )

    def test_snap_simple(self, adapter: RawJsonAdapter):
        data = {"padding": 13, "cornerRadius": 5}
        result = adapter.snap(data)
        assert result["correction_count"] == 2
        assert result["snapped"]["padding"] == "12px"

    def test_snap_nested(self, adapter: RawJsonAdapter):
        data = {"container": {"padding": "13px"}, "items": [{"gap": 7}]}
        result = adapter.snap(data)
        assert result["correction_count"] == 2

    def test_snap_no_match(self, adapter: RawJsonAdapter):
        data = {"name": "button", "visible": True}
        result = adapter.snap(data)
        assert result["correction_count"] == 0

    def test_fetch_inline_json(self, adapter: RawJsonAdapter):
        data = adapter.fetch('{"padding": 13}')
        assert data["padding"] == 13

    def test_score_recognized_keys(self, adapter: RawJsonAdapter):
        data = {"padding": 8, "margin": 4, "gap": 12, "color": "#000"}
        score = adapter.score(data)
        assert score > 0

    def test_score_no_keys(self, adapter: RawJsonAdapter):
        score = adapter.score({"name": "foo"})
        assert score == 0.0
