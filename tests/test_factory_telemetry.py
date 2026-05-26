from __future__ import annotations

import csv
import io
import json
import os
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest


SCRIPTS = Path(__file__).resolve().parent.parent / "aidlc-scripts"
TELEMETRY_PY = SCRIPTS / "factory_telemetry.py"


def _run(args, env=None):
    return subprocess.run(
        [sys.executable, str(TELEMETRY_PY), *args],
        capture_output=True, text=True, env=env or {**os.environ},
    )


# ---------------------------------------------------------------------------
# hot-path
# ---------------------------------------------------------------------------


SAMPLE_MD = textwrap.dedent("""\
    # Title

    Some preamble.

    ## Hot Section
    Body of hot section. Discusses things like factory_run.py emit and substep 6.
    The shared-primitives Step 8 protocol applies. Wall-clocking is forbidden.

    ## FAST_PATH — TINY tier execution
    Cold path. Only runs for TINY-tier classifications.
    Discusses TINY tier and minimal scaffolding.

    ## shared-primitives loop
    Always executes on every spawn. This section is "always" reach.

    ## Another Hot Section
    Repeats the same factory_run.py emit FIRST pattern with Capture `ts_x` and
    a canonical sequence reference. substep 6 applies.
""")


def test_hot_path_smoke(tmp_path: Path):
    md = tmp_path / "sample.md"
    md.write_text(SAMPLE_MD)
    r = _run(["hot-path", str(md)])
    assert r.returncode == 0, r.stderr
    out = r.stdout
    assert "HOT-PATH REPORT" in out
    assert "REACH BREAKDOWN" in out
    assert "FAST_PATH" in out


def test_hot_path_classifies_cold_path_section(tmp_path: Path):
    md = tmp_path / "sample.md"
    md.write_text(SAMPLE_MD)
    json_out = tmp_path / "report.json"
    r = _run(["hot-path", str(md), "--json", str(json_out)])
    assert r.returncode == 0, r.stderr
    report = json.loads(json_out.read_text())
    by_title = {s["title"]: s for s in report["sections"]}
    # FAST_PATH heading must be classified as cold
    fast = next(s for t, s in by_title.items() if "FAST_PATH" in t)
    assert fast["reach"] == "cold"
    # "shared-primitives loop" must be classified as always
    shared = next(s for t, s in by_title.items() if "shared" in t.lower())
    assert shared["reach"] == "always"


def test_hot_path_counts_audit_phrases(tmp_path: Path):
    md = tmp_path / "sample.md"
    md.write_text(SAMPLE_MD)
    json_out = tmp_path / "report.json"
    r = _run(["hot-path", str(md), "--json", str(json_out)])
    assert r.returncode == 0, r.stderr
    report = json.loads(json_out.read_text())
    # The two hot sections both restate audit-protocol phrases
    hot_sections = [s for s in report["sections"] if s["reach"] == "hot"]
    total_hits = sum(s["audit_phrase_hit_total"] for s in hot_sections)
    assert total_hits >= 4, f"expected ≥4 phrase hits in hot sections, got {total_hits}"


def test_hot_path_redundancy_score_in_range(tmp_path: Path):
    md = tmp_path / "sample.md"
    md.write_text(SAMPLE_MD)
    json_out = tmp_path / "report.json"
    r = _run(["hot-path", str(md), "--json", str(json_out)])
    assert r.returncode == 0, r.stderr
    report = json.loads(json_out.read_text())
    for s in report["sections"]:
        assert 0.0 <= s["redundancy"] <= 1.0


def test_hot_path_missing_file_exits_2(tmp_path: Path):
    r = _run(["hot-path", str(tmp_path / "does-not-exist.md")])
    assert r.returncode == 2
    assert "not found" in r.stderr.lower()


def test_hot_path_ignores_h2_inside_fenced_code_blocks(tmp_path: Path):
    """H2 lines that appear inside ``` fences are example output, not real headings."""
    md = tmp_path / "fenced.md"
    md.write_text(textwrap.dedent("""\
        ## Real Section
        Some prose.

        Example audit block:
        ```
        ## <ts> INCEPTION - WORKSPACE SCOUT START
        - [Orchestrator] spawned ...
        ```

        More prose still part of Real Section.

        ## Second Real Section
        Body.
    """))
    json_out = tmp_path / "report.json"
    r = _run(["hot-path", str(md), "--json", str(json_out)])
    assert r.returncode == 0, r.stderr
    report = json.loads(json_out.read_text())
    titles = [s["title"] for s in report["sections"]]
    assert "<ts> INCEPTION - WORKSPACE SCOUT START" not in titles
    assert "Real Section" in titles
    assert "Second Real Section" in titles


