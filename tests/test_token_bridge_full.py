from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "aidlc-scripts"))


# ── Fixtures ────────────────────────────────────────────────────────────────

@pytest.fixture
def repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


# ── factory_token_to_tailwind.py ───────────────────────────────────────────

def test_tailwind_importable():
    from factory_token_to_tailwind import generate_tailwind_config
    assert callable(generate_tailwind_config)


def test_tailwind_generate_contains_tokens(repo_root: Path):
    from factory_token_to_tailwind import generate_tailwind_config
    config = generate_tailwind_config(repo_root)
    assert "spacing:" in config
    assert "borderRadius:" in config
    assert "fontSize:" in config
    assert "colors:" in config
    assert "'md': 12" in config
    assert "'sm':" in config
    assert "tailwindcss" in config


def test_tailwind_generate_esm(repo_root: Path):
    from factory_token_to_tailwind import generate_tailwind_config
    config = generate_tailwind_config(repo_root, esm=True)
    assert "export default config" in config


def test_tailwind_generate_cjs(repo_root: Path):
    from factory_token_to_tailwind import generate_tailwind_config
    config = generate_tailwind_config(repo_root, esm=False)
    assert "module.exports = config" in config


def test_tailwind_no_tokens_dir(tmp_path: Path):
    from factory_token_to_tailwind import generate_tailwind_config
    config = generate_tailwind_config(tmp_path)
    assert "No design-system/tokens/" in config


def test_tailwind_empty_output_file(repo_root: Path, tmp_path: Path):
    from factory_token_to_tailwind import generate_tailwind_config
    config = generate_tailwind_config(repo_root)
    assert len(config) > 300
    assert "module.exports" in config


# ── factory_token_bridge.py ─────────────────────────────────────────────────

def test_bridge_importable():
    from factory_token_bridge import prepare, list_prompts, bootstrap_greenfield
    assert callable(prepare)
    assert callable(list_prompts)
    assert callable(bootstrap_greenfield)


def test_bridge_prepare(repo_root: Path, tmp_path: Path):
    from factory_token_bridge import prepare
    result = prepare(repo_root, tmp_path)
    assert len(result["artifacts"]) >= 2
    artifact_types = [a["type"] for a in result["artifacts"]]
    assert "css" in artifact_types
    assert "prompt" in artifact_types


def test_bridge_prepare_generates_files(repo_root: Path, tmp_path: Path):
    from factory_token_bridge import prepare
    prepare(repo_root, tmp_path)
    assert (tmp_path / "tokens.css").exists()
    assert (tmp_path / "token-prompt.md").exists()


def test_bridge_prepare_prompt_content(repo_root: Path, tmp_path: Path):
    from factory_token_bridge import prepare
    result = prepare(repo_root, tmp_path)
    assert result["prompt_path"] is not None
    prompt = Path(result["prompt_path"]).read_text(encoding="utf-8")
    assert "Design Tokens" in prompt


def test_bridge_list_prompts(repo_root: Path):
    from factory_token_bridge import list_prompts
    prompts = list_prompts(repo_root)
    names = [p["name"] for p in prompts]
    assert "tokens" in names
    assert len(prompts) == 1  # Only the generic tokens.md


def test_bridge_bootstrap_greenfield(tmp_path: Path):
    from factory_token_bridge import bootstrap_greenfield
    created = bootstrap_greenfield(tmp_path, force=True)
    assert len(created) >= 4
    assert (tmp_path / "design-system" / "tokens" / "spacing.md").exists()
    assert (tmp_path / "design-system" / "tokens" / "color.md").exists()
    assert (tmp_path / "design-system" / "tokens" / "tokens.css").exists()


def test_bridge_bootstrap_idempotent(tmp_path: Path):
    from factory_token_bridge import bootstrap_greenfield
    first = bootstrap_greenfield(tmp_path, force=True)
    second = bootstrap_greenfield(tmp_path, force=False)
    assert len(second) == 0  # All exist, no overwrite


def test_bridge_bootstrap_force_overwrites(tmp_path: Path):
    from factory_token_bridge import bootstrap_greenfield
    first = bootstrap_greenfield(tmp_path, force=True)
    (tmp_path / "design-system" / "tokens" / "spacing.md").write_text("modified")
    second = bootstrap_greenfield(tmp_path, force=True)
    content = (tmp_path / "design-system" / "tokens" / "spacing.md").read_text()
    assert "Spacing Tokens" in content


# ── factory_design_system_extract_brownfield.py ─────────────────────────────

def test_brownfield_importable():
    from factory_design_system_extract_brownfield import detect_sources, extract_tailwind, extract_css_vars
    assert callable(detect_sources)
    assert callable(extract_tailwind)
    assert callable(extract_css_vars)


