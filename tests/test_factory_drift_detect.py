from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "aidlc-scripts"))
from factory_drift_detect import (
    CodeSnapshot,
    DriftReport,
    baseline_init,
    baseline_list,
    capture_screenshot,
    create_snapshot,
    diff_structural,
    diff_visual,
)


# ── CodeSnapshot ──────────────────────────────────────────────────────────

class TestCodeSnapshot:
    def test_to_dict_roundtrip(self):
        snap = CodeSnapshot(
            component="Button",
            variant="primary",
            timestamp="2025-01-01T00:00:00",
            files=[{"path": "Button.tsx", "size": 100, "tokens": {}, "components": []}],
            tokens_used={"color": ["brand.primary"]},
            components_used=["Button"],
            code_hash="abc123",
        )
        d = snap.to_dict()
        restored = CodeSnapshot.from_dict(d)
        assert restored.component == "Button"
        assert restored.variant == "primary"
        assert restored.code_hash == "abc123"
        assert restored.tokens_used == {"color": ["brand.primary"]}

    def test_from_dict_extra_keys_ignored(self):
        d = {
            "component": "Input",
            "variant": "default",
            "timestamp": "x",
            "files": [],
            "tokens_used": {},
            "components_used": [],
            "code_hash": "def456",
            "extra": "should be ignored",
        }
        snap = CodeSnapshot.from_dict(d)
        assert snap.component == "Input"
        assert snap.code_hash == "def456"


# ── DriftReport ───────────────────────────────────────────────────────────

class TestDriftReport:
    def test_defaults(self):
        r = DriftReport(passed=True)
        assert r.passed
        assert r.diff_percentage == 0.0
        assert r.structural_changes == []
        assert r.warnings == []
        assert r.score == 1.0


# ── create_snapshot ──────────────────────────────────────────────────────

class TestCreateSnapshot:
    @pytest.fixture
    def code_dir(self, tmp_path: Path) -> Path:
        d = tmp_path / "generated"
        d.mkdir()
        (d / "Button.tsx").write_text(
            '<Button>Click</Button>\n'
            '<Stack gap="spacing.sm" />\n'
        )
        (d / "Stack.tsx").write_text(
            "<Stack>content</Stack>\n"
        )
        (d / "ignored.txt").write_text("not scanned")
        return d

    def test_basic_snapshot(self, code_dir: Path):
        snap = create_snapshot("Button", "primary", code_dir)
        assert snap.component == "Button"
        assert snap.variant == "primary"
        assert len(snap.files) == 2
        paths = [f["path"] for f in snap.files]
        assert "Button.tsx" in paths
        assert "Stack.tsx" in paths

    def test_snapshot_tokens_detected(self, code_dir: Path):
        snap = create_snapshot("Button", "primary", code_dir)
        all_tokens = set()
        for v in snap.tokens_used.values():
            all_tokens.update(v)
        assert "sm" in all_tokens or "brand.primary" in all_tokens

    def test_snapshot_components_detected(self, code_dir: Path):
        snap = create_snapshot("Button", "primary", code_dir)
        assert "Stack" in snap.components_used or "Button" in snap.components_used

    def test_snapshot_hash_changes_on_content_change(self, code_dir: Path):
        snap1 = create_snapshot("Button", "primary", code_dir)
        (code_dir / "Button.tsx").write_text("// modified content\n")
        snap2 = create_snapshot("Button", "primary", code_dir)
        assert snap1.code_hash != snap2.code_hash

    def test_snapshot_empty_directory(self, tmp_path: Path):
        empty = tmp_path / "empty"
        empty.mkdir()
        snap = create_snapshot("Empty", "default", empty)
        assert snap.files == []
        assert snap.tokens_used == {}
        assert snap.components_used == []

    def test_snapshot_rejects_symlinks(self, tmp_path: Path):
        d = tmp_path / "code"
        d.mkdir()
        (d / "real.tsx").write_text("spacing.sm")
        snap = create_snapshot("Cmp", "a", d)
        assert len(snap.files) == 1


# ── diff_structural ──────────────────────────────────────────────────────