def test_hot_path_boilerplate_zero_on_current_orchestrator(tmp_path: Path):
    """The refactored orchestrator.md must have 0 boilerplate phrase hits."""
    md = SCRIPTS.parent / ".claude" / "agents" / "orchestrator.md"
    if not md.exists():
        pytest.skip("orchestrator.md not found")
    json_out = tmp_path / "report.json"
    r = _run(["hot-path", str(md), "--json", str(json_out)])
    assert r.returncode == 0, r.stderr
    report = json.loads(json_out.read_text())
    boiler_total = sum(s["boilerplate_hit_total"] for s in report["sections"])
    assert boiler_total == 0, f"expected 0 boilerplate hits, got {boiler_total}"


def test_hot_path_pointer_count_nonzero_on_current_orchestrator(tmp_path: Path):
    """The orchestrator.md kernel must have ≥3 pointer references to runtime files."""
    md = SCRIPTS.parent / ".claude" / "agents" / "orchestrator.md"
    if not md.exists():
        pytest.skip("orchestrator.md not found")
    json_out = tmp_path / "report.json"
    r = _run(["hot-path", str(md), "--json", str(json_out)])
    assert r.returncode == 0, r.stderr
    report = json.loads(json_out.read_text())
    ptr_total = sum(s["pointer_hit_total"] for s in report["sections"])
    assert ptr_total >= 3, f"expected ≥3 pointer references, got {ptr_total}"


def test_hot_path_no_h2_treats_whole_file_as_preamble(tmp_path: Path):
    md = tmp_path / "flat.md"
    md.write_text("Just some content with no H2 headings at all.\n")
    json_out = tmp_path / "report.json"
    r = _run(["hot-path", str(md), "--json", str(json_out)])
    assert r.returncode == 0, r.stderr
    report = json.loads(json_out.read_text())
    assert report["section_count"] == 1
    assert report["sections"][0]["title"] == "PREAMBLE"


# ---------------------------------------------------------------------------
# count-tokens
# ---------------------------------------------------------------------------


@pytest.fixture
def fake_run(tmp_path: Path, monkeypatch):
    """Build a minimal AIDLC_ROOT with one run that has a timeline + handoff."""
    root = tmp_path / "repo"
    runs = root / ".aidlc-orchestrator" / "runs" / "r1"
    handoffs = runs / "handoffs"
    handoffs.mkdir(parents=True)
    agents = root / ".claude" / "agents"
    stage = agents / "stage"
    stage.mkdir(parents=True)
    (agents / "orchestrator.md").write_text("# orchestrator\n" * 50)
    (stage / "workspace-scout.md").write_text("# workspace-scout agent prompt\n" * 20)
    (stage / "code-generator.md").write_text("# code-generator agent prompt\n" * 30)

    timeline = runs / "timeline.jsonl"
    timeline.write_text(
        json.dumps({"ts": "2026-05-13T10:00:00+00:00", "evt": "spawn_start",
                    "run_id": "r1", "stage": "workspace-scout",
                    "tokens_estimate": 50000}) + "\n"
        + json.dumps({"ts": "2026-05-13T10:01:30+00:00", "evt": "spawn_end",
                      "run_id": "r1", "stage": "workspace-scout",
                      "status": "complete", "tokens_in": 12000,
                      "tokens_out": 4000, "wall_min": 1.5}) + "\n"
        + json.dumps({"ts": "2026-05-13T10:02:00+00:00", "evt": "spawn_start",
                      "run_id": "r1", "stage": "code-generator"}) + "\n"
        + json.dumps({"ts": "2026-05-13T10:08:00+00:00", "evt": "spawn_end",
                      "run_id": "r1", "stage": "code-generator",
                      "status": "complete", "tokens_in": 80000,
                      "tokens_out": 25000, "wall_min": 6.0}) + "\n"
    )

    (handoffs / "workspace-scout.input.yaml").write_text("a: 1\n" * 10)
    (handoffs / "code-generator.input.yaml").write_text("a: 1\n" * 30)

    monkeypatch.setenv("AIDLC_ROOT", str(root))
    return root