def test_brownfield_detect_empty(tmp_path: Path):
    from factory_design_system_extract_brownfield import detect_sources
    sources = detect_sources(tmp_path)
    assert len(sources) == 0


def test_brownfield_detect_tailwind(tmp_path: Path):
    from factory_design_system_extract_brownfield import detect_sources
    (tmp_path / "tailwind.config.js").write_text(
        'module.exports = { theme: { extend: { colors: { primary: "#000" } } } }',
        encoding="utf-8",
    )
    sources = detect_sources(tmp_path)
    assert any(s["type"] == "tailwind" for s in sources)


def test_tailwind_detected_v3_config(tmp_path: Path):
    from factory_token_bridge import _tailwind_detected
    (tmp_path / "tailwind.config.js").write_text("module.exports = {}", encoding="utf-8")
    assert _tailwind_detected(tmp_path) is True


def test_tailwind_detected_v3_package_json(tmp_path: Path):
    from factory_token_bridge import _tailwind_detected
    (tmp_path / "package.json").write_text(
        '{"devDependencies": {"tailwindcss": "^3.4.0"}}', encoding="utf-8"
    )
    assert _tailwind_detected(tmp_path) is True


def test_tailwind_detected_v4_css_import(tmp_path: Path):
    from factory_token_bridge import _tailwind_detected
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "index.css").write_text(
        '@import "tailwindcss";\n@theme { --color-primary: #2563EB; }',
        encoding="utf-8",
    )
    assert _tailwind_detected(tmp_path) is True


def test_tailwind_not_detected(tmp_path: Path):
    from factory_token_bridge import _tailwind_detected
    (tmp_path / "package.json").write_text(
        '{"dependencies": {"react": "^18.0.0"}}', encoding="utf-8"
    )
    assert _tailwind_detected(tmp_path) is False


def test_brownfield_detect_css_vars(tmp_path: Path):
    from factory_design_system_extract_brownfield import detect_sources
    css_dir = tmp_path / "src" / "styles"
    css_dir.mkdir(parents=True)
    (css_dir / "variables.css").write_text(
        ":root { --spacing-md: 12px; --color-primary: #2563EB; }",
        encoding="utf-8",
    )
    sources = detect_sources(tmp_path)
    assert any(s["type"] == "css_vars" for s in sources)


def test_brownfield_extract_tailwind(tmp_path: Path):
    from factory_design_system_extract_brownfield import extract_tailwind
    config = tmp_path / "tailwind.config.js"
    config.write_text(
        'module.exports = { theme: { extend: { spacing: { "md": "12px" }, '
        'colors: { "primary": "#2563EB" } } } }',
        encoding="utf-8",
    )
    result = extract_tailwind(tmp_path, config)
    assert result["source"] == "tailwind"
    assert "spacing" in result["tokens"]
    assert result["tokens"]["spacing"]["md"] == "12px"


def test_brownfield_extract_tailwind_single_line(tmp_path: Path):
    from factory_design_system_extract_brownfield import extract_tailwind
    config = tmp_path / "tailwind.config.js"
    config.write_text(
        'module.exports = { theme: { extend: { '
        "spacing: { 'xs': '4px', 'sm': '8px', 'md': '12px', 'lg': '16px' }, "
        "colors: { 'brand-primary': '#2563EB', 'brand-secondary': '#059669' }, "
        "borderRadius: { 'sm': '3px', 'md': '6px' } "
        '} } }',
        encoding="utf-8",
    )
    result = extract_tailwind(tmp_path, config)
    assert result["source"] == "tailwind"
    assert result["tokens"]["spacing"]["xs"] == "4px"
    assert result["tokens"]["spacing"]["sm"] == "8px"
    assert result["tokens"]["spacing"]["md"] == "12px"
    assert result["tokens"]["spacing"]["lg"] == "16px"
    assert result["tokens"]["colors"]["brand-primary"] == "#2563EB"
    assert result["tokens"]["colors"]["brand-secondary"] == "#059669"
    assert result["tokens"]["borderRadius"]["sm"] == "3px"
    assert result["tokens"]["borderRadius"]["md"] == "6px"


def test_brownfield_extract_css_vars(tmp_path: Path):
    from factory_design_system_extract_brownfield import extract_css_vars
    css_path = tmp_path / "tokens.css"
    css_path.write_text(
        ":root { --spacing-md: 12px; --radius-sm: 3px; --color-primary: #2563EB; }",
        encoding="utf-8",
    )
    result = extract_css_vars(tmp_path, css_path)
    assert result["source"] == "css_vars"
    assert "spacing" in result["tokens"]
    assert "color" in result["tokens"]