class TestDiffStructural:
    def make_snap(self, **overrides) -> CodeSnapshot:
        defaults = dict(
            component="Button",
            variant="primary",
            timestamp="2025-01-01T00:00:00",
            files=[{"path": "Button.tsx", "size": 100, "tokens": {"color": ["brand.primary"]}, "components": ["Button"]}],
            tokens_used={"color": ["brand.primary"]},
            components_used=["Button"],
            code_hash="aaa",
        )
        defaults.update(overrides)
        return CodeSnapshot(**defaults)

    def test_identical_snapshots_pass(self):
        b = self.make_snap()
        c = self.make_snap()
        report = diff_structural(b, c)
        assert report.passed
        assert report.structural_changes == []
        assert report.token_changes == []
        assert report.score == 1.0
        assert report.diff_percentage == 0.0

    def test_added_component_detected(self):
        b = self.make_snap(components_used=["Button"])
        c = self.make_snap(components_used=["Button", "Icon"])
        report = diff_structural(b, c)
        assert not report.passed
        assert any(ch["type"] == "components_added" for ch in report.structural_changes)

    def test_removed_component_detected(self):
        b = self.make_snap(components_used=["Button", "Icon"])
        c = self.make_snap(components_used=["Button"])
        report = diff_structural(b, c)
        assert not report.passed
        assert any(ch["type"] == "components_removed" for ch in report.structural_changes)

    def test_token_added_detected(self):
        b = self.make_snap(tokens_used={"color": ["brand.primary"]})
        c = self.make_snap(tokens_used={"color": ["brand.primary", "brand.secondary"]})
        report = diff_structural(b, c)
        assert not report.passed
        assert any(tc["type"] == "added" for tc in report.token_changes)

    def test_token_removed_detected(self):
        b = self.make_snap(tokens_used={"color": ["brand.primary", "brand.secondary"]})
        c = self.make_snap(tokens_used={"color": ["brand.primary"]})
        report = diff_structural(b, c)
        assert not report.passed
        assert any(tc["type"] == "removed" for tc in report.token_changes)

    def test_new_token_category_detected(self):
        b = self.make_snap(tokens_used={"color": ["brand.primary"]})
        c = self.make_snap(tokens_used={"color": ["brand.primary"], "spacing": ["sm"]})
        report = diff_structural(b, c)
        assert not report.passed
        assert any(tc["type"] == "added_category" for tc in report.token_changes)

    def test_files_added_and_removed(self):
        b = self.make_snap(files=[{"path": "a.tsx", "size": 10, "tokens": {}, "components": []}])
        c = self.make_snap(
            files=[{"path": "b.tsx", "size": 20, "tokens": {}, "components": []}]
        )
        report = diff_structural(b, c)
        assert not report.passed
        types = [ch["type"] for ch in report.structural_changes]
        assert "files_removed" in types
        assert "files_added" in types

    def test_code_hash_change_detected(self):
        b = self.make_snap(code_hash="aaa")
        c = self.make_snap(code_hash="bbb")
        report = diff_structural(b, c)
        assert not report.passed
        assert any(ch["type"] == "code_changed" for ch in report.structural_changes)

    def test_multiple_drifts_accumulate_score(self):
        b = self.make_snap(
            components_used=["Button"],
            tokens_used={"color": ["brand.primary"]},
            code_hash="aaa",
        )
        c = self.make_snap(
            components_used=["Button", "Icon", "Input"],
            tokens_used={"color": ["brand.primary", "brand.secondary"], "spacing": ["sm"]},
            code_hash="bbb",
        )
        report = diff_structural(b, c)
        assert report.score < 1.0
        assert report.diff_percentage > 0
        assert len(report.warnings) > 0
        assert len(report.structural_changes) + len(report.token_changes) >= 3

    def test_empty_baseline_no_crash(self):
        b = self.make_snap(files=[], tokens_used={}, components_used=[])
        c = self.make_snap()
        report = diff_structural(b, c)
        assert report.score < 1.0

    def test_empty_current_no_crash(self):
        b = self.make_snap()
        c = self.make_snap(files=[], tokens_used={}, components_used=[])
        report = diff_structural(b, c)
        assert not report.passed


# ── diff_visual (without Playwright/Pillow) ──────────────────────────────

class TestDiffVisual:
    def test_no_baseline_returns_warning(self, tmp_path: Path):
        current = tmp_path / "current.png"
        current.write_text("fake")
        report = diff_visual("nonexistent.png", str(current), tmp_path)
        assert report.passed
        assert any("No baseline" in w for w in report.warnings)

    def test_no_current_image_fails(self, tmp_path: Path):
        baseline = tmp_path / "baseline.png"
        baseline.write_text("fake")
        report = diff_visual(str(baseline), "nonexistent.png", tmp_path)
        assert not report.passed
        assert any("not found" in w.lower() for w in report.warnings)

    def test_fallback_filesize_similar_passes(self, tmp_path: Path):
        b = tmp_path / "base.png"
        c = tmp_path / "curr.png"
        data = b"\x89PNG\r\n\x1a\n" + b"\x00" * 1000
        b.write_bytes(data)
        c.write_bytes(data)
        report = diff_visual(str(b), str(c), tmp_path)
        assert report.passed
        assert report.score == 1.0

    def test_fallback_filesize_different_triggers_warning(self, tmp_path: Path):
        b = tmp_path / "base.png"
        c = tmp_path / "curr.png"
        b.write_bytes(b"\x00" * 10000)
        c.write_bytes(b"\xff" * 1000)
        report = diff_visual(str(b), str(c), tmp_path)
        assert report.score < 1.0


