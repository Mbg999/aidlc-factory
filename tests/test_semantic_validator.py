from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "aidlc-scripts"))
from factory_design_system_harness import SemanticIntent
from harness_adapters.validators.semantic_validator import SemanticConstraintValidator


@pytest.fixture
def valid_intent() -> SemanticIntent:
    return SemanticIntent(
        tokens={
            "spacing": {"xs": 4, "sm": 8, "md": 12, "lg": 16, "xl": 24},
            "color": {
                "brand.primary": "#2563EB",
                "neutral.text": "#111827",
                "neutral.bg": "#FFFFFF",
                "danger": "#DC2626",
            },
            "radius": {"none": 0, "sm": 3, "md": 6, "lg": 12},
        },
        components=[
            {"type": "button", "label": "SubmitBtn", "variant": "primary", "size": "md"},
            {"type": "text", "label": "Title"},
        ],
        layout=[{"type": "stack", "gap": "md", "children": []}],
    )


class TestTokenValidation:
    def test_valid_intent_passes(self, valid_intent: SemanticIntent):
        report = SemanticConstraintValidator().validate(valid_intent)
        assert report.passed

    def test_missing_spacing_is_deviation(self):
        intent = SemanticIntent(tokens={}, components=[], layout=[])
        report = SemanticConstraintValidator().validate(intent)
        assert not report.passed
        assert any("spacing" in d.get("detail", "") for d in report.deviations)

    def test_missing_color_is_deviation(self):
        intent = SemanticIntent(tokens={"spacing": {"md": 8}}, components=[], layout=[])
        report = SemanticConstraintValidator().validate(intent)
        assert not report.passed
        assert any("color" in d.get("detail", "") for d in report.deviations)

    def test_missing_radius_is_warning(self):
        intent = SemanticIntent(
            tokens={"spacing": {"md": 8}, "color": {"brand.primary": "#2563EB"}},
            components=[],
            layout=[],
        )
        report = SemanticConstraintValidator().validate(intent)
        assert report.passed
        assert any("radius" in w for w in report.warnings)

    def test_spacing_not_multiples_of_4_warns(self):
        intent = SemanticIntent(
            tokens={
                "spacing": {"xs": 4, "sm": 7, "md": 12, "lg": 16, "xl": 24},
                "color": {"brand.primary": "#2563EB"},
            },
            components=[],
            layout=[],
        )
        report = SemanticConstraintValidator().validate(intent)
        assert any("sm" in w and "multiple" in w for w in report.warnings)

    def test_invalid_hex_color_is_deviation(self):
        intent = SemanticIntent(
            tokens={
                "spacing": {"md": 8},
                "color": {"brand.primary": "not-a-color"},
            },
            components=[],
            layout=[],
        )
        report = SemanticConstraintValidator().validate(intent)
        assert not report.passed
        assert any("not a valid" in d.get("detail", "").lower() for d in report.deviations)


class TestComponentValidation:
    def test_invalid_component_type_is_deviation(self):
        intent = SemanticIntent(
            tokens={"spacing": {"md": 8}, "color": {"brand.primary": "#2563EB"}},
            components=[{"type": "slider", "label": "Slider"}],
            layout=[],
        )
        report = SemanticConstraintValidator().validate(intent)
        assert not report.passed
        assert any("slider" in d.get("detail", "") for d in report.deviations)

    def test_component_without_label_warns(self):
        intent = SemanticIntent(
            tokens={"spacing": {"md": 8}, "color": {"brand.primary": "#2563EB"}},
            components=[{"type": "button"}],
            layout=[],
        )
        report = SemanticConstraintValidator().validate(intent)
        assert any("no label" in w.lower() for w in report.warnings)

    def test_no_components_warns(self):
        intent = SemanticIntent(
            tokens={"spacing": {"md": 8}, "color": {"brand.primary": "#2563EB"}},
            components=[],
            layout=[],
        )
        report = SemanticConstraintValidator().validate(intent)
        assert any("no components" in w.lower() for w in report.warnings)


class TestLayoutValidation:
    def test_invalid_layout_type_is_deviation(self):
        intent = SemanticIntent(
            tokens={"spacing": {"md": 8}, "color": {"brand.primary": "#2563EB"}},
            components=[],
            layout=[{"type": "gridish", "children": []}],
        )
        report = SemanticConstraintValidator().validate(intent)
        assert not report.passed
        assert any("gridish" in d.get("detail", "") for d in report.deviations)

    def test_nested_layout_validated_recursively(self):
        intent = SemanticIntent(
            tokens={"spacing": {"md": 8}, "color": {"brand.primary": "#2563EB"}},
            components=[],
            layout=[{"type": "stack", "children": [{"type": "unknown_nested", "children": []}]}],
        )
        report = SemanticConstraintValidator().validate(intent)
        assert not report.passed
        assert any("unknown_nested" in d.get("detail", "") for d in report.deviations)

    def test_valid_layout_types_pass(self, valid_intent: SemanticIntent):
        report = SemanticConstraintValidator().validate(valid_intent)
        assert report.passed

    def test_all_layout_types_pass(self):
        intent = SemanticIntent(
            tokens={"spacing": {"md": 8}, "color": {"brand.primary": "#2563EB"}},
            components=[],
            layout=[
                {"type": "stack", "children": []},
                {"type": "inline", "children": []},
                {"type": "box", "children": []},
                {"type": "grid", "children": []},
                {"type": "surface", "children": []},
            ],
        )
        report = SemanticConstraintValidator().validate(intent)
        assert report.passed


class TestCrossReferenceValidation:
    def test_layout_gap_not_in_tokens_warns(self):
        intent = SemanticIntent(
            tokens={"spacing": {"md": 8}, "color": {"brand.primary": "#2563EB"}},
            components=[],
            layout=[{"type": "stack", "gap": "nonexistent", "children": []}],
        )
        report = SemanticConstraintValidator().validate(intent)
        assert any("nonexistent" in w for w in report.warnings)

    def test_layout_child_label_not_in_components_warns(self):
        intent = SemanticIntent(
            tokens={"spacing": {"md": 8}, "color": {"brand.primary": "#2563EB"}},
            components=[{"type": "button", "label": "SubmitBtn"}],
            layout=[{"type": "stack", "children": [{"label": "NonExistent"}]}],
        )
        report = SemanticConstraintValidator().validate(intent)
        assert any("NonExistent" in w for w in report.warnings)
