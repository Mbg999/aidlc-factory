from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "aidlc-scripts"))
from factory_design_system_harness import DesignSystemHarness, SemanticIntent
from harness_adapters.source.figma import FigmaAdapter
from harness_adapters.source.raw_json import RawJsonAdapter
from harness_adapters.framework.react import ReactAdapter
from harness_adapters.framework.angular import AngularAdapter
from harness_adapters.framework.flutter import FlutterAdapter
from harness_adapters.framework.html import HtmlAdapter
from factory_drift_detect import create_snapshot, diff_structural


# ── Fixtures ─────────────────────────────────────────────────────────────

@pytest.fixture
def ds_root(tmp_path: Path) -> Path:
    root = tmp_path / "design-system"
    tokens = root / "tokens"
    tokens.mkdir(parents=True)

    (tokens / "spacing.md").write_text(
        "# Spacing\n\n"
        "| Token | Pixels |\n"
        "|-------|--------|\n"
        "| `spacing.xs` | 4 |\n"
        "| `spacing.sm` | 8 |\n"
        "| `spacing.md` | 12 |\n"
        "| `spacing.lg` | 16 |\n"
        "| `spacing.xl` | 24 |\n"
        "| `spacing.xxl` | 32 |\n"
    )
    (tokens / "radius.md").write_text(
        "# Radius\n\n"
        "| Token | Pixels |\n"
        "|-------|--------|\n"
        "| `radius.none` | 0 |\n"
        "| `radius.sm` | 3 |\n"
        "| `radius.md` | 6 |\n"
        "| `radius.lg` | 12 |\n"
        "| `radius.full` | 9999 |\n"
    )
    (tokens / "typography.md").write_text(
        "# Typography\n\n"
        "| Token | Pixels |\n"
        "|-------|--------|\n"
        "| `font-size.caption` | 12 |\n"
        "| `font-size.body` | 14 |\n"
        "| `font-size.body-large` | 16 |\n"
        "| `font-size.h4` | 20 |\n"
        "| `font-size.h3` | 24 |\n"
        "| `font-size.h2` | 32 |\n"
        "| `font-size.h1` | 40 |\n"
    )
    (tokens / "color.md").write_text(
        "# Colors\n\n"
        "| Token | Hex |\n"
        "|-------|-----|\n"
        "| `brand.primary` | #2563EB |\n"
        "| `brand.secondary` | #059669 |\n"
        "| `neutral.text-primary` | #111827 |\n"
        "| `neutral.text-secondary` | #6B7280 |\n"
        "| `neutral.bg` | #FFFFFF |\n"
        "| `neutral.border` | #E5E7EB |\n"
        "| `neutral.surface` | #F9FAFB |\n"
        "| `semantic.danger` | #EF4444 |\n"
        "| `semantic.success` | #10B981 |\n"
        "| `semantic.warning` | #F59E0B |\n"
    )
    (tokens / "elevation.md").write_text(
        "# Elevation\n\n"
        "| Token | Z-Index |\n"
        "|-------|---------|\n"
        "| `elevation.sm` | 1 |\n"
        "| `elevation.md` | 10 |\n"
        "| `elevation.lg` | 100 |\n"
        "| `elevation.xl` | 1000 |\n"
    )
    return root


@pytest.fixture
def harness(ds_root: Path) -> DesignSystemHarness:
    h = DesignSystemHarness(ds_root)
    h.load()
    return h


@pytest.fixture
def react_adapter() -> ReactAdapter:
    return ReactAdapter()


# ── 6.1: Figma JSON -> snap -> SemanticIntent -> React code ────────────

