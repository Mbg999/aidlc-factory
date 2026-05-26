from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "aidlc-scripts"))
from factory_design_system_harness import (
    ComplianceReport,
    DesignSystemHarness,
    QualityScore,
    SemanticIntent,
)


# ── Fixtures ────────────────────────────────────────────────────────────────

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
def minimal_ds(tmp_path: Path) -> Path:
    """Minimal design system — only spacing + color with few values."""
    root = tmp_path / "minimal-ds"
    tokens = root / "tokens"
    tokens.mkdir(parents=True)

    (tokens / "spacing.md").write_text(
        "# Spacing\n\n"
        "| Token | Pixels |\n"
        "|-------|--------|\n"
        "| `spacing.sm` | 8 |\n"
        "| `spacing.md` | 12 |\n"
    )
    (tokens / "color.md").write_text(
        "# Colors\n\n"
        "| Token | Hex |\n"
        "|-------|-----|\n"
        "| `brand.primary` | #3B82F6 |\n"
        "| `neutral.bg` | #FFFFFF |\n"
    )
    return root


@pytest.fixture
def harness(ds_root: Path) -> DesignSystemHarness:
    return DesignSystemHarness(ds_root)


# ── Token loading ───────────────────────────────────────────────────────────

def test_load_all_tokens(harness: DesignSystemHarness):
    harness.load()
    assert harness.tokens.spacing["md"] == 12
    assert harness.tokens.radius["sm"] == 3
    assert harness.tokens.typography["body"]["size"] == 14
    assert harness.tokens.color["brand.primary"] == "#2563EB"
    assert harness.tokens.elevation["lg"]["zIndex"] == 100


def test_load_missing_tokens_dir(tmp_path: Path):
    h = DesignSystemHarness(tmp_path / "nonexistent")
    h.load()
    assert len(h.tokens.spacing) == 0
    assert any(w.severity == "critical" for w in h.warnings)


def test_load_partial(minimal_ds: Path):
    h = DesignSystemHarness(minimal_ds)
    h.load()
    assert h.tokens.spacing["sm"] == 8
    assert len(h.tokens.radius) == 0
    assert len(h.tokens.typography) == 0
    assert h.tokens.color["brand.primary"] == "#3B82F6"
    assert len(h.tokens.elevation) == 0


# ── Validation ──────────────────────────────────────────────────────────────

def test_validate_full_ds(harness: DesignSystemHarness):
    results = harness.validate()
    criticals = [r for r in results if r.severity == "critical"]
    assert len(criticals) == 0


def test_validate_minimal(minimal_ds: Path):
    h = DesignSystemHarness(minimal_ds)
    results = h.validate()
    criticals = [r for r in results if r.severity == "critical"]
    assert len(criticals) == 0
    warnings = [r for r in results if r.severity == "warning"]
    assert any("Only 2 spacing values" in r.message for r in warnings)


def test_validate_missing_required(tmp_path: Path):
    root = tmp_path / "bad-ds"
    tokens = root / "tokens"
    tokens.mkdir(parents=True)
    # Only spacing — missing color (required)
    (tokens / "spacing.md").write_text(
        "# Spacing\n\n| Token | Pixels |\n|-------|--------|\n| `spacing.md` | 12 |\n"
    )
    h = DesignSystemHarness(root)
    results = h.validate()
    criticals = [r for r in results if r.severity == "critical"]
    assert any("color" in r.category for r in criticals)


# ── Quality score ───────────────────────────────────────────────────────────

def test_quality_score_full(harness: DesignSystemHarness):
    score = harness.quality_score()
    assert score.overall >= 0.8
    assert score.categories_present == 5


def test_quality_score_minimal(minimal_ds: Path):
    h = DesignSystemHarness(minimal_ds)
    score = h.quality_score()
    assert score.overall < 0.8
    assert score.categories_present == 2


