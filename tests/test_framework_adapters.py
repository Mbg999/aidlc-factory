from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "aidlc-scripts"))
from factory_design_system_harness import SemanticIntent
from harness_adapters.framework.angular import AngularAdapter
from harness_adapters.framework.flutter import FlutterAdapter
from harness_adapters.framework.html import HtmlAdapter


@pytest.fixture
def intent() -> SemanticIntent:
    return SemanticIntent(
        tokens={
            "spacing": {"xs": 4, "sm": 8, "md": 12, "lg": 16, "xl": 24},
            "radius": {"none": 0, "sm": 3, "md": 6, "lg": 12},
            "color": {
                "brand.primary": "#2563EB",
                "neutral.text-primary": "#111827",
                "neutral.bg": "#FFFFFF",
            },
        },
        components=[
            {"type": "button", "label": "SubmitBtn", "variant": "primary", "size": "md"},
            {"type": "input", "label": "EmailField", "variant": "outlined", "size": "md"},
            {"type": "text", "label": "Title", "variant": "h2"},
        ],
        layout=[],
        meta={"framework_hint": "angular"},
    )


# ── AngularAdapter ──────────────────────────────────────────────────────

class TestAngularAdapter:
    def test_render_contains_component_decorator(self, intent: SemanticIntent):
        adapter = AngularAdapter()
        code = adapter.render(intent)
        assert "@Component" in code
        assert "selector:" in code

    def test_render_creates_components(self, intent: SemanticIntent):
        adapter = AngularAdapter()
        code = adapter.render(intent)
        assert "SubmitBtnComponent" in code
        assert "EmailFieldComponent" in code
        assert "TitleComponent" in code

    def test_render_uses_kebab_selectors(self, intent: SemanticIntent):
        adapter = AngularAdapter()
        code = adapter.render(intent)
        assert "submit-btn" in code
        assert "email-field" in code

    def test_render_has_angular_imports(self, intent: SemanticIntent):
        adapter = AngularAdapter()
        code = adapter.render(intent)
        assert "Input" in code
        assert "Output" in code
        assert "EventEmitter" in code

    def test_render_empty_intent_no_crash(self):
        adapter = AngularAdapter()
        empty = SemanticIntent(tokens={}, components=[], layout=[])
        code = adapter.render(empty)
        assert len(code) > 0

    def test_validate_detects_missing_component(self, intent: SemanticIntent):
        adapter = AngularAdapter()
        report = adapter.validate("import { Injectable } from '@angular/core';", intent)
        assert not report.passed or len(report.warnings) > 0

    def test_validate_clean_code_passes(self, intent: SemanticIntent):
        adapter = AngularAdapter()
        clean = "import { Component } from '@angular/core';\n@Component({selector: 'test'})\nexport class Test {}"
        report = adapter.validate(clean, intent)
        assert report.passed

    def test_render_with_layout(self, intent: SemanticIntent):
        intent.layout = [{"type": "stack", "gap": "md", "padding": "lg", "children": []}]
        adapter = AngularAdapter()
        code = adapter.render(intent)
        assert "flex flex-col" in code or "<!-- Layout" in code

    def test_render_text_component(self, intent: SemanticIntent):
        intent.components = [{"type": "text", "label": "Title", "variant": "h2"}]
        code = AngularAdapter().render(intent)
        assert "TitleComponent" in code
        assert "variant" in code

    def test_render_link_component(self, intent: SemanticIntent):
        intent.components = [{"type": "link", "label": "DocLink"}]
        code = AngularAdapter().render(intent)
        assert "DocLinkComponent" in code
        assert "href" in code
        assert "data-testid" in code

    def test_render_icon_component(self, intent: SemanticIntent):
        intent.components = [{"type": "icon", "label": "StarIcon"}]
        code = AngularAdapter().render(intent)
        assert "StarIconComponent" in code

    def test_render_multiple_component_types(self, intent: SemanticIntent):
        intent.components = [
            {"type": "button", "label": "Btn", "variant": "primary"},
            {"type": "input", "label": "Fld"},
            {"type": "text", "label": "Ttl"},
            {"type": "link", "label": "Lnk"},
            {"type": "icon", "label": "Icn"},
        ]
        code = AngularAdapter().render(intent)
        assert "BtnComponent" in code
        assert "FldComponent" in code
        assert "TtlComponent" in code
        assert "LnkComponent" in code
        assert "IcnComponent" in code

    def test_render_layout_with_component_child(self, intent: SemanticIntent):
        intent.layout = [{"type": "stack", "gap": "md", "children": [{"label": "SubmitBtn"}]}]
        code = AngularAdapter().render(intent)
        assert "flex flex-col" in code

    def test_render_inline_layout(self, intent: SemanticIntent):
        intent.layout = [{"type": "inline", "gap": "md", "children": []}]
        code = AngularAdapter().render(intent)
        assert "flex flex-row" in code

    def test_validate_detects_raw_px(self, intent: SemanticIntent):
        code = "<div style='padding: 12px'>bad</div>"
        report = AngularAdapter().validate(code, intent)
        assert not report.passed or len(report.deviations) > 0 or len(report.warnings) > 0

    def test_render_kebab_selector_multi_word(self, intent: SemanticIntent):
        intent.components = [{"type": "button", "label": "SubmitBtn"}]
        code = AngularAdapter().render(intent)
        assert "submit-btn" in code

    def test_render_intent_with_layout_and_components(self, intent: SemanticIntent):
        intent.components = [{"type": "button", "label": "SubmitBtn"}]
        intent.layout = [{"type": "stack", "gap": "md", "children": []}]
        code = AngularAdapter().render(intent)
        assert "submit-btn" in code