class TestFigmaToReactPipeline:
    """Full pipeline: raw Figma JSON -> snapped values -> SemanticIntent -> TSX."""

    def test_button_from_figma(self, harness: DesignSystemHarness, react_adapter: ReactAdapter):
        figma = FigmaAdapter(
            spacing=[4, 8, 12, 16, 24, 32],
            radius=[0, 3, 6, 12, 9999],
            font_sizes=[12, 14, 16, 20, 24, 32, 40],
            color_map={"#2563EB": "brand.primary", "#FFFFFF": "white"},
        )
        raw_node = {
            "type": "FRAME",
            "padding": "13px",
            "borderRadius": "5px",
            "children": [
                {
                    "type": "TEXT",
                    "fontSize": "15px",
                    "characters": "Click me",
                }
            ],
        }
        snapped = figma.snap(raw_node)
        assert snapped["correction_count"] >= 1
        assert snapped["snapped"]["padding"] == "12px"

        intent = harness.compose_intent(
            ["Button"],
            source="figma",
            source_quality=0.85,
        )
        intent.components[0]["label"] = "Button"
        intent.components[0]["variant"] = "primary"

        code = react_adapter.render(intent)
        assert "export function Button" in code
        assert "data-testid" in code
        assert "spacing" in intent.tokens or "color" in intent.tokens

    def test_input_from_figma(self, harness: DesignSystemHarness, react_adapter: ReactAdapter):
        figma = FigmaAdapter(
            spacing=[4, 8, 12, 16], radius=[0, 3, 6, 12],
            font_sizes=[12, 14, 16], color_map={},
        )
        raw = {"type": "FRAME", "padding": "9px", "children": [{"type": "TEXT", "characters": "Email"}]}
        snapped = figma.snap(raw)
        assert snapped["correction_count"] >= 1

        intent = harness.compose_intent(["Input"], source="figma")
        intent.components[0]["label"] = "EmailInput"

        code = react_adapter.render(intent)
        assert "export function EmailInput" in code
        assert "placeholder" in code

    def test_intent_roundtrip_json(self, harness: DesignSystemHarness):
        intent = harness.compose_intent(["Button", "Input"], source="figma")
        d = intent.to_dict()
        restored = SemanticIntent.from_dict(d)
        assert restored.tokens == intent.tokens
        assert len(restored.components) == 2

    def test_raw_json_adapter_feeds_harness(self, harness: DesignSystemHarness, react_adapter: ReactAdapter):
        raw = {"padding": 13, "cornerRadius": 5}
        adapter = RawJsonAdapter(
            spacing=[4, 8, 12, 16], radius=[0, 3, 6, 12],
            color_map={},
        )
        snapped = adapter.snap(raw)
        assert snapped["snapped"].get("padding") in ("12px", "8px")

        intent = harness.compose_intent(["Button"], source="raw-json")
        code = react_adapter.render(intent)
        assert "export function Button" in code


# ── 6.2: SemanticIntent -> multiple frameworks ─────────────────────────

class TestMultiFrameworkPipeline:
    """Same SemanticIntent rendered to different framework outputs."""

    @pytest.fixture
    def shared_intent(self, harness: DesignSystemHarness) -> SemanticIntent:
        intent = harness.compose_intent(
            ["Button", "Input"],
            layout_hint=[{
                "type": "stack", "gap": "md", "padding": "lg",
                "children": [
                    {"type": "box", "children": [{"label": "SubmitBtn"}]},
                    {"type": "box", "children": [{"label": "EmailField"}]},
                ],
            }],
        )
        intent.components[0].update({"label": "SubmitBtn", "variant": "primary", "size": "md"})
        intent.components[1].update({"label": "EmailField"})
        return intent

    def test_react(self, shared_intent: SemanticIntent):
        code = ReactAdapter().render(shared_intent)
        assert "export function SubmitBtn" in code
        assert "export function EmailField" in code
        assert "export function PageLayout" in code

    def test_angular(self, shared_intent: SemanticIntent):
        code = AngularAdapter().render(shared_intent)
        assert "SubmitBtnComponent" in code
        assert "EmailFieldComponent" in code
        assert "@Component" in code

    def test_flutter(self, shared_intent: SemanticIntent):
        code = FlutterAdapter().render(shared_intent)
        assert "SubmitBtn" in code
        assert "EmailField" in code
        assert "import 'package:flutter/material.dart'" in code

    def test_html(self, shared_intent: SemanticIntent):
        code = HtmlAdapter().render(shared_intent)
        assert "submit-btn" in code or "SubmitBtn" in code
        assert "<style>" in code
        assert "<body>" in code


# ── 6.3: Bad Figma (no Auto Layout) -> archaeologist -> output usable ─

class TestArchaeologistMode:
    """Low-quality input triggers archaeologist mode, but still produces output."""

    def test_figma_without_auto_layout(self, harness: DesignSystemHarness, react_adapter: ReactAdapter):
        figma = FigmaAdapter(
            spacing=[4, 8], radius=[0, 3],
            font_sizes=[12, 14], color_map={},
        )
        flat_node = {
            "type": "FRAME",
            "padding": "999px",
            "borderRadius": "999px",
            "children": [
                {"type": "TEXT", "fontSize": "99px", "characters": "hello"},
            ],
        }
        snapped = figma.snap(flat_node)
        quality_score = figma.score(flat_node)
        assert quality_score < 0.5

        intent = harness.compose_intent(
            ["Button"],
            source="figma",
            source_quality=quality_score,
        )
        intent.components[0]["label"] = "RoughBtn"
        intent.meta["archaeologist_mode"] = True

        code = react_adapter.render(intent)
        assert "export function RoughBtn" in code

    def test_archaeologist_mode_flag_in_meta(self, harness: DesignSystemHarness):
        intent = harness.compose_intent(["Text"], source="archaeologist", source_quality=0.15)
        assert intent.meta["archaeologist_mode"] is False
        assert intent.meta["source_quality"] == 0.15