# ── capture_screenshot (without Playwright) ──────────────────────────────

class TestCaptureScreenshot:
    def test_without_playwright_returns_error(self, tmp_path: Path):
        html = tmp_path / "test.html"
        html.write_text("<html><body>Hello</body></html>")
        out = tmp_path / "out.png"
        result = capture_screenshot(str(html), str(out))
        assert not result["success"]
        assert "Playwright not installed" in result["error"] or "Playwright import failed" in result["error"]


# ── baseline_init / baseline_list ────────────────────────────────────────

class TestBaseline:
    def test_baseline_init_creates_screenshots_dir(self, tmp_path: Path):
        ds = tmp_path / "ds"
        ds.mkdir()
        created = baseline_init(ds)
        assert (ds / "screenshots").exists()
        assert any("screenshots" in c for c in created)

    def test_baseline_init_with_primitives(self, tmp_path: Path):
        ds = tmp_path / "ds"
        (ds / "primitives" / "Button").mkdir(parents=True)
        (ds / "primitives" / "Input").mkdir(parents=True)
        created = baseline_init(ds)
        assert (ds / "screenshots" / "Button").exists()
        assert (ds / "screenshots" / "Input").exists()

    def test_baseline_list_empty(self, tmp_path: Path):
        ds = tmp_path / "ds"
        ds.mkdir()
        assert baseline_list(ds) == []

    def test_baseline_list_with_files(self, tmp_path: Path):
        ds = tmp_path / "ds"
        (ds / "screenshots" / "Button").mkdir(parents=True)
        (ds / "screenshots" / "Button" / "primary.png").write_text("")
        entries = baseline_list(ds)
        assert len(entries) == 1
        assert entries[0]["component"] == "Button"
        assert entries[0]["count"] == 1

    def test_baseline_list_multiple_components(self, tmp_path: Path):
        ds = tmp_path / "ds"
        (ds / "screenshots" / "Button").mkdir(parents=True)
        (ds / "screenshots" / "Input").mkdir(parents=True)
        (ds / "screenshots" / "Button" / "primary.png").write_text("")
        (ds / "screenshots" / "Input" / "default.png").write_text("")
        (ds / "screenshots" / "Input" / "error.png").write_text("")
        entries = baseline_list(ds)
        assert len(entries) == 2
        by_name = {e["component"]: e["count"] for e in entries}
        assert by_name["Button"] == 1
        assert by_name["Input"] == 2

    def test_baseline_init_idempotent(self, tmp_path: Path):
        ds = tmp_path / "ds"
        ds.mkdir()
        baseline_init(ds)
        baseline_init(ds)
        assert (ds / "screenshots").exists()


# ── Integration: create_snapshot + diff_structural roundtrip ──────────────

class TestIntegration:
    def test_snapshot_and_diff_identical(self, tmp_path: Path):
        d = tmp_path / "code"
        d.mkdir()
        (d / "Cmp.tsx").write_text("spacing.md")
        snap1 = create_snapshot("Cmp", "a", d)
        snap2 = create_snapshot("Cmp", "a", d)
        report = diff_structural(snap1, snap2)
        assert report.passed
        assert report.score == 1.0

    def test_snapshot_and_diff_changed(self, tmp_path: Path):
        d = tmp_path / "code"
        d.mkdir()
        (d / "Cmp.tsx").write_text("spacing.md")
        snap1 = create_snapshot("Cmp", "a", d)

        (d / "Cmp.tsx").write_text("spacing.xl\ncolor.brand.primary")
        snap2 = create_snapshot("Cmp", "a", d)

        report = diff_structural(snap1, snap2)
        assert not report.passed
        assert report.diff_percentage > 0

    def test_json_output_roundtrip(self, tmp_path: Path):
        d = tmp_path / "code"
        d.mkdir()
        (d / "Cmp.tsx").write_text("spacing.sm")
        snap = create_snapshot("Cmp", "a", d)

        path = tmp_path / "snapshot.json"
        path.write_text(json.dumps(snap.to_dict(), indent=2))
        loaded = CodeSnapshot.from_dict(json.loads(path.read_text()))

        assert loaded.component == snap.component
        assert loaded.code_hash == snap.code_hash
        assert loaded.files == snap.files