# ── FlutterAdapter ──────────────────────────────────────────────────────

class TestFlutterAdapter:
    def test_render_contains_flutter_import(self, intent: SemanticIntent):
        adapter = FlutterAdapter()
        code = adapter.render(intent)
        assert "import 'package:flutter/material.dart'" in code

    def test_render_creates_widgets(self, intent: SemanticIntent):
        adapter = FlutterAdapter()
        code = adapter.render(intent)
        assert "SubmitBtn" in code
        assert "EmailField" in code
        assert "Title" in code

    def test_render_widgets_extend_stateless(self, intent: SemanticIntent):
        adapter = FlutterAdapter()
        code = adapter.render(intent)
        assert "extends StatelessWidget" in code

    def test_render_button_has_elevated_button(self, intent: SemanticIntent):
        adapter = FlutterAdapter()
        code = adapter.render(intent)
        assert "ElevatedButton" in code

    def test_render_input_has_text_field(self, intent: SemanticIntent):
        adapter = FlutterAdapter()
        code = adapter.render(intent)
        assert "TextField" in code

    def test_render_text_has_text_widget(self, intent: SemanticIntent):
        adapter = FlutterAdapter()
        code = adapter.render(intent)
        assert "Text(" in code

    def test_render_empty_intent_no_crash(self):
        adapter = FlutterAdapter()
        empty = SemanticIntent(tokens={}, components=[], layout=[])
        code = adapter.render(empty)
        assert "import" in code

    def test_validate_detects_missing_flutter(self, intent: SemanticIntent):
        adapter = FlutterAdapter()
        report = adapter.validate("void main() {}", intent)
        assert not report.passed or len(report.warnings) > 0

    def test_render_with_stack_layout(self, intent: SemanticIntent):
        intent.layout = [{"type": "stack", "gap": "md", "children": []}]
        adapter = FlutterAdapter()
        code = adapter.render(intent)
        assert "Column(" in code

    def test_render_link_component(self, intent: SemanticIntent):
        intent.components = [{"type": "link", "label": "DocLink"}]
        code = FlutterAdapter().render(intent)
        assert "DocLink" in code
        assert "Gest" in code or "GestureDetector" in code

    def test_render_icon_component(self, intent: SemanticIntent):
        intent.components = [{"type": "icon", "label": "StarIcon"}]
        code = FlutterAdapter().render(intent)
        assert "StarIcon" in code
        assert "Icons.star" in code

    def test_render_text_component_specifics(self, intent: SemanticIntent):
        intent.components = [{"type": "text", "label": "Title", "variant": "h2"}]
        code = FlutterAdapter().render(intent)
        assert "Text(" in code
        assert "fontSize" in code

    def test_render_inline_layout(self, intent: SemanticIntent):
        intent.layout = [{"type": "inline", "gap": "md", "children": []}]
        code = FlutterAdapter().render(intent)
        assert "Row(" in code

    def test_render_stack_layout_with_children(self, intent: SemanticIntent):
        intent.layout = [{"type": "stack", "gap": "md", "children": [{"label": "SubmitBtn"}]}]
        intent.components = [{"type": "button", "label": "SubmitBtn"}]
        code = FlutterAdapter().render(intent)
        assert "Column(" in code
        assert "SubmitBtn()" in code

    def test_render_inline_layout_with_children(self, intent: SemanticIntent):
        intent.layout = [{"type": "inline", "gap": "sm", "children": [{"label": "SubmitBtn"}, {"label": "Title"}]}]
        intent.components = [
            {"type": "button", "label": "SubmitBtn"},
            {"type": "text", "label": "Title"},
        ]
        code = FlutterAdapter().render(intent)
        assert "Row(" in code
        assert "SubmitBtn()" in code
        assert "Title()" in code

    def test_render_multiple_component_types(self, intent: SemanticIntent):
        intent.components = [
            {"type": "button", "label": "Btn"},
            {"type": "input", "label": "Fld"},
            {"type": "text", "label": "Ttl"},
            {"type": "link", "label": "Lnk"},
            {"type": "icon", "label": "Icn"},
        ]
        intent.layout = []
        code = FlutterAdapter().render(intent)
        assert "Btn" in code
        assert "Fld" in code
        assert "Ttl" in code
        assert "Lnk" in code
        assert "Icn" in code

    def test_render_standalone_no_layout(self, intent: SemanticIntent):
        intent.components = [{"type": "button", "label": "SubmitBtn"}]
        intent.layout = []
        code = FlutterAdapter().render(intent)
        assert "SubmitBtn" in code
        assert "App" in code

    def test_validate_detects_sizedbox_raw(self, intent: SemanticIntent):
        code = "SizedBox(height: 12)"
        report = FlutterAdapter().validate(code, intent)
        assert not report.passed or len(report.deviations) > 0 or len(report.warnings) > 0

    def test_validate_clean_dart_passes(self, intent: SemanticIntent):
        code = "import 'package:flutter/material.dart';\nclass App extends StatelessWidget { Widget build(BuildContext context) => Container(); }"
        report = FlutterAdapter().validate(code, intent)
        assert report.passed

    def test_validate_detects_missing_import(self):
        report = FlutterAdapter().validate("void main() {}", SemanticIntent(tokens={}, components=[], layout=[]))
        assert len(report.warnings) > 0

    def test_render_empty_components_list(self):
        intent = SemanticIntent(tokens={"spacing": {"md": 8}}, components=[], layout=[])
        code = FlutterAdapter().render(intent)
        assert "import" in code


