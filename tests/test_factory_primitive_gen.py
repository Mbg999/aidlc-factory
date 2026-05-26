from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "aidlc-scripts"))
from factory_primitive_gen import (
    list_primitives,
    generate_primitive,
    generate_all_missing,
)


# ── list_primitives ──────────────────────────────────────────────────────

class TestListPrimitives:
    def test_real_primitives_listed(self):
        prims = list_primitives()
        names = {p["name"] for p in prims}
        assert "Button" in names
        assert "Stack" in names
        assert "Input" in names
        assert len(prims) >= 7

    def test_button_is_complete(self):
        prims = list_primitives()
        by_name = {p["name"]: p for p in prims}
        assert by_name["Button"]["complete"]

    def test_each_has_category(self):
        prims = list_primitives()
        for p in prims:
            assert p["category"] != "unknown"

    def test_list_is_sorted(self):
        prims = list_primitives()
        names = [p["name"] for p in prims]
        assert names == sorted(names)


# ── generate_primitive ───────────────────────────────────────────────────

class TestGeneratePrimitive:
    def test_dry_run_does_not_create_files(self, tmp_path: Path, monkeypatch):
        monkeypatch.setattr("factory_primitive_gen.DS_PRIMITIVES", tmp_path / "prims")
        d = tmp_path / "prims"
        (d / "TestComp").mkdir(parents=True)
        (d / "TestComp" / "design.md").write_text("# TestComp\n")
        result = generate_primitive("TestComp", dry_run=True)
        assert not (d / "TestComp" / "anatomy.md").exists()
        assert any("dry-run" in r for r in result)

    def test_creates_missing_files(self, tmp_path: Path, monkeypatch):
        monkeypatch.setattr("factory_primitive_gen.DS_PRIMITIVES", tmp_path / "prims")
        d = tmp_path / "prims"
        (d / "Stack").mkdir(parents=True)
        (d / "Stack" / "design.md").write_text("# Stack\n")
        result = generate_primitive("Stack", style="web")
        created = [r for r in result if "Created" in r]
        assert any("anatomy.md" in r for r in created)
        assert any("do-dont.md" in r for r in created)

    def test_does_not_overwrite_existing(self, tmp_path: Path, monkeypatch):
        monkeypatch.setattr("factory_primitive_gen.DS_PRIMITIVES", tmp_path / "prims")
        d = tmp_path / "prims"
        (d / "Stack").mkdir(parents=True)
        (d / "Stack" / "design.md").write_text("original")
        generate_primitive("Stack", style="web", force=False)
        assert (d / "Stack" / "design.md").read_text() == "original"

    def test_force_overwrites(self, tmp_path: Path, monkeypatch):
        monkeypatch.setattr("factory_primitive_gen.DS_PRIMITIVES", tmp_path / "prims")
        d = tmp_path / "prims"
        (d / "Stack").mkdir(parents=True)
        (d / "Stack" / "design.md").write_text("original")
        generate_primitive("Stack", style="web", force=True)
        assert "original" not in (d / "Stack" / "design.md").read_text()

    def test_generates_valid_markdown(self, tmp_path: Path, monkeypatch):
        monkeypatch.setattr("factory_primitive_gen.DS_PRIMITIVES", tmp_path / "prims")
        d = tmp_path / "prims"
        (d / "Button").mkdir(parents=True)
        (d / "Button" / "design.md").write_text("# Button\n")
        generate_primitive("Button", style="web", force=True)
        anat = (d / "Button" / "anatomy.md").read_text(encoding="utf-8")
        assert "# Button" in anat
        dodont = (d / "Button" / "do-dont.md").read_text(encoding="utf-8")
        assert "Do" in dodont

    def test_unknown_primitive_still_creates_minimal(self, tmp_path: Path, monkeypatch):
        monkeypatch.setattr("factory_primitive_gen.DS_PRIMITIVES", tmp_path / "prims")
        d = tmp_path / "prims"
        (d / "FooBar").mkdir(parents=True)
        result = generate_primitive("FooBar", style="web")
        assert len(result) >= 2


# ── generate_all_missing ─────────────────────────────────────────────────

class TestGenerateAllMissing:
    def test_skips_complete_primitives(self, tmp_path: Path, monkeypatch):
        monkeypatch.setattr("factory_primitive_gen.DS_PRIMITIVES", tmp_path / "prims")
        d = tmp_path / "prims"
        for p in ("Button", "Stack"):
            (d / p).mkdir(parents=True)
            (d / p / "design.md").write_text("#")
            (d / p / "anatomy.md").write_text("#")
            (d / p / "do-dont.md").write_text("#")
        result = generate_all_missing(style="web", dry_run=True)
        assert len(result) == 0

    def test_generates_only_missing(self, tmp_path: Path, monkeypatch):
        monkeypatch.setattr("factory_primitive_gen.DS_PRIMITIVES", tmp_path / "prims")
        d = tmp_path / "prims"
        (d / "Button").mkdir(parents=True)
        (d / "Button" / "design.md").write_text("#")
        (d / "Button" / "anatomy.md").write_text("#")
        (d / "Button" / "do-dont.md").write_text("#")
        (d / "Input").mkdir(parents=True)
        (d / "Input" / "design.md").write_text("#")
        result = generate_all_missing(style="web", dry_run=True)
        assert any("Input" in r for r in result)
        assert not any("Button" in r for r in result)

    def test_empty_primitives_dir_no_crash(self, tmp_path: Path, monkeypatch):
        monkeypatch.setattr("factory_primitive_gen.DS_PRIMITIVES", tmp_path / "empty")
        (tmp_path / "empty").mkdir(exist_ok=True)
        result = generate_all_missing(style="web")
        assert result == []


# ── Template quality ─────────────────────────────────────────────────────

class TestTemplateQuality:
    def test_button_template_has_variants(self):
        from factory_primitive_gen import _design_template
        content = _design_template("button", "web")
        assert "primary" in content
        assert "secondary" in content
        assert "danger" in content

    def test_stack_template_has_gap(self):
        from factory_primitive_gen import _design_template
        content = _design_template("stack", "web")
        assert "gap" in content
        assert "spacing" in content

    def test_input_template_has_accessibility(self):
        from factory_primitive_gen import _design_template
        content = _design_template("input", "web")
        assert "Accessibility" in content
        assert "aria-describedby" in content

    def test_all_primitives_have_design_template(self):
        from factory_primitive_gen import _PRIMITIVE_META, _design_template
        for name in _PRIMITIVE_META:
            content = _design_template(name, "web")
            assert f"# {_PRIMITIVE_META[name]['title']}" in content

    def test_all_primitives_have_anatomy_template(self):
        from factory_primitive_gen import _PRIMITIVE_META, _anatomy_template
        for name in _PRIMITIVE_META:
            content = _anatomy_template(name, "web")
            assert "## Element structure" in content

    def test_all_primitives_have_dodont_template(self):
        from factory_primitive_gen import _PRIMITIVE_META, _dodont_template
        for name in _PRIMITIVE_META:
            content = _dodont_template(name, "web")
            assert "DO" in content or "Do" in content

    def test_flutter_style_generates(self):
        from factory_primitive_gen import _design_template
        content = _design_template("button", "flutter")
        assert len(content) > 20

    def test_text_variants_listed(self):
        from factory_primitive_gen import _design_template
        content = _design_template("text", "web")
        assert "h1" in content
        assert "body" in content
        assert "caption" in content
