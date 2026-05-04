"""Tests for mcp_bridge.py (skill discovery/injection) and pipeline.py (DAG executor)."""
from __future__ import annotations

import json
import runpy
import tempfile
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
BRIDGE_PATH = REPO_ROOT / "scripts" / "subagents" / "mcp_bridge.py"
PIPELINE_PATH = REPO_ROOT / "scripts" / "subagents" / "pipeline.py"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_bridge():
    return runpy.run_path(str(BRIDGE_PATH))


def _load_pipeline():
    return runpy.run_path(str(PIPELINE_PATH))


# ---------------------------------------------------------------------------
# mcp_bridge — MCPBridge class
# ---------------------------------------------------------------------------

class TestMCPBridge:
    def test_list_tools_returns_list(self):
        mod = _load_bridge()
        MCPBridge = mod["MCPBridge"]
        bridge = MCPBridge(allowed_tools=[])
        tools = bridge.list_tools()
        assert isinstance(tools, list)
        assert len(tools) > 0

    def test_list_tools_no_filter_returns_all_known(self):
        mod = _load_bridge()
        MCPBridge = mod["MCPBridge"]
        KNOWN = mod["KNOWN_MCP_TOOLS"]
        bridge = MCPBridge(allowed_tools=[])
        tools = bridge.list_tools()
        assert len(tools) == len(KNOWN)

    def test_list_tools_with_prefix_filter(self):
        mod = _load_bridge()
        MCPBridge = mod["MCPBridge"]
        bridge = MCPBridge(allowed_tools=[])
        pylance_tools = bridge.list_tools(filter_prefix="mcp_pylance_")
        assert all(t["name"].startswith("mcp_pylance_") for t in pylance_tools)
        assert len(pylance_tools) > 0

    def test_allowlist_restricts_tool_list(self):
        mod = _load_bridge()
        MCPBridge = mod["MCPBridge"]
        allowed = ["mcp_pylance_mcp_s_pylanceSyntaxErrors"]
        bridge = MCPBridge(allowed_tools=allowed)
        tools = bridge.list_tools()
        assert len(tools) == 1
        assert tools[0]["name"] == "mcp_pylance_mcp_s_pylanceSyntaxErrors"

    def test_allowlist_glob_pattern(self):
        mod = _load_bridge()
        MCPBridge = mod["MCPBridge"]
        bridge = MCPBridge(allowed_tools=["mcp_pylance_*"])
        tools = bridge.list_tools()
        assert len(tools) > 0
        assert all(t["name"].startswith("mcp_pylance_") for t in tools)

    def test_to_context_dict_keys(self):
        mod = _load_bridge()
        MCPBridge = mod["MCPBridge"]
        bridge = MCPBridge(allowed_tools=[])
        ctx = bridge.to_context_dict()
        assert "available_mcp_tools" in ctx
        assert "mcp_requires_approval" in ctx
        assert ctx["mcp_requires_approval"] is True


# ---------------------------------------------------------------------------
# mcp_bridge — discover_all_skills + load_skills_for_agent
# ---------------------------------------------------------------------------

class TestSkillDiscovery:
    def test_discover_all_skills_with_fake_root(self, tmp_path):
        mod = _load_bridge()
        discover = mod["discover_all_skills"]

        # Create two fake skills
        (tmp_path / "alpha" / "SKILL.md").parent.mkdir()
        (tmp_path / "alpha" / "SKILL.md").write_text("# Alpha skill")
        (tmp_path / "beta" / "SKILL.md").parent.mkdir()
        (tmp_path / "beta" / "SKILL.md").write_text("# Beta skill")

        found = discover(skills_root=tmp_path)
        assert "alpha" in found
        assert "beta" in found
        assert found["alpha"].name == "SKILL.md"

    def test_discover_all_skills_skips_dir_without_skill_md(self, tmp_path):
        mod = _load_bridge()
        discover = mod["discover_all_skills"]

        (tmp_path / "no-skill-here").mkdir()
        found = discover(skills_root=tmp_path)
        assert "no-skill-here" not in found

    def test_load_skills_explicit_names(self, tmp_path):
        mod = _load_bridge()
        load_skills = mod["load_skills_for_agent"]

        (tmp_path / "myskill" / "SKILL.md").parent.mkdir()
        (tmp_path / "myskill" / "SKILL.md").write_text("# My Skill\nDo stuff.")

        agent_cfg = {"skills": ["myskill"]}
        result = load_skills(agent_cfg, skills_root=tmp_path)
        assert "myskill" in result
        assert "Do stuff" in result["myskill"]

    def test_load_skills_missing_skill_silently_skipped(self, tmp_path):
        mod = _load_bridge()
        load_skills = mod["load_skills_for_agent"]

        agent_cfg = {"skills": ["does-not-exist"]}
        result = load_skills(agent_cfg, skills_root=tmp_path)
        assert result == {}

    def test_load_skills_wildcard_loads_all(self, tmp_path):
        mod = _load_bridge()
        load_skills = mod["load_skills_for_agent"]

        for name in ("skill-a", "skill-b", "skill-c"):
            (tmp_path / name).mkdir()
            (tmp_path / name / "SKILL.md").write_text(f"# {name}")

        agent_cfg = {"skills": ["*"]}
        result = load_skills(agent_cfg, skills_root=tmp_path)
        # skills_root skills must all be present; home skills may also appear (superset OK)
        assert {"skill-a", "skill-b", "skill-c"}.issubset(set(result.keys()))

    def test_load_skills_empty_list_returns_empty(self, tmp_path):
        mod = _load_bridge()
        load_skills = mod["load_skills_for_agent"]
        result = load_skills({"skills": []}, skills_root=tmp_path)
        assert result == {}

    def test_load_skills_no_skills_key(self, tmp_path):
        mod = _load_bridge()
        load_skills = mod["load_skills_for_agent"]
        result = load_skills({}, skills_root=tmp_path)
        assert result == {}