def test_count_tokens_csv_shape(fake_run: Path):
    r = _run(["count-tokens", "r1"])
    assert r.returncode == 0, r.stderr
    reader = csv.DictReader(io.StringIO(r.stdout))
    rows = list(reader)
    assert {row["stage"] for row in rows} == {"workspace-scout", "code-generator"}
    assert reader.fieldnames == [
        "stage", "tokens_in", "tokens_out", "wall_min",
        "kernel_bytes", "handoff_bytes", "prompt_bytes",
    ]


def test_count_tokens_aggregates_correctly(fake_run: Path):
    r = _run(["count-tokens", "r1"])
    assert r.returncode == 0, r.stderr
    reader = csv.DictReader(io.StringIO(r.stdout))
    rows = {row["stage"]: row for row in reader}
    ws = rows["workspace-scout"]
    assert int(ws["tokens_in"]) == 12000
    assert int(ws["tokens_out"]) == 4000
    assert float(ws["wall_min"]) == 1.5
    assert int(ws["handoff_bytes"]) > 0
    assert int(ws["prompt_bytes"]) > 0
    assert int(ws["kernel_bytes"]) > 0
    cg = rows["code-generator"]
    assert int(cg["tokens_in"]) == 80000
    assert int(cg["tokens_out"]) == 25000


def test_count_tokens_out_path(fake_run: Path, tmp_path: Path):
    out = tmp_path / "telemetry.csv"
    r = _run(["count-tokens", "r1", "--out", str(out)])
    assert r.returncode == 0, r.stderr
    assert out.exists()
    text = out.read_text()
    assert "stage,tokens_in,tokens_out" in text
    assert "workspace-scout" in text


def test_count_tokens_missing_run_exits_2(tmp_path: Path, monkeypatch):
    root = tmp_path / "empty"
    root.mkdir()
    monkeypatch.setenv("AIDLC_ROOT", str(root))
    r = _run(["count-tokens", "missing"])
    assert r.returncode == 2
    assert "run not found" in r.stderr.lower()


def test_count_tokens_invalid_run_id_exits_2(fake_run: Path):
    r = _run(["count-tokens", "../escape"])
    assert r.returncode == 2
    assert "invalid run_id" in r.stderr.lower()


def test_count_tokens_handles_malformed_timeline_line(tmp_path: Path, monkeypatch):
    root = tmp_path / "repo"
    runs = root / ".aidlc-orchestrator" / "runs" / "r2"
    (runs / "handoffs").mkdir(parents=True)
    (root / ".claude" / "agents" / "stage").mkdir(parents=True)
    (runs / "timeline.jsonl").write_text(
        "this is not json\n"
        + json.dumps({"ts": "2026-05-13T10:00:00+00:00", "evt": "spawn_start",
                      "run_id": "r2", "stage": "workspace-scout"}) + "\n"
        + json.dumps({"ts": "2026-05-13T10:00:30+00:00", "evt": "spawn_end",
                      "run_id": "r2", "stage": "workspace-scout",
                      "tokens_in": 1000, "tokens_out": 500}) + "\n"
    )
    monkeypatch.setenv("AIDLC_ROOT", str(root))
    r = _run(["count-tokens", "r2"])
    assert r.returncode == 0, r.stderr
    assert "workspace-scout" in r.stdout


def test_count_tokens_tokens_fallback_to_single_counter(tmp_path: Path, monkeypatch):
    """If spawn_end emits only `tokens` (no tokens_in/out), it counts as tokens_out."""
    root = tmp_path / "repo"
    runs = root / ".aidlc-orchestrator" / "runs" / "r3"
    (runs / "handoffs").mkdir(parents=True)
    (root / ".claude" / "agents" / "stage").mkdir(parents=True)
    (runs / "timeline.jsonl").write_text(
        json.dumps({"ts": "2026-05-13T10:00:00+00:00", "evt": "spawn_start",
                    "run_id": "r3", "stage": "reviewer-code"}) + "\n"
        + json.dumps({"ts": "2026-05-13T10:00:30+00:00", "evt": "spawn_end",
                      "run_id": "r3", "stage": "reviewer-code",
                      "tokens": 7777}) + "\n"
    )
    monkeypatch.setenv("AIDLC_ROOT", str(root))
    r = _run(["count-tokens", "r3"])
    assert r.returncode == 0, r.stderr
    reader = csv.DictReader(io.StringIO(r.stdout))
    rows = {row["stage"]: row for row in reader}
    assert int(rows["reviewer-code"]["tokens_out"]) == 7777
    assert int(rows["reviewer-code"]["tokens_in"]) == 0