def test_brownfield_write_tokens(tmp_path: Path):
    from factory_design_system_extract_brownfield import write_tokens_from_extraction
    extracted = {
        "source": "tailwind",
        "tokens": {
            "spacing": {"md": "12", "lg": "16"},
            "color": {"primary": "#2563EB"},
        },
    }
    written = write_tokens_from_extraction(tmp_path, extracted)
    assert len(written) >= 2
    spacing_file = tmp_path / "design-system" / "tokens" / "spacing.md"
    assert spacing_file.exists()
    content = spacing_file.read_text(encoding="utf-8")
    assert "spacing.md" in content or "spacing" in content


def test_brownfield_detect_no_false_positives(tmp_path: Path):
    from factory_design_system_extract_brownfield import detect_sources
    (tmp_path / "some-random-file.js").write_text("var x = 1;")
    (tmp_path / "styles.css").write_text("body { color: red; }")
    sources = detect_sources(tmp_path)
    assert len(sources) == 0


# ── End-to-end: bridge detects brownfield ─────────────────────────────────

def test_bridge_detects_brownfield(tmp_path: Path):
    from factory_design_system_extract_brownfield import detect_sources
    (tmp_path / "tailwind.config.js").write_text(
        'module.exports = { theme: { extend: {} } }',
        encoding="utf-8",
    )
    sources = detect_sources(tmp_path)
    assert len(sources) >= 1
    assert sources[0]["type"] == "tailwind"


def test_bridge_prepare_with_brownfield_detection(repo_root: Path, tmp_path: Path):
    from factory_token_bridge import prepare
    result = prepare(repo_root, tmp_path)
    assert "artifacts" in result
    css_files = [a for a in result["artifacts"] if a["type"] == "css"]
    assert len(css_files) > 0


# ── Greenfield bootstrap produces valid tokens ─────────────────────────────

def test_greenfield_bootstrap_css_is_valid(tmp_path: Path):
    from factory_token_bridge import bootstrap_greenfield
    bootstrap_greenfield(tmp_path, force=True)
    css_file = tmp_path / "design-system" / "tokens" / "tokens.css"
    assert css_file.exists()
    content = css_file.read_text(encoding="utf-8")
    assert "--spacing-md: 12px" in content
    assert "--radius-sm: 3px" in content
    assert "--color-" in content
    assert "--typography-" in content


def test_greenfield_bootstrap_tailwind_generatable(tmp_path: Path):
    from factory_token_bridge import bootstrap_greenfield
    from factory_token_to_tailwind import generate_tailwind_config
    bootstrap_greenfield(tmp_path, force=True)
    config = generate_tailwind_config(tmp_path)
    assert "spacing:" in config
    assert "'md': 12" in config


# ── CLI smoke tests ───────────────────────────────────────────────────────

def test_token_to_css_cli_help():
    import subprocess
    r = subprocess.run(
        [sys.executable, "aidlc-scripts/factory_token_to_css.py", "--help"],
        capture_output=True, text=True,
    )
    assert r.returncode == 0
    assert "generate" in r.stdout


def test_token_to_tailwind_cli_help():
    import subprocess
    r = subprocess.run(
        [sys.executable, "aidlc-scripts/factory_token_to_tailwind.py", "--help"],
        capture_output=True, text=True,
    )
    assert r.returncode == 0
    assert "generate" in r.stdout


def test_bridge_cli_help():
    import subprocess
    r = subprocess.run(
        [sys.executable, "aidlc-scripts/factory_token_bridge.py", "--help"],
        capture_output=True, text=True,
    )
    assert r.returncode == 0
    assert "prepare" in r.stdout


def test_brownfield_cli_help():
    import subprocess
    r = subprocess.run(
        [sys.executable, "aidlc-scripts/factory_design_system_extract_brownfield.py", "--help"],
        capture_output=True, text=True,
    )
    assert r.returncode == 0
    assert "detect" in r.stdout


# ── Contract validation: code-generator input with token_bridge_artifacts ──

