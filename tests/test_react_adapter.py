from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "aidlc-scripts"))
from harness_engine import DesignSystemHarness, SemanticIntent
from harness_adapters.framework.react import ReactAdapter


@pytest.fixture
def harness() -> DesignSystemHarness:
    root = Path(__file__).resolve().parent.parent / "design-system"
    h = DesignSystemHarness(root)
    h.load()
    return h


@pytest.fixture
def adapter(harness: DesignSystemHarness) -> ReactAdapter:
    return ReactAdapter()


# ── Render component types ─────────────────────────────────────────────────

def test_render_button_component(adapter: ReactAdapter, harness: DesignSystemHarness):
    intent = harness.compose_intent(["button"])
    code = adapter.render(intent)
    assert "export function Button(" in code
    assert "interface ButtonProps" in code
    assert "data-testid" in code
    assert "disabled" in code


def test_render_input_component(adapter: ReactAdapter, harness: DesignSystemHarness):
    intent = harness.compose_intent(["input"])
    code = adapter.render(intent)
    assert "export function Input(" in code
    assert "interface InputProps" in code
    assert "placeholder" in code
    assert "error" in code


def test_render_text_component(adapter: ReactAdapter, harness: DesignSystemHarness):
    intent = harness.compose_intent(["text"])
    code = adapter.render(intent)
    assert "export function Text(" in code
    assert "as?: 'p' | 'h1' | 'h2' | 'h3' | 'h4' | 'span'" in code


def test_render_link_component(adapter: ReactAdapter, harness: DesignSystemHarness):
    intent = harness.compose_intent(["link"])
    code = adapter.render(intent)
    assert "export function Link(" in code
    assert "href" in code


def test_render_icon_component(adapter: ReactAdapter, harness: DesignSystemHarness):
    intent = harness.compose_intent(["icon"])
    code = adapter.render(intent)
    assert "export function Icon(" in code
    assert "<svg" in code


# ── Render with layout ─────────────────────────────────────────────────────

def test_render_with_layout(adapter: ReactAdapter, harness: DesignSystemHarness):
    intent = harness.compose_intent(
        ["button", "input"],
        layout_hint=[{"type": "stack", "gap": "md", "padding": "lg", "children": []}],
    )
    code = adapter.render(intent)
    assert "PageLayout" in code
    assert "flex flex-col" in code
    assert "App()" in code


def test_render_standalone(adapter: ReactAdapter, harness: DesignSystemHarness):
    intent = harness.compose_intent(["button"])
    code = adapter.render(intent)
    assert "export default function App()" in code
    assert "<Button />" in code


# ── Validate ───────────────────────────────────────────────────────────────

def test_validate_clean(adapter: ReactAdapter, harness: DesignSystemHarness):
    intent = harness.compose_intent(["button"])
    code = adapter.render(intent)
    report = adapter.validate(code, intent)
    assert report.passed


def test_validate_with_hardcoded_value(adapter: ReactAdapter, harness: DesignSystemHarness):
    intent = harness.compose_intent(["button"])
    bad_code = "padding: 13px; border-radius: 5px;"
    report = adapter.validate(bad_code, intent)
    assert not report.passed


# ── Full pipeline: engine → adapter ────────────────────────────────────────

def test_full_pipeline_button(adapter: ReactAdapter, harness: DesignSystemHarness):
    intent = harness.compose_intent(["button"])
    code = adapter.render(intent)
    report = adapter.validate(code, intent)

    assert report.passed
    assert "Button" in code
    assert intent.meta["source"] == "manual"


def test_full_pipeline_login_form(adapter: ReactAdapter, harness: DesignSystemHarness):
    intent = harness.compose_intent(
        ["input", "button"],
        layout_hint=[{"type": "stack", "gap": "md", "padding": "lg", "children": []}],
        framework_hint="react",
    )
    code = adapter.render(intent)

    assert "Input" in code
    assert "Button" in code
    assert "PageLayout" in code
    assert intent.meta["framework_hint"] == "react"

    report = adapter.validate(code, intent)
    assert report.passed


def test_full_pipeline_all_types(adapter: ReactAdapter, harness: DesignSystemHarness):
    intent = harness.compose_intent(["button", "input", "text", "link", "icon"])
    code = adapter.render(intent)

    for t in ("Button", "Input", "Text", "Link", "Icon"):
        assert f"export function {t}(" in code

    assert len(intent.components) == 5


def test_compliance_report_shape(adapter: ReactAdapter, harness: DesignSystemHarness):
    intent = harness.compose_intent(["button"])
    code = adapter.render(intent)
    report = adapter.validate(code, intent)

    assert hasattr(report, "passed")
    assert hasattr(report, "deviations")
    assert hasattr(report, "warnings")
    assert isinstance(report.deviations, list)
    assert isinstance(report.warnings, list)
