from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parent.parent / "aidlc-scripts"
LEARN_PY = SCRIPTS / "factory_design_system_learn.py"


# ── Fixtures ────────────────────────────────────────────────────────────────


@pytest.fixture
def ds_root(tmp_path: Path) -> Path:
    """Create a temporary AIDLC repo with a minimal design system."""
    _init_repo(tmp_path)
    _init_design_system(tmp_path)
    os.environ["AIDLC_ROOT"] = str(tmp_path)
    yield tmp_path
    os.environ.pop("AIDLC_ROOT", None)


def _init_repo(root: Path) -> None:
    """Create minimal repo structure needed for script to work."""
    scripts = root / "aidlc-scripts"
    scripts.mkdir(parents=True)


def _init_design_system(root: Path) -> None:
    """Create a minimal design system with tokens, INDEX.md, and one primitive."""
    ds = root / "design-system"
    ds.mkdir(parents=True)

    # INDEX.md
    (ds / "INDEX.md").write_text(
        "# Design System Index\n\n"
        "## Primitives\n\n"
        "| Primitive | Description |\n"
        "|-----------|-------------|\n"
        "| `Button` | Clickable action element |\n"
        "| `Stack` | Vertical layout container |\n"
        "| `Inline` | Horizontal layout container |\n"
        "| `Box` | Generic container |\n"
    )

    # Tokens
    tokens = ds / "tokens"
    tokens.mkdir()
    (tokens / "spacing.md").write_text(
        "# Spacing Tokens\n\n"
        "| Token | Value |\n"
        "|-------|-------|\n"
        "| `spacing.xs` | 4px |\n"
        "| `spacing.sm` | 8px |\n"
        "| `spacing.md` | 12px |\n"
        "| `spacing.lg` | 16px |\n"
    )

    # Primitive: Button
    button_dir = ds / "primitives" / "Button"
    button_dir.mkdir(parents=True)
    (button_dir / "design.md").write_text("# Button\n\nPrimary action primitive.\n")
    (button_dir / "anatomy.md").write_text("# Button Anatomy\n\nProps: variant, size, label\n")

    # Primitive: Stack
    stack_dir = ds / "primitives" / "Stack"
    stack_dir.mkdir(parents=True)
    (stack_dir / "design.md").write_text("# Stack\n\nVertical layout primitive.\n")
    (stack_dir / "anatomy.md").write_text("# Stack Anatomy\n\nProps: gap, padding\n")


# ── Helper ───────────────────────────────────────────────────────────────────


def _run_learn(*args: str, ds_root: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(LEARN_PY), "--repo-root", str(ds_root), *args],
        capture_output=True, text=True,
        env={**os.environ, "AIDLC_ROOT": str(ds_root)},
    )


# ── Tests: approve ───────────────────────────────────────────────────────────


class TestApprove:
    def test_approve_saves_example(self, ds_root: Path):
        result = _run_learn(
            "approve", "--component", "Button",
            "--code", "<Button variant='primary' size='md' label='Save' />",
            "--source", "src/components/SaveButton.tsx",
            "--run-id", "test-001",
            ds_root=ds_root,
        )
        assert result.returncode == 0
        assert "Saved approved" in result.stdout

        # Verify file was created
        examples_dir = ds_root / "design-system" / "primitives" / "Button" / "examples"
        assert examples_dir.exists()
        example_files = list(examples_dir.glob("approved-*.md"))
        assert len(example_files) == 1
        content = example_files[0].read_text()
        assert "Button" in content
        assert "SaveButton.tsx" in content
        assert "test-001" in content
        assert "primitives" in content

    def test_approve_trim_to_cap(self, ds_root: Path):
        """After 3 approvals with the same component, the oldest is trimmed."""
        for i in range(1, 6):
            result = _run_learn(
                "approve", "--component", "Button",
                "--code", f"<Button label='Item {i}' />",
                "--source", f"src/Button{i}.tsx",
                "--run-id", f"test-{i:03d}",
                ds_root=ds_root,
            )
            assert result.returncode == 0

        examples_dir = ds_root / "design-system" / "primitives" / "Button" / "examples"
        example_files = sorted(examples_dir.glob("approved-*.md"))
        assert len(example_files) == 3, f"Expected max 3, got {len(example_files)}"

    def test_approve_with_stack(self, ds_root: Path):
        result = _run_learn(
            "approve", "--component", "Stack",
            "--code", "<Stack gap='md'><Box padding='sm' /></Stack>",
            "--source", "src/components/Card.tsx",
            "--run-id", "test-002",
            ds_root=ds_root,
        )
        assert result.returncode == 0
        assert "Saved approved" in result.stdout

    def test_approve_json_output(self, ds_root: Path):
        result = _run_learn(
            "--json", "approve", "--component", "Button",
            "--code", "<Button label='OK' />",
            "--source", "src/OK.tsx",
            "--run-id", "test-003",
            ds_root=ds_root,
        )
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert "path" in data
        assert "logs" in data
        assert Path(data["path"]).exists()

    def test_approve_nonexistent_component(self, ds_root: Path):
        """approve creates the directory even if the primitive doesn't exist yet."""
        result = _run_learn(
            "approve", "--component", "Input",
            "--code", "<Input placeholder='Name' />",
            "--source", "src/NameInput.tsx",
            "--run-id", "test-004",
            ds_root=ds_root,
        )
        assert result.returncode == 0
        examples_dir = ds_root / "design-system" / "primitives" / "Input" / "examples"
        assert examples_dir.exists()
        assert len(list(examples_dir.glob("approved-*.md"))) == 1


