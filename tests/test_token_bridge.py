from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "aidlc-scripts"))
from factory_token_to_css import generate_css, inspect_tokens


# ── Fixture ────────────────────────────────────────────────────────────────

@pytest.fixture
def repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


# ── generate_css ───────────────────────────────────────────────────────────

def test_generate_css_contains_all_token_categories(repo_root: Path):
    css = generate_css(repo_root)
    assert "spacing" in css
    assert "radius" in css
    assert "typography" in css
    assert "color" in css
    assert "--spacing-md: 12px" in css
    assert "--radius-sm: 3px" in css
    assert "--radius-full: 9999px" in css


def test_generate_css_valid_syntax(repo_root: Path):
    css = generate_css(repo_root)
    lines = css.splitlines()
    open_blocks = 0
    for line in lines:
        stripped = line.strip()
        if stripped == ":root {":
            open_blocks += 1
        elif stripped == "}":
            open_blocks -= 1
        elif stripped.startswith("--") and not stripped.startswith("/*"):
            assert ":" in stripped, f"Invalid CSS var: {stripped}"
            assert stripped.endswith(";"), f"Missing semicolon: {stripped}"
    assert open_blocks == 0, f"Unclosed :root blocks: {open_blocks}"


def test_generate_css_color_vars_have_clean_names(repo_root: Path):
    css = generate_css(repo_root)
    for line in css.splitlines():
        if "--color-" in line and ":" in line:
            var_name = line.split(":")[0].strip()
            assert "color.color" not in var_name, f"Double prefix in: {var_name}"
            assert var_name.startswith("--color-")


def test_generate_css_typography_includes_hyphenated_names(repo_root: Path):
    css = generate_css(repo_root)
    assert "--typography-body-large" in css


def test_generate_css_spacing_values_are_multiples_of_4(repo_root: Path):
    css = generate_css(repo_root)
    for line in css.splitlines():
        if "--spacing-" in line and ":" in line:
            val = line.split(":")[1].strip().replace("px;", "")
            if val.isdigit():
                assert int(val) % 4 == 0, f"Spacing not multiple of 4: {line.strip()}"


def test_generate_css_with_raw_comments(repo_root: Path):
    css = generate_css(repo_root, include_raw_values=True)
    assert "as number" in css


def test_generate_css_empty_tokens_dir(tmp_path: Path):
    css = generate_css(tmp_path)
    assert "No design-system/tokens/ directory found" in css


# ── inspect_tokens ─────────────────────────────────────────────────────────

def test_inspect_tokens_all_categories(repo_root: Path):
    data = inspect_tokens(repo_root)
    assert "spacing" in data
    assert "radius" in data
    assert "typography" in data
    assert "color" in data
    assert data["_meta"]["categories"] >= 4


def test_inspect_tokens_counts(repo_root: Path):
    data = inspect_tokens(repo_root)
    assert data["spacing"]["exists"]
    assert data["spacing"]["count"] >= 4
    assert data["color"]["count"] >= 5


def test_inspect_tokens_values(repo_root: Path):
    data = inspect_tokens(repo_root)
    assert data["spacing"]["tokens"]["md"] == "12px"
    assert data["radius"]["tokens"]["sm"] == "3px"
    assert data["color"]["tokens"]["color.brand.primary"] == "#2563eb"


def test_inspect_no_tokens_dir(tmp_path: Path):
    data = inspect_tokens(tmp_path)
    assert "error" in data


# ── tokens.css file ────────────────────────────────────────────────────────

def test_tokens_css_file_exists(repo_root: Path):
    css_file = repo_root / "design-system" / "tokens" / "tokens.css"
    assert css_file.exists(), "tokens.css not generated yet. Run factory_token_to_css.py generate"
    content = css_file.read_text(encoding="utf-8")
    assert "--spacing-md: 12px" in content
    assert "--radius-sm: 3px" in content


# ── Prompt templates ───────────────────────────────────────────────────────


def test_tech_stack_prompts_exist(repo_root: Path):
    prompts_dir = repo_root / "aidlc-scripts" / "prompts" / "tech-stack"
    assert prompts_dir.exists(), "prompts/tech-stack/ directory not found"
    prompt_file = prompts_dir / "tokens.md"
    assert prompt_file.exists(), "Missing generic prompt: tokens.md"


def test_tech_stack_prompt_content(repo_root: Path):
    prompt_file = repo_root / "aidlc-scripts" / "prompts" / "tech-stack" / "tokens.md"
    content = prompt_file.read_text(encoding="utf-8")
    assert "var(--spacing" in content
    assert "Token usage" in content
    assert "No raw values" in content
    assert len(content) > 200


def test_tech_stack_prompts_mention_var(repo_root: Path):
    prompt_file = repo_root / "aidlc-scripts" / "prompts" / "tech-stack" / "tokens.md"
    content = prompt_file.read_text(encoding="utf-8")
    assert "var(--spacing" in content
    assert "var(--color" in content
