from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "aidlc-scripts"))
from factory_ds_bootstrap import (
    cmd_init,
    cmd_import,
    _build_imported_index,
    _parse_json_tokens,
    _parse_material_tokens,
    _parse_stitch_designmd,
    _tokens_to_md,
)


# ── Fixtures ────────────────────────────────────────────────────────────

@pytest.fixture
def tmp_repo(tmp_path: Path) -> Path:
    return tmp_path


# ── Init tests ──────────────────────────────────────────────────────────

def test_init_dry_run_does_not_write(tmp_repo: Path):
    assert cmd_init(tmp_repo, force=False, dry_run=True) == 0
    assert not (tmp_repo / "design-system").exists()


def test_init_creates_token_files(tmp_repo: Path):
    assert cmd_init(tmp_repo, force=False, dry_run=False) == 0
    ds = tmp_repo / "design-system"
    assert (ds / "tokens" / "spacing.md").exists()
    assert (ds / "tokens" / "radius.md").exists()
    assert (ds / "tokens" / "typography.md").exists()
    assert (ds / "tokens" / "color.md").exists()
    assert (ds / "tokens" / "elevation.md").exists()
    assert (ds / "INDEX.md").exists()
    assert (ds / "patterns" / "form-layout.md").exists()
    assert (ds / "patterns" / "navigation.md").exists()
    assert (ds / "patterns" / "modal-dialog.md").exists()


def test_init_creates_primitives(tmp_repo: Path):
    assert cmd_init(tmp_repo, force=False, dry_run=False) == 0
    primitives = tmp_repo / "design-system" / "primitives"
    assert primitives.exists()
    assert (primitives / "Button" / "design.md").exists() or \
           (primitives / "Stack" / "design.md").exists()


def test_init_no_force_skips_existing(tmp_repo: Path):
    (tmp_repo / "design-system" / "tokens").mkdir(parents=True)
    (tmp_repo / "design-system" / "tokens" / "spacing.md").write_text("custom")
    cmd_init(tmp_repo, force=False, dry_run=False)
    assert (tmp_repo / "design-system" / "tokens" / "spacing.md").read_text() == "custom"


def test_init_force_overwrites(tmp_repo: Path):
    (tmp_repo / "design-system" / "tokens").mkdir(parents=True)
    (tmp_repo / "design-system" / "tokens" / "spacing.md").write_text("custom")
    cmd_init(tmp_repo, force=True, dry_run=False)
    content = (tmp_repo / "design-system" / "tokens" / "spacing.md").read_text()
    assert content != "custom"
    assert "spacing.xs" in content


# ── JSON import tests ──────────────────────────────────────────────────

def test_parse_json_spacing_object():
    data = _parse_json_tokens({"spacing": {"sm": 8, "md": 16, "lg": 24}})
    assert data["spacing"] == {"sm": 8, "md": 16, "lg": 24}


def test_parse_json_spacing_array():
    data = _parse_json_tokens({"spacing": [4, 8, 12, 16]})
    assert data["spacing"]["xs"] == 4
    assert data["spacing"]["sm"] == 8
    assert data["spacing"]["md"] == 12
    assert data["spacing"]["lg"] == 16


def test_parse_json_color():
    data = _parse_json_tokens({"color": {"primary": "#ff0000", "bg": "#fff"}})
    assert data["color"]["primary"] == "#ff0000"


def test_parse_json_radius():
    data = _parse_json_tokens({"radius": [0, 2, 4, 8]})
    assert data["radius"]["none"] == 0
    assert data["radius"]["sm"] == 2
    assert data["radius"]["md"] == 4


def test_parse_json_typography():
    data = _parse_json_tokens({"typography": {"body": 14, "h1": 32}})
    assert data["typography"]["body"]["size"] == 14
    assert data["typography"]["h1"]["size"] == 32


def test_import_json_dry_run(tmp_repo: Path):
    json_path = tmp_repo / "source.json"
    json_path.write_text(json.dumps({
        "spacing": [2, 4, 8, 16],
        "color": {"primary": "#000"},
        "radius": {"sm": 2, "md": 4},
    }))
    assert cmd_import(tmp_repo, str(json_path), "json",
                      force=False, dry_run=True) == 0
    assert not (tmp_repo / "design-system").exists()


def test_import_json_writes_tokens(tmp_repo: Path):
    json_path = tmp_repo / "source.json"
    json_path.write_text(json.dumps({
        "spacing": [2, 4, 8, 16],
        "color": {"primary": "#000", "bg": "#fff"},
        "radius": {"sm": 2, "md": 4},
    }))
    assert cmd_import(tmp_repo, str(json_path), "json",
                      force=True, dry_run=False) == 0
    ds = tmp_repo / "design-system"
    assert (ds / "tokens" / "spacing.md").exists()
    assert (ds / "tokens" / "color.md").exists()
    assert (ds / "tokens" / "radius.md").exists()
    content = (ds / "tokens" / "spacing.md").read_text()
    assert "spacing.xs" in content
    assert "2" in content


# ── Material import tests ──────────────────────────────────────────────

def test_parse_material_spacing():
    data = _parse_material_tokens({"spacing": [4, 8, 16, 24, 32, 40]})
    assert data["spacing"]["xs"] == 4
    assert data["spacing"]["xl"] == 32


def test_parse_material_color():
    data = _parse_material_tokens({"color": {"primary": "#6200EE", "secondary": "#03DAC6"}})
    assert data["color"]["primary"] == "#6200EE"


# ── Stitch DESIGN.md import tests ──────────────────────────────────────

def test_parse_stitch_designmd():
    content = """
| `--spacing-sm` | `8px` | Small spacing |
| `--spacing-md` | `16px` | Medium spacing |
| `--radius-sm` | `4px` | Small radius |
| `--color-primary` | `#2563EB` | Primary color |
"""
    data = _parse_stitch_designmd(content)
    assert "--spacing-sm" in data["spacing"]
    assert data["spacing"]["--spacing-md"] == 16
    assert "--radius-sm" in data["radius"]
    assert data["radius"]["--radius-sm"] == 4
    assert "--color-primary" in data["color"]


# ── tokens_to_md tests ─────────────────────────────────────────────────

def test_tokens_to_md_spacing():
    files = _tokens_to_md({"spacing": {"sm": 8, "md": 16}})
    assert "design-system/tokens/spacing.md" in files
    assert "spacing.sm" in files["design-system/tokens/spacing.md"]
    assert "8" in files["design-system/tokens/spacing.md"]


def test_tokens_to_md_color():
    files = _tokens_to_md({"color": {"primary": "#000"}})
    assert "design-system/tokens/color.md" in files


def test_tokens_to_md_typography():
    files = _tokens_to_md({"typography": {"body": {"size": 14}}})
    assert "design-system/tokens/typography.md" in files


# ── INDEX.md tests ─────────────────────────────────────────────────────

def test_build_imported_index():
    tokens = {"spacing": {"sm": 8, "md": 16}, "color": {"primary": "#000"}}
    index = _build_imported_index(tokens)
    assert "Spacing" in index
    assert "8, 16" in index
    assert "color" in index or "Color" in index


# ── Error handling ─────────────────────────────────────────────────────

def test_import_missing_file(tmp_repo: Path):
    rc = cmd_import(tmp_repo, "/nonexistent/file.json", "json",
                    force=False, dry_run=False)
    assert rc != 0


def test_import_bad_format(tmp_repo: Path, tmp_path: Path):
    rc = cmd_import(tmp_repo, str(tmp_path / "x.json"), "badformat",
                    force=False, dry_run=True)
    assert rc != 0