# ---------------------------------------------------------------------------
# multi-repo fixtures + discover / aggregate / report
# ---------------------------------------------------------------------------


def _write_manifest(path: Path, **fields):
    import yaml as _yaml
    base = {
        "run_id": path.name,
        "started_at": "2026-05-13T10:00:00+00:00",
        "user_request": "test",
        "project_slug": path.parents[2].name,
        "current_stage": "complete",
        "completed_stages": [],
        "skipped_stages": [],
        "failed_stages": [],
        "units": [],
    }
    base.update(fields)
    path.write_text(_yaml.safe_dump(base, sort_keys=False))


def _write_timeline(path: Path, spawns: list[tuple[str, int, float]]):
    """spawns: list of (stage, tokens, wall_min) -> emits start+end pair each."""
    lines = []
    t_idx = 0
    for stage, tokens, wall in spawns:
        lines.append(json.dumps({
            "ts": f"2026-05-13T10:{t_idx:02d}:00+00:00", "evt": "spawn_start",
            "run_id": path.parent.name, "stage": stage,
        }))
        t_idx += 1
        lines.append(json.dumps({
            "ts": f"2026-05-13T10:{t_idx:02d}:00+00:00", "evt": "spawn_end",
            "run_id": path.parent.name, "stage": stage,
            "status": "complete", "tokens": tokens, "wall_min": wall,
        }))
        t_idx += 1
    path.write_text("\n".join(lines) + "\n")


@pytest.fixture
def multi_repo(tmp_path: Path):
    """Build three sibling repos with one run each at different tiers."""
    parent = tmp_path / "workspaces"
    parent.mkdir()
    out: dict[str, Path] = {}
    for slug, run_id, tier_fields, spawns in [
        ("repoA", "r-small-1", {"complexity_tier": "SMALL"},
         [("workspace-scout", 30_000, 3.0), ("requirements-analyst", 120_000, 5.0)]),
        ("repoB", "r-medium-1", {"complexity_tier": "MEDIUM"},
         [("workspace-scout", 35_000, 3.5), ("requirements-analyst", 130_000, 5.2),
          ("workflow-planner", 90_000, 4.0), ("code-generator", 400_000, 12.0)]),
        ("repoC", "r-large-1", {"complexity_tier": "LARGE", "units": [{"id": "auth"}, {"id": "crud"}, {"id": "audit"}]},
         [("workspace-scout", 40_000, 3.8), ("requirements-analyst", 200_000, 7.0),
          ("workflow-planner", 110_000, 4.5), ("code-generator", 700_000, 18.0),
          ("build-test-agent", 150_000, 6.0)]),
    ]:
        repo = parent / slug
        runs_dir = repo / ".aidlc-orchestrator" / "runs" / run_id
        (runs_dir / "handoffs").mkdir(parents=True)
        (repo / ".claude" / "agents" / "stage").mkdir(parents=True)
        (repo / ".claude" / "agents" / "orchestrator.md").write_text("# orch\n" * 100)
        _write_manifest(runs_dir / "manifest.yaml", run_id=run_id, project_slug=slug, **tier_fields)
        _write_timeline(runs_dir / "timeline.jsonl", spawns)
        out[slug] = repo
    return out


def test_discover_one_root(multi_repo, tmp_path: Path):
    out_json = tmp_path / "disc.json"
    r = _run(["discover", "--root", str(multi_repo["repoA"]),
              "--json", str(out_json)])
    assert r.returncode == 0, r.stderr
    runs = json.loads(out_json.read_text())
    assert len(runs) == 1
    assert runs[0]["run_id"] == "r-small-1"
    assert runs[0]["tier"] == "SMALL"


def test_discover_scan_siblings(multi_repo, tmp_path: Path):
    out_json = tmp_path / "disc.json"
    r = _run(["discover", "--root", str(multi_repo["repoA"]),
              "--scan-siblings", "--json", str(out_json)])
    assert r.returncode == 0, r.stderr
    runs = json.loads(out_json.read_text())
    tiers = {run["tier"] for run in runs}
    assert tiers == {"SMALL", "MEDIUM", "LARGE"}
    assert len(runs) == 3


def test_discover_no_runs_in_root(tmp_path: Path):
    empty = tmp_path / "empty"
    empty.mkdir()
    r = _run(["discover", "--root", str(empty)])
    assert r.returncode == 0
    assert "DISCOVERED 0 run" in r.stdout