# ── HtmlAdapter ─────────────────────────────────────────────────────────

class TestHtmlAdapter:
    def test_render_contains_style_tag(self, intent: SemanticIntent):
        adapter = HtmlAdapter()
        code = adapter.render(intent)
        assert "<style>" in code

    def test_render_contains_body(self, intent: SemanticIntent):
        adapter = HtmlAdapter()
        code = adapter.render(intent)
        assert "<body>" in code

    def test_render_creates_components(self, intent: SemanticIntent):
        adapter = HtmlAdapter()
        code = adapter.render(intent)
        assert 'class="btn btn--primary btn--md"' in code or 'data-testid="SubmitBtn"' in code
        assert 'type="text"' in code or 'class="input"' in code

    def test_render_creates_css_variables(self, intent: SemanticIntent):
        adapter = HtmlAdapter()
        code = adapter.render(intent)
        assert "--color-brand-primary" in code
        assert "--xs" in code or "--spacing" in code

    def test_render_empty_intent_no_crash(self):
        adapter = HtmlAdapter()
        empty = SemanticIntent(tokens={}, components=[], layout=[])
        code = adapter.render(empty)
        assert "<style>" in code

    def test_validate_detects_no_html(self, intent: SemanticIntent):
        adapter = HtmlAdapter()
        report = adapter.validate("just some text", intent)
        assert len(report.warnings) > 0

    def test_validate_clean_html_passes(self, intent: SemanticIntent):
        adapter = HtmlAdapter()
        clean = "<!DOCTYPE html><html><body><div id='app'></div></body></html>"
        report = adapter.validate(clean, intent)
        assert report.passed

    def test_render_with_layout(self, intent: SemanticIntent):
        intent.layout = [{"type": "stack", "gap": "md", "children": []}]
        adapter = HtmlAdapter()
        code = adapter.render(intent)
        assert 'class="stack' in code

    def test_render_text_component(self, intent: SemanticIntent):
        intent.components = [{"type": "text", "label": "Title"}]
        code = HtmlAdapter().render(intent)
        assert '<span class="text"' in code

    def test_render_link_component(self, intent: SemanticIntent):
        intent.components = [{"type": "link", "label": "DocLink"}]
        code = HtmlAdapter().render(intent)
        assert '<a class="link"' in code
        assert "href=" in code

    def test_render_icon_component(self, intent: SemanticIntent):
        intent.components = [{"type": "icon", "label": "StarIcon"}]
        code = HtmlAdapter().render(intent)
        assert 'class="icon"' in code
        assert 'data-icon="StarIcon"' in code

    def test_render_all_component_types(self, intent: SemanticIntent):
        intent.components = [
            {"type": "button", "label": "Btn", "variant": "primary"},
            {"type": "input", "label": "Fld"},
            {"type": "text", "label": "Ttl"},
            {"type": "link", "label": "Lnk"},
            {"type": "icon", "label": "Icn"},
        ]
        intent.layout = []
        code = HtmlAdapter().render(intent)
        assert 'class="btn' in code
        assert 'class="input"' in code
        assert '<span class="text"' in code
        assert '<a class="link"' in code
        assert 'class="icon"' in code

    def test_render_inline_layout(self, intent: SemanticIntent):
        intent.layout = [{"type": "inline", "gap": "md", "children": []}]
        code = HtmlAdapter().render(intent)
        assert 'class="inline' in code

    def test_render_layout_with_component_child(self, intent: SemanticIntent):
        intent.layout = [{"type": "stack", "gap": "md", "children": [{"label": "SubmitBtn"}]}]
        code = HtmlAdapter().render(intent)
        assert 'data-component="SubmitBtn"' in code

    def test_render_css_vars_color_and_radius(self, intent: SemanticIntent):
        intent.tokens = {
            "color": {"brand.primary": "#2563EB"},
            "radius": {"md": 6},
            "spacing": {"md": 12},
        }
        code = HtmlAdapter().render(intent)
        assert "--color-brand-primary" in code
        assert "--md" in code

    def test_render_component_fallback(self, intent: SemanticIntent):
        intent.components = [{"type": "unknown_type", "label": "CustomThing"}]
        code = HtmlAdapter().render(intent)
        assert "<div" in code

    def test_validate_detects_raw_px(self, intent: SemanticIntent):
        code = "<div style='padding: 12px'>bad</div>"
        report = HtmlAdapter().validate(code, intent)
        assert not report.passed or len(report.deviations) > 0 or len(report.warnings) > 0

    def test_validate_detects_missing_doctype(self):
        report = HtmlAdapter().validate("just some text", SemanticIntent(tokens={}, components=[], layout=[]))
        assert len(report.warnings) > 0

    def test_render_empty_components_list(self):
        intent = SemanticIntent(tokens={"spacing": {"md": 8}}, components=[], layout=[])
        code = HtmlAdapter().render(intent)
        assert "<style>" in code
