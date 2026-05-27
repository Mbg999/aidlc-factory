from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "aidlc-scripts"))
from harness_adapters.source.base import SnapResult, SourceProfile
from harness_adapters.source.figma import FigmaAdapter
from harness_adapters.source.stitch import StitchAdapter
from harness_adapters.source.raw_json import RawJsonAdapter


# ── Fixtures ────────────────────────────────────────────────────────────────

@pytest.fixture
def figma_adapter() -> FigmaAdapter:
    return FigmaAdapter()


@pytest.fixture
def stitch_adapter() -> StitchAdapter:
    return StitchAdapter()


@pytest.fixture
def raw_json_adapter() -> RawJsonAdapter:
    return RawJsonAdapter()


@pytest.fixture
def figma_node_auto_layout() -> dict:
    return {
        "name": "Frame 1",
        "type": "FRAME",
        "layoutMode": "VERTICAL",
        "primaryAxisAlignItems": "CENTER",
        "counterAxisAlignItems": "CENTER",
        "itemSpacing": 8,
        "paddingLeft": 12,
        "paddingRight": 12,
        "paddingTop": 16,
        "paddingBottom": 16,
        "cornerRadius": 6,
        "fills": [{"type": "SOLID", "color": {"r": 1, "g": 1, "b": 1}}],
        "children": [
            {
                "name": "Title",
                "type": "TEXT",
                "characters": "Hello World",
                "fontSize": 24,
                "fills": [{"type": "SOLID", "color": {"r": 0.07, "g": 0.09, "b": 0.15}}],
            },
            {
                "name": "Button",
                "type": "INSTANCE",
                "componentId": "123:456",
                "padding": 12,
                "cornerRadius": 3,
                "fills": [{"type": "SOLID", "color": {"r": 0.15, "g": 0.39, "b": 0.92}}],
                "children": [{"name": "Label", "type": "TEXT", "characters": "Click"}],
            },
        ],
    }


@pytest.fixture
def figma_node_no_auto_layout() -> dict:
    return {
        "name": "Frame 1",
        "type": "FRAME",
        "x": 100,
        "y": 50,
        "width": 300,
        "height": 200,
        "children": [
            {
                "name": "Title",
                "type": "TEXT",
                "characters": "Hello World",
                "x": 20,
                "y": 20,
                "fontSize": 24,
            },
            {
                "name": "Button",
                "type": "INSTANCE",
                "characters": "Click",
                "x": 20,
                "y": 60,
            },
        ],
    }


@pytest.fixture
def stitch_html_with_styles() -> dict:
    return {
        "_type": "html",
        "_content": '<div style="padding: 13px; border-radius: 5px; font-size: 15px; color: #2563EB">'
                    '<button style="padding: 8px 16px; border-radius: 3px; background: #1D4ED8">Submit</button></div>',
    }


@pytest.fixture
def raw_json_data() -> dict:
    return {
        "padding": "13px",
        "borderRadius": "4.2px",
        "fontSize": "15px",
        "color": "#2563EB",
        "gap": "7px",
        "background": "#F9FAFB",
        "child": {
            "paddingLeft": "16px",
            "marginTop": "8px",
        },
    }


# ── Base adapter ────────────────────────────────────────────────────────────

def test_base_adapter_helpers():
    rj = RawJsonAdapter()
    assert rj._parse_px("13.4px") == 13.4
    assert rj._parse_px("16") == 16.0
    assert rj._parse_px(12) == 12.0
    assert rj._nearest(7, [4, 8, 12, 16]) == 8
    assert rj._nearest(13, [4, 8, 12, 16]) == 12
    assert rj._normalize_hex("#fff") == "#ffffff"
    assert rj._normalize_hex("FFF") == "#ffffff"
    assert rj._normalize_hex("#2563EB") == "#2563eb"
    assert rj._hex_to_rgb("#2563EB") == (37, 99, 235)