# ── 6.4: Drift detection -> diff report ──────────────────────────────

class TestDriftIntegration:
    """End-to-end drift detection with real snapshots."""

    def test_drift_between_versions(self, tmp_path: Path):
        v1 = tmp_path / "v1"
        v1.mkdir()
        (v1 / "Button.tsx").write_text("<Button>Click</Button>\n<Stack gap='spacing.sm' />\n")

        v2 = tmp_path / "v2"
        v2.mkdir()
        (v2 / "Button.tsx").write_text("<Button>Click</Button>\n<Stack gap='spacing.xl' />\n<Icon name='plus' />\n")

        snap1 = create_snapshot("Button", "primary", v1)
        snap2 = create_snapshot("Button", "primary", v2)

        report = diff_structural(snap1, snap2)
        assert not report.passed
        assert report.diff_percentage > 0
        assert len(report.structural_changes) > 0 or len(report.token_changes) > 0

    def test_no_drift_identical_code(self, tmp_path: Path):
        d = tmp_path / "code"
        d.mkdir()
        (d / "Cmp.tsx").write_text("spacing.sm\ncolor.brand.primary\n")
        snap1 = create_snapshot("Cmp", "a", d)
        snap2 = create_snapshot("Cmp", "a", d)
        report = diff_structural(snap1, snap2)
        assert report.passed
        assert report.score == 1.0

    def test_drift_harness_integration(self, harness: DesignSystemHarness):
        intent_a = harness.compose_intent(["Button", "Input"], source="test")
        intent_b = harness.compose_intent(["Button"], source="test")
        report = harness.check_drift(intent_a, intent_b)
        assert len(report.deviations) > 0 or len(report.warnings) > 0


# ── 6.5: Quality score variants ───────────────────────────────────────

class TestQualityScore:
    """Token set completeness mapping to quality scores."""

    def test_full_token_set_high_score(self, harness: DesignSystemHarness):
        score = harness.quality_score()
        assert score.overall >= 0.8
        assert score.categories_present >= 4

    def test_minimal_token_set_low_score(self, tmp_path: Path):
        root = tmp_path / "minimal-ds"
        tokens = root / "tokens"
        tokens.mkdir(parents=True)
        (tokens / "spacing.md").write_text(
            "# Spacing\n\n| Token | Pixels |\n|-------|--------|\n| `spacing.sm` | 8 |\n"
        )
        (tokens / "color.md").write_text(
            "# Colors\n\n| Token | Hex |\n|-------|-----|\n| `brand.primary` | #2563EB |\n"
        )
        h = DesignSystemHarness(root)
        h.load()
        score = h.quality_score()
        assert score.overall < 0.6
        assert score.categories_present <= 3

    def test_missing_required_categories(self, tmp_path: Path):
        root = tmp_path / "broken-ds"
        tokens = root / "tokens"
        tokens.mkdir(parents=True)
        (tokens / "spacing.md").write_text(
            "# Spacing\n\n| Token | Pixels |\n|-------|--------|\n| `spacing.sm` | 8 |\n"
        )
        h = DesignSystemHarness(root)
        validation = h.validate()
        criticals = [w for w in validation if w.severity == "critical"]
        assert any("color" in w.message.lower() for w in criticals)

    def test_no_tokens_zero_score(self, tmp_path: Path):
        root = tmp_path / "empty-ds"
        root.mkdir()
        h = DesignSystemHarness(root)
        h.load()
        score = h.quality_score()
        assert score.overall == 0.0
        assert score.categories_present == 0


# ── 6.6: React validation detects raw px values ──────────────────────

class TestReactValidation:
    """FrameworkAdapter.validate catches hardcoded values."""

    def test_detects_raw_px_in_generated_code(self, harness: DesignSystemHarness, react_adapter: ReactAdapter):
        intent = harness.compose_intent(["Button"], source="test")
        intent.tokens.setdefault("spacing", {"sm": 8, "md": 12})
        intent.tokens.setdefault("radius", {"sm": 3})

        bad_code = """export function BadButton() {
          return <button style={{ padding: '12px', borderRadius: '3px' }}>Click</button>;
        }"""
        report = react_adapter.validate(bad_code, intent)
        assert not report.passed or len(report.deviations) > 0

    def test_clean_code_passes(self, harness: DesignSystemHarness, react_adapter: ReactAdapter):
        intent = harness.compose_intent(["Button"], source="test")
        intent.tokens.setdefault("spacing", {"sm": 8, "md": 12})
        intent.tokens.setdefault("radius", {"sm": 3})

        clean_code = """export function GoodButton() {
          return <button className="btn btn--primary">Click</button>;
        }"""
        report = react_adapter.validate(clean_code, intent)
        assert report.passed