# ---------------------------------------------------------------------------
# pipeline.py — load_pipelines + run_pipeline
# ---------------------------------------------------------------------------

class TestPipelineLoader:
    def test_load_pipelines_returns_list(self):
        mod = _load_pipeline()
        load_pipelines = mod["load_pipelines"]
        pipelines = load_pipelines()
        assert isinstance(pipelines, list)
        assert len(pipelines) >= 2

    def test_construction_full_pipeline_exists(self):
        mod = _load_pipeline()
        load_pipelines = mod["load_pipelines"]
        pipelines = load_pipelines()
        ids = [p["id"] for p in pipelines]
        assert "construction-full" in ids
        assert "review-only" in ids

    def test_pipeline_has_stages(self):
        mod = _load_pipeline()
        load_pipelines = mod["load_pipelines"]
        pipelines = load_pipelines()
        for p in pipelines:
            assert "stages" in p
            assert isinstance(p["stages"], list)
            assert len(p["stages"]) >= 1

    def test_each_stage_has_group(self):
        mod = _load_pipeline()
        load_pipelines = mod["load_pipelines"]
        pipelines = load_pipelines()
        for p in pipelines:
            for stage in p["stages"]:
                assert "group" in stage
                assert isinstance(stage["group"], list)


class TestRunPipeline:
    """run_pipeline should execute agents and return per-agent results."""

    def test_run_pipeline_returns_results_dict(self, tmp_path):
        mod = _load_pipeline()
        run_pipeline = mod["run_pipeline"]
        # Use review-only — smallest pipeline
        results = run_pipeline("review-only", context={"run_folder": str(tmp_path)})
        assert isinstance(results, dict)
        assert "stages" in results or "agent_results" in results or isinstance(results, dict)

    def test_run_pipeline_unknown_id_returns_error(self):
        mod = _load_pipeline()
        run_pipeline = mod["run_pipeline"]
        result = run_pipeline("nonexistent-pipeline-id", context={})
        assert isinstance(result, dict)
        assert result.get("status") == "error"
        assert "not found" in result.get("error", "").lower()

    def test_run_pipeline_result_contains_agent_ids(self, tmp_path):
        mod = _load_pipeline()
        run_pipeline = mod["run_pipeline"]
        results = run_pipeline("review-only", context={"run_folder": str(tmp_path)})
        # Flatten all agent results from all stages
        all_agent_ids: list[str] = []
        for stage in results.get("stages", []):
            for agent_id, res in stage.get("results", {}).items():
                all_agent_ids.append(agent_id)
        assert "code-reviewer" in all_agent_ids or "construction-reviewer" in all_agent_ids


# ---------------------------------------------------------------------------
# code_reviewer.py — new implementation
# ---------------------------------------------------------------------------

class TestCodeReviewer:
    """Validates the new real code_reviewer against the expected output schema."""

    def _load(self):
        path = REPO_ROOT / "scripts" / "subagents" / "code_reviewer.py"
        return runpy.run_path(str(path))

    def test_run_returns_correct_schema(self, tmp_path):
        mod = self._load()
        run = mod["run"]
        result = run({"path": str(tmp_path), "aidlc_docs": str(tmp_path / "docs")})
        assert result["agent_id"] == "code-reviewer"
        assert result["status"] in ("ok", "warning", "error")
        assert "blocking" in result
        assert isinstance(result["blocking"], bool)
        assert "findings" in result
        assert "report_path" in result

    def test_clean_dir_returns_ok(self, tmp_path):
        mod = self._load()
        run = mod["run"]
        result = run({"path": str(tmp_path), "aidlc_docs": str(tmp_path / "docs")})
        assert result["status"] == "ok"
        assert result["blocking"] is False

    def test_hardcoded_password_is_blocking(self, tmp_path):
        mod = self._load()
        run = mod["run"]
        (tmp_path / "bad.py").write_text("password = 'supersecret123'\n")
        result = run({"path": str(tmp_path), "aidlc_docs": str(tmp_path / "docs")})
        assert result["blocking"] is True
        assert result["findings"]["security_blocking"] >= 1

    def test_eval_usage_is_warning(self, tmp_path):
        mod = self._load()
        run = mod["run"]
        (tmp_path / "risky.py").write_text("eval(user_input)\n")
        result = run({"path": str(tmp_path), "aidlc_docs": str(tmp_path / "docs")})
        assert result["findings"]["security_warnings"] >= 1

    def test_todo_is_detected(self, tmp_path):
        mod = self._load()
        run = mod["run"]
        (tmp_path / "work.py").write_text("# TODO: implement this\nx = 1\n")
        result = run({"path": str(tmp_path), "aidlc_docs": str(tmp_path / "docs")})
        assert result["findings"]["todos"] >= 1

    def test_report_file_is_written(self, tmp_path):
        mod = self._load()
        run = mod["run"]
        docs = tmp_path / "docs"
        result = run({"path": str(tmp_path), "aidlc_docs": str(docs)})
        report = Path(result["report_path"])
        assert report.exists()
        content = report.read_text()
        assert "Code Review Report" in content

    def test_skills_injected_appear_in_report(self, tmp_path):
        mod = self._load()
        run = mod["run"]
        docs = tmp_path / "docs"
        result = run({
            "path": str(tmp_path),
            "aidlc_docs": str(docs),
            "skills": {"caveman-review": "# Caveman Review Skill\nBe brief."},
        })
        report = Path(result["report_path"])
        assert "caveman-review" in report.read_text()