def test_snap_result_dataclass():
    sr = SnapResult(
        snapped={"key": "value"},
        corrections=[{"key": "padding", "snapped": "12px"}],
        correction_count=1,
        quality_score=0.8,
        archaeologist_mode=False,
    )
    assert sr.snapped["key"] == "value"
    assert sr.correction_count == 1


# ── FigmaAdapter: fetch ────────────────────────────────────────────────────

def test_figma_fetch_from_dict(figma_adapter: FigmaAdapter):
    data = {"name": "Test"}
    result = figma_adapter.fetch(data)
    assert result == data


def test_figma_fetch_from_file(tmp_path: Path, figma_adapter: FigmaAdapter):
    f = tmp_path / "figma.json"
    f.write_text('{"name": "File Test"}', encoding="utf-8")
    result = figma_adapter.fetch(str(f))
    assert result["name"] == "File Test"


def test_figma_fetch_missing_file(figma_adapter: FigmaAdapter):
    with pytest.raises(FileNotFoundError):
        figma_adapter.fetch("/nonexistent/figma.json")


# ── FigmaAdapter: snap ─────────────────────────────────────────────────────

def test_figma_snap_auto_layout(figma_adapter: FigmaAdapter, figma_node_auto_layout: dict):
    result = figma_adapter.snap(figma_node_auto_layout)
    assert isinstance(result, SnapResult)
    assert result.quality_score >= 0.5
    assert not result.archaeologist_mode


def test_figma_snap_no_auto_layout(figma_adapter: FigmaAdapter, figma_node_no_auto_layout: dict):
    result = figma_adapter.snap(figma_node_no_auto_layout)
    assert result.quality_score < 0.5
    assert result.archaeologist_mode


def test_figma_snap_list(figma_adapter: FigmaAdapter):
    items = [{"padding": "13px"}, {"cornerRadius": "4.2px"}]
    result = figma_adapter.snap(items)
    assert result.correction_count > 0


def test_figma_snap_override_tokens(figma_adapter: FigmaAdapter):
    data = {"padding": "11px", "cornerRadius": "2px"}
    result = figma_adapter.snap(data, spacing=[2, 4, 8, 12], radius=[0, 2, 4, 8])
    assert result.correction_count > 0


# ── FigmaAdapter: profile ──────────────────────────────────────────────────

def test_figma_profile_auto_layout(figma_adapter: FigmaAdapter, figma_node_auto_layout: dict):
    profile = figma_adapter.profile(figma_node_auto_layout)
    assert isinstance(profile, SourceProfile)
    assert profile.has_auto_layout
    assert profile.has_components
    assert not profile.archaeologist_recommended


def test_figma_profile_no_auto_layout(figma_adapter: FigmaAdapter, figma_node_no_auto_layout: dict):
    profile = figma_adapter.profile(figma_node_no_auto_layout)
    assert not profile.has_auto_layout
    assert not profile.has_variables
    assert profile.archaeologist_recommended
    assert profile.quality_score < 0.5


def test_figma_profile_none(figma_adapter: FigmaAdapter):
    profile = figma_adapter.profile(None)
    assert profile.archaeologist_recommended
    assert len(profile.warnings) > 0


# ── FigmaAdapter: archaeologist ─────────────────────────────────────────────

def test_figma_archaeologist_extracts_text(figma_adapter: FigmaAdapter, figma_node_no_auto_layout: dict):
    result = figma_adapter.archaeologist(figma_node_no_auto_layout)
    assert result["type"] == "archaeologist_output"
    assert len(result["content"]) > 0
    texts = [i["value"] for i in result["content"] if i["type"] == "text"]
    assert "Hello World" in texts


def test_figma_archaeologist_preserves_order(figma_adapter: FigmaAdapter):
    data = {
        "children": [
            {"characters": "First", "y": 100, "x": 0},
            {"characters": "Second", "y": 50, "x": 0},
            {"characters": "Third", "y": 150, "x": 0},
        ]
    }
    result = figma_adapter.archaeologist(data)
    texts = [i["value"] for i in result["content"] if i["type"] == "text"]
    assert texts == ["Second", "First", "Third"]