# ── Tests: reject ────────────────────────────────────────────────────────────


class TestReject:
    def test_reject_saves_antipattern(self, ds_root: Path):
        result = _run_learn(
            "reject", "--component", "Button",
            "--reason", "Missing loading state — button flashes from text to spinner",
            "--source", "src/components/SaveButton.tsx",
            "--run-id", "test-001",
            ds_root=ds_root,
        )
        assert result.returncode == 0
        assert "Saved antipattern" in result.stdout

        # Verify file was created
        live_dir = ds_root / "design-system" / "anti-patterns" / "live"
        assert live_dir.exists()
        files = list(live_dir.glob("*.md"))
        assert len(files) >= 1
        content = files[0].read_text()
        assert "Button" in content
        assert "loading state" in content
        assert "test-001" in content

    def test_reject_multiple_separate_issues(self, ds_root: Path):
        for i, reason in enumerate(["Missing aria-label", "No focus trap", "Hardcoded color"]):
            result = _run_learn(
                "reject", "--component", "Button",
                "--reason", reason,
                "--source", f"src/issue{i}.tsx",
                "--run-id", f"test-{i:03d}",
                ds_root=ds_root,
            )
            assert result.returncode == 0

        live_dir = ds_root / "design-system" / "anti-patterns" / "live"
        files = list(live_dir.glob("*.md"))
        assert len(files) == 3

    def test_reject_json_output(self, ds_root: Path):
        result = _run_learn(
            "--json", "reject", "--component", "Stack",
            "--reason", "Unnecessary nesting depth > 3",
            "--source", "src/DeepStack.tsx",
            "--run-id", "test-005",
            ds_root=ds_root,
        )
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert "path" in data
        assert Path(data["path"]).exists()


# ── Tests: update-index ──────────────────────────────────────────────────────


class TestUpdateIndex:
    def test_update_index_with_examples(self, ds_root: Path):
        _run_learn(
            "approve", "--component", "Button",
            "--code", "<Button label='OK' />",
            "--source", "src/OK.tsx",
            "--run-id", "test-001",
            ds_root=ds_root,
        )
        _run_learn(
            "approve", "--component", "Stack",
            "--code", "<Stack gap='md' />",
            "--source", "src/StackTest.tsx",
            "--run-id", "test-002",
            ds_root=ds_root,
        )

        result = _run_learn("update-index", ds_root=ds_root)
        assert result.returncode == 0
        assert "Updated INDEX.md" in result.stdout

        index_content = (ds_root / "design-system" / "INDEX.md").read_text()
        assert "Usage Count" in index_content
        assert "Button" in index_content
        assert "Stack" in index_content

    def test_update_index_no_examples(self, ds_root: Path):
        result = _run_learn("update-index", ds_root=ds_root)
        assert result.returncode == 0
        assert "No approved examples" in result.stdout

    def test_update_index_deduplicates(self, ds_root: Path):
        """Re-running update-index shouldn't duplicate the Usage Count section."""
        _run_learn(
            "approve", "--component", "Button",
            "--code", "<Button />",
            "--source", "src/Btn.tsx",
            "--run-id", "test-001",
            ds_root=ds_root,
        )
        _run_learn("update-index", ds_root=ds_root)
        result = _run_learn("update-index", ds_root=ds_root)

        assert result.returncode == 0
        index_content = (ds_root / "design-system" / "INDEX.md").read_text()
        assert index_content.count("Usage Count") == 1


# ── Tests: error handling ────────────────────────────────────────────────────


class TestErrors:
    def test_missing_component(self, ds_root: Path):
        result = _run_learn(
            "approve",
            "--code", "<Button />",
            "--source", "src/Btn.tsx",
            "--run-id", "test-001",
            ds_root=ds_root,
        )
        assert result.returncode == 2

    def test_missing_code(self, ds_root: Path):
        result = _run_learn(
            "approve", "--component", "Button",
            "--source", "src/Btn.tsx",
            "--run-id", "test-001",
            ds_root=ds_root,
        )
        assert result.returncode == 2

    def test_invalid_command(self, ds_root: Path):
        result = _run_learn("nonexistent", ds_root=ds_root)
        assert result.returncode == 2