def test_code_generator_handoff_with_token_bridge_artifacts(tmp_path: Path):
    """Test that a code-generator input handoff with token_bridge_artifacts
    validates against the code-generator.input.v1.json schema contract.
    This ensures the orchestrator can inject bridge artifacts and agents
    will receive valid handoffs. (Plan item 6.6)"""
    import json
    import subprocess

    scripts = Path(__file__).resolve().parent.parent / "aidlc-scripts"
    contract = (scripts.parent / ".aidlc-orchestrator" / "contracts"
                / "code-generator.input.v1.json")
    validate_py = scripts / "factory_validate.py"

    # 1. Bootstrap tokens and run prepare
    from factory_token_bridge import bootstrap_greenfield, prepare
    bootstrap_greenfield(tmp_path, force=True)
    tokens_dir = tmp_path / ".aidlc-tokens"
    result = prepare(tmp_path, tokens_dir)

    # 2. Build a minimal valid code-generator input handoff
    artifacts = result.get("artifacts", [])
    handoff = {
        "run_id": "test-run-2026",
        "stage_id": "code-generator",
        "user_request": "Build a button component",
        "predecessor_artifacts": ["execution-plan.md", "unit-spec.yaml"],
        "unit_name": "button-component",
        "skills_required": [
            "using-agent-skills",
            "incremental-implementation",
            "test-driven-development",
            "source-driven-development",
        ],
        "skill_paths_resolved": ["path/to/skill.md"],
        "token_bridge_artifacts": artifacts,
        "design_system_path": "design-system/",
        "fast_path": False,
    }

    # 3. Write handoff to temp YAML (factory_validate.py reads YAML)
    handoff_path = tmp_path / "handoff.yaml"
    import yaml
    handoff_path.write_text(yaml.dump(handoff), encoding="utf-8")

    # 4. Validate against contract
    r = subprocess.run(
        [sys.executable, str(validate_py), str(contract), str(handoff_path)],
        capture_output=True, text=True,
    )
    assert r.returncode == 0, f"Validation FAILED:\nstdout={r.stdout}\nstderr={r.stderr}"
    assert "OK" in r.stdout


def test_code_generator_handoff_minimal_no_artifacts(tmp_path: Path):
    """Test that a handoff WITHOUT token_bridge_artifacts still validates
    (backward compatibility — projects without ui:true)."""
    import json
    import subprocess
    import yaml

    scripts = Path(__file__).resolve().parent.parent / "aidlc-scripts"
    contract = (scripts.parent / ".aidlc-orchestrator" / "contracts"
                / "code-generator.input.v1.json")
    validate_py = scripts / "factory_validate.py"

    handoff = {
        "run_id": "test-run-2026",
        "stage_id": "code-generator",
        "user_request": "Build an API endpoint",
        "predecessor_artifacts": ["execution-plan.md"],
        "unit_name": "api-endpoint",
        "skills_required": [
            "using-agent-skills",
            "incremental-implementation",
            "test-driven-development",
            "source-driven-development",
        ],
        "skill_paths_resolved": ["path/to/skill.md"],
        "fast_path": False,
    }

    handoff_path = tmp_path / "minimal-handoff.yaml"
    handoff_path.write_text(yaml.dump(handoff), encoding="utf-8")

    r = subprocess.run(
        [sys.executable, str(validate_py), str(contract), str(handoff_path)],
        capture_output=True, text=True,
    )
    assert r.returncode == 0, f"Validation FAILED:\nstdout={r.stdout}\nstderr={r.stderr}"
    assert "OK" in r.stdout


def test_build_test_agent_handoff_with_token_bridge_artifacts(tmp_path: Path):
    """Test build-test-agent handoff with token_bridge_artifacts validates
    against the build-test-agent.input.v1.json schema contract."""
    import subprocess
    import yaml

    scripts = Path(__file__).resolve().parent.parent / "aidlc-scripts"
    contract = (scripts.parent / ".aidlc-orchestrator" / "contracts"
                / "build-test-agent.input.v1.json")
    validate_py = scripts / "factory_validate.py"

    handoff = {
        "run_id": "test-run-2026",
        "stage_id": "build-test-agent",
        "user_request": "Build and test button component",
        "predecessor_artifacts": ["code-generator-output.yaml"],
        "unit_name": "button-component",
        "skills_required": [
            "using-agent-skills",
            "test-driven-development",
            "debugging-and-error-recovery",
        ],
        "skill_paths_resolved": ["path/to/skill.md"],
        "design_system_path": "design-system/",
        "token_bridge_artifacts": [
            {"type": "css", "path": "design-system/tokens/tokens.css"},
            {"type": "prompt", "path": "design-system/tokens/token-prompt.md"},
        ],
    }

    handoff_path = tmp_path / "bta-handoff.yaml"
    handoff_path.write_text(yaml.dump(handoff), encoding="utf-8")

    r = subprocess.run(
        [sys.executable, str(validate_py), str(contract), str(handoff_path)],
        capture_output=True, text=True,
    )
    assert r.returncode == 0, f"Validation FAILED:\nstdout={r.stdout}\nstderr={r.stderr}"
    assert "OK" in r.stdout