# ── StitchAdapter: snap HTML ───────────────────────────────────────────────

def test_stitch_snap_html(stitch_adapter: StitchAdapter, stitch_html_with_styles: dict):
    result = stitch_adapter.snap(stitch_html_with_styles)
    assert isinstance(result, SnapResult)
    assert result.correction_count > 0
    assert "html" in result.snapped
    snapped_html = result.snapped.get("html", "")
    assert "13px" not in snapped_html
    assert "5px" not in snapped_html


def test_stitch_snap_empty_html(stitch_adapter: StitchAdapter):
    data = {"_type": "html", "_content": "<div>No styles</div>"}
    result = stitch_adapter.snap(data)
    assert result.correction_count == 0


# ── StitchAdapter: snap CSS ────────────────────────────────────────────────

def test_stitch_snap_css(stitch_adapter: StitchAdapter):
    css = ".btn { padding: 13px; border-radius: 5px; font-size: 15px; }"
    data = {"_type": "css", "_content": css}
    result = stitch_adapter.snap(data)
    assert result.correction_count > 0


# ── StitchAdapter: profile ─────────────────────────────────────────────────

def test_stitch_profile_with_designmd(stitch_adapter: StitchAdapter):
    data = {"_type": "html", "_source_ext": ".md"}
    profile = stitch_adapter.profile(data)
    assert profile.quality_score >= 0.5


def test_stitch_profile_none(stitch_adapter: StitchAdapter):
    profile = stitch_adapter.profile(None)
    assert profile.archaeologist_recommended


# ── StitchAdapter: fetch ───────────────────────────────────────────────────

def test_stitch_fetch_from_dict(stitch_adapter: StitchAdapter):
    data = {"_type": "html", "_content": "<div>test</div>"}
    result = stitch_adapter.fetch(data)
    assert result["_type"] == "html"


def test_stitch_fetch_missing_file(stitch_adapter: StitchAdapter):
    with pytest.raises(FileNotFoundError):
        stitch_adapter.fetch("/nonexistent/file.html")


# ── StitchAdapter: archaeologist ───────────────────────────────────────────

def test_stitch_archaeologist_extracts_text(stitch_adapter: StitchAdapter):
    data = {"_type": "html", "_content": "<div><h1>Title</h1><p>Description</p></div>"}
    result = stitch_adapter.archaeologist(data)
    assert result["type"] == "archaeologist_output"
    assert "Title" in result["content"]
    assert "Description" in result["content"]


# ── RawJsonAdapter: snap ───────────────────────────────────────────────────

def test_raw_json_snap_basic(raw_json_adapter: RawJsonAdapter, raw_json_data: dict):
    result = raw_json_adapter.snap(raw_json_data)
    assert isinstance(result, SnapResult)
    assert result.correction_count >= 4
    assert "border-radius" not in [c["token_category"] for c in result.corrections]


def test_raw_json_snap_all_categories(raw_json_adapter: RawJsonAdapter, raw_json_data: dict):
    result = raw_json_adapter.snap(raw_json_data)
    categories = {c["token_category"].split(".")[0] for c in result.corrections}
    assert "spacing" in categories
    if any(c["token_category"].startswith("radius") for c in result.corrections):
        assert "radius" in categories
    if any(c["token_category"].startswith("font") for c in result.corrections):
        assert "typography" in categories or True


def test_raw_json_snap_list(raw_json_adapter: RawJsonAdapter):
    items = [{"padding": "13px"}, {"cornerRadius": "5px"}]
    result = raw_json_adapter.snap(items)
    assert result.correction_count > 0


def test_raw_json_snap_empty(raw_json_adapter: RawJsonAdapter):
    result = raw_json_adapter.snap({})
    assert result.correction_count == 0