def test_quality_score_empty(tmp_path: Path):
    h = DesignSystemHarness(tmp_path / "empty")
    score = h.quality_score()
    assert score.overall == 0.0


# ── Composition ─────────────────────────────────────────────────────────────

def test_compose_intent_simple(harness: DesignSystemHarness):
    intent = harness.compose_intent(["button", "input", "text"])
    assert len(intent.components) == 3
    assert intent.components[0]["type"] == "button"
    assert intent.components[0]["label"] == "Button"
    assert intent.components[0]["variant"] == "primary"
    assert intent.components[2]["type"] == "text"
    assert intent.tokens["spacing"]["md"] == 12
    assert intent.meta["source"] == "manual"


def test_compose_intent_with_meta(harness: DesignSystemHarness):
    intent = harness.compose_intent(
        ["button"],
        source="figma",
        source_quality=0.3,
        framework_hint="flutter",
        layout_hint=[{"type": "stack", "gap": "md", "children": []}],
    )
    assert intent.meta["source"] == "figma"
    assert intent.meta["source_quality"] == 0.3
    assert intent.meta["framework_hint"] == "flutter"
    assert intent.meta["archaeologist_mode"] is False
    assert len(intent.layout) == 1


def test_compose_intent_unknown_type(harness: DesignSystemHarness):
    intent = harness.compose_intent(["foobar"])
    assert intent.components[0]["type"] == "text"


# ── Drift detection ─────────────────────────────────────────────────────────

def test_drift_no_diff(harness: DesignSystemHarness):
    intent = harness.compose_intent(["button", "input"])
    report = harness.check_drift(intent, intent)
    assert report.passed
    assert len(report.deviations) == 0


def test_drift_token_changed(harness: DesignSystemHarness):
    baseline = harness.compose_intent(["button"])
    current = harness.compose_intent(["button"])
    current.tokens["spacing"]["md"] = 999
    report = harness.check_drift(baseline, current)
    assert not report.passed
    assert any(d["type"] == "value_changed" for d in report.deviations)


def test_drift_component_removed(harness: DesignSystemHarness):
    baseline = harness.compose_intent(["button", "input", "text"])
    current = harness.compose_intent(["button"])
    report = harness.check_drift(baseline, current)
    assert any("removed" in w for w in report.warnings)


def test_drift_component_added(harness: DesignSystemHarness):
    baseline = harness.compose_intent(["button"])
    current = harness.compose_intent(["button", "input"])
    report = harness.check_drift(baseline, current)
    assert any("added" in w for w in report.warnings)


# ── SemanticIntent serialization ───────────────────────────────────────────

def test_semantic_intent_roundtrip(harness: DesignSystemHarness):
    original = harness.compose_intent(["button", "text"], source="figma")
    d = original.to_dict()
    restored = SemanticIntent.from_dict(d)
    assert restored.components == original.components
    assert restored.tokens == original.tokens
    assert restored.meta == original.meta


def test_semantic_intent_from_dict():
    data = {
        "tokens": {"spacing": {"xs": 4}, "color": {"brand.primary": "#000"}},
        "components": [{"type": "button", "label": "Save", "variant": "primary", "size": "md"}],
    }
    intent = SemanticIntent.from_dict(data)
    assert intent.components[0]["label"] == "Save"
    assert intent.tokens["spacing"]["xs"] == 4


# ── Edge cases ──────────────────────────────────────────────────────────────

def test_empty_design_system(tmp_path: Path):
    root = tmp_path / "empty-ds"
    root.mkdir()
    h = DesignSystemHarness(root)
    h.load()
    assert len(h.tokens.spacing) == 0
    score = h.quality_score()
    assert score.overall == 0.0
    intent = h.compose_intent(["button"])
    assert len(intent.components) == 1
    # No tokens to include
    assert "spacing" not in intent.tokens


def test_compose_intent_empty_list(harness: DesignSystemHarness):
    intent = harness.compose_intent([])
    assert len(intent.components) == 0