def test_discover_derives_tier_from_skipped_stages(tmp_path: Path):
    """When complexity_tier is absent, tier comes from skip_stages heuristics."""
    repo = tmp_path / "repo"
    run = repo / ".aidlc-orchestrator" / "runs" / "r1"
    (run / "handoffs").mkdir(parents=True)
    _write_manifest(run / "manifest.yaml", run_id="r1",
                    skipped_stages=["unit-decomposer", "story-writer"])
    (run / "timeline.jsonl").write_text("")
    r = _run(["discover", "--root", str(repo)])
    assert r.returncode == 0
    assert "SMALL" in r.stdout


def test_aggregate_groups_by_tier(multi_repo, tmp_path: Path):
    out_json = tmp_path / "agg.json"
    r = _run(["aggregate", "--auto-discover",
              "--root", str(multi_repo["repoA"]),
              "--scan-siblings",
              "--json", str(out_json)])
    assert r.returncode == 0, r.stderr
    agg = json.loads(out_json.read_text())
    assert set(agg.keys()) == {"SMALL", "MEDIUM", "LARGE"}
    assert agg["SMALL"]["run_count"] == 1
    # SMALL total tokens = 30,000 + 120,000 = 150,000
    assert agg["SMALL"]["total_tokens"]["mean"] == 150000
    # workspace-scout in SMALL
    assert agg["SMALL"]["per_stage"]["workspace-scout"]["tokens"]["mean"] == 30000


def test_aggregate_explicit_runs(multi_repo, tmp_path: Path):
    a = multi_repo["repoA"] / ".aidlc-orchestrator" / "runs" / "r-small-1"
    b = multi_repo["repoB"] / ".aidlc-orchestrator" / "runs" / "r-medium-1"
    out_json = tmp_path / "agg.json"
    r = _run(["aggregate", "--run", str(a), "--run", str(b),
              "--json", str(out_json)])
    assert r.returncode == 0, r.stderr
    agg = json.loads(out_json.read_text())
    assert "SMALL" in agg
    assert "MEDIUM" in agg


def test_aggregate_no_args_exits_2(tmp_path: Path):
    r = _run(["aggregate"])
    assert r.returncode == 2
    assert "auto-discover" in r.stderr.lower() or "--run" in r.stderr


def test_report_writes_markdown(multi_repo, tmp_path: Path):
    out_md = tmp_path / "baseline.md"
    out_json = tmp_path / "baseline.json"
    r = _run([
        "report",
        "--repo-root", str(multi_repo["repoA"]),
        "--root", str(multi_repo["repoA"]),
        "--scan-siblings", "--auto-discover",
        "--baseline", str(out_md),
        "--json", str(out_json),
    ])
    assert r.returncode == 0, r.stderr
    assert out_md.exists()
    text = out_md.read_text()
    assert "AIDLC Orchestrator -- Refactor Baseline" in text
    assert "BASELINE_KERNEL_BYTES" in text
    assert "BASELINE_SMALL_TOKENS_MEAN" in text
    assert "BASELINE_MEDIUM_TOKENS_MEAN" in text
    assert "BASELINE_LARGE_TOKENS_MEAN" in text
    # JSON snapshot is also produced
    snap = json.loads(out_json.read_text())
    assert "hot_path" in snap
    assert "discovered_runs" in snap
    assert "aggregate" in snap


def test_report_handles_no_runs(tmp_path: Path):
    repo = tmp_path / "empty"
    (repo / ".claude" / "agents").mkdir(parents=True)
    (repo / ".claude" / "agents" / "orchestrator.md").write_text("# orch\n")
    out_md = tmp_path / "baseline.md"
    r = _run([
        "report", "--repo-root", str(repo),
        "--root", str(repo), "--auto-discover",
        "--baseline", str(out_md),
    ])
    assert r.returncode == 0, r.stderr
    assert out_md.exists()
    text = out_md.read_text()
    assert "No runs discovered" in text


def test_count_tokens_repo_root_override(multi_repo, tmp_path: Path):
    """--repo-root lets you read a run from a different repo than AIDLC_ROOT."""
    r = _run([
        "count-tokens", "r-medium-1",
        "--repo-root", str(multi_repo["repoB"]),
    ])
    assert r.returncode == 0, r.stderr
    reader = csv.DictReader(io.StringIO(r.stdout))
    stages = {row["stage"] for row in reader}
    assert "code-generator" in stages
    assert "workflow-planner" in stages