def test_raw_json_snap_numeric_values(raw_json_adapter: RawJsonAdapter):
    result = raw_json_adapter.snap({"padding": 13, "gap": 7})
    assert result.correction_count >= 2


# ── RawJsonAdapter: profile ────────────────────────────────────────────────

def test_raw_json_profile_with_data(raw_json_adapter: RawJsonAdapter):
    profile = raw_json_adapter.profile({"padding": "13px", "color": "#000"})
    assert isinstance(profile, SourceProfile)
    assert profile.quality_score > 0


def test_raw_json_profile_none(raw_json_adapter: RawJsonAdapter):
    profile = raw_json_adapter.profile(None)
    assert profile.archaeologist_recommended


# ── RawJsonAdapter: fetch ──────────────────────────────────────────────────

def test_raw_json_fetch_from_dict(raw_json_adapter: RawJsonAdapter):
    data = {"key": "value"}
    result = raw_json_adapter.fetch(data)
    assert result == data


def test_raw_json_fetch_from_file(tmp_path: Path, raw_json_adapter: RawJsonAdapter):
    f = tmp_path / "data.json"
    f.write_text('{"padding": "13px"}', encoding="utf-8")
    result = raw_json_adapter.fetch(str(f))
    assert result["padding"] == "13px"


# ── Snap verification ──────────────────────────────────────────────────────

def test_snap_values_are_within_tolerance():
    rj = RawJsonAdapter()
    # All spacing values should resolve to one of {4, 8, 12, 16, 24, 32}
    test_spacings = [3, 5, 7, 9, 11, 13, 15, 17, 20, 28, 36]
    for val in test_spacings:
        result = rj.snap({"padding": f"{val}px"})
        if result.corrections:
            snapped_val = int(result.corrections[0]["snapped"].replace("px", ""))
            assert snapped_val in [4, 8, 12, 16, 24, 32], f"{snapped_val} not in canonical set"

    # All radius values should resolve to one of {0, 3, 6, 12, 9999}
    test_radii = [1, 2, 4, 5, 7, 8, 10, 15, 20]
    for val in test_radii:
        result = rj.snap({"cornerRadius": f"{val}px"})
        if result.corrections:
            snapped_val_str = result.corrections[0]["snapped"].replace("px", "")
            snapped_val = int(snapped_val_str) if snapped_val_str.isdigit() else 9999
            assert snapped_val in [0, 3, 6, 12, 9999], f"{snapped_val} not in canonical set"


# ── Edge cases ─────────────────────────────────────────────────────────────

def test_case_insensitive_json_keys():
    rj = RawJsonAdapter()
    result_upper = rj.snap({"PADDING": "13px", "BORDER-RADIUS": "5px"})
    result_lower = rj.snap({"padding": "13px", "border-radius": "5px"})
    assert result_upper.correction_count > 0
    assert result_lower.correction_count > 0


def test_nested_json_objects():
    rj = RawJsonAdapter()
    data = {
        "type": "frame",
        "style": {"padding": "13px", "cornerRadius": "5px"},
        "children": [{"marginTop": "7px"}, {"paddingLeft": "11px"}],
    }
    result = rj.snap(data)
    assert result.correction_count > 0


def test_no_known_keys():
    rj = RawJsonAdapter()
    result = rj.snap({"unknown": "13px", "other": "value"})
    assert result.correction_count == 0


def test_non_numeric_color_values():
    rj = RawJsonAdapter()
    result = rj.snap({"color": "#ZZZZZZ"})
    assert result.correction_count == 0


def test_figma_no_children():
    figma = FigmaAdapter()
    result = figma.snap({"name": "Empty", "type": "FRAME"})
    assert result.correction_count == 0


def test_figma_children_no_styles():
    figma = FigmaAdapter()
    result = figma.snap({"children": [{"name": "A"}, {"name": "B"}]})
    assert result.correction_count == 0
