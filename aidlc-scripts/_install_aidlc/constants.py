from __future__ import annotations

from pathlib import Path


AGENT_SKILLS_REPO = "https://github.com/addyosmani/agent-skills.git"
AGENT_SKILLS_DIRS = ["skills", "references"]

VALID_TOOLS = (
    "cursor", "claude",
    "copilot", "opencode", "codex", "frida", "other",
)

ORCHESTRATOR_FACTORY_SCRIPTS = [
    "factory_validate.py",
    "factory_merge_reviews.py",
    "factory_conflict.py",
    "factory_run.py",
    "factory_triage.py",
    "factory_audit_writes.py",
    "factory_secretscan.py",
    "factory_build_cache.py",
    "factory_complexity.py",
    "factory_model.py",
    "factory_graph.py",
    "factory_agent_discover.py",
    "factory_telemetry.py",
    "factory_content_validate.py",
    "factory_lint_rules.py",
    "factory_evidence_extract.py",
    "factory_features.py",
    "factory_stage_registry.py",
    "factory_cost_estimate.py",
    "factory_quality_report.py",
    "factory_prompt_ab.py",
    "factory_slo_check.py",
    "factory_knowledge_promote.py",
    "factory_knowledge_dashboard.py",
    "factory_custom_skills.py",
    "factory_skill_drift.py",
    "factory_design_system_snap.py",
    "factory_design_system_resolve.py",
    "factory_design_system_learn.py",
    "factory_design_system_harness.py",
    "factory_design_system_extract_brownfield.py",
    "factory_token_to_css.py",
    "factory_token_to_tailwind.py",
    "factory_token_bridge.py",
    "harness_adapters/__init__.py",
    "harness_adapters/source/__init__.py",
    "harness_adapters/source/base.py",
    "harness_adapters/source/figma.py",
    "harness_adapters/source/stitch.py",
    "harness_adapters/source/raw_json.py",
    "prompts/tech-stack/tokens.md",
    "factory_stitch_snap.py",
    "factory_skill_sync.py",
    "skill_utils.py",
    "factory_codegraph.py",
    "factory_project_context.py",
    "factory_tech_mappings.py",
    "stage_gate.py",
    "factory_context_builder.py",
    "factory_project_profile.py",
    "factory_drift_detect.py",
    "factory_ds_bootstrap.py",
    "factory_figma_mcp.py",
    "factory_primitive_gen.py",
    "factory_stitch_mcp.py",
]

ORCHESTRATOR_ROOT_CONFIGS = [
    "skill-sources.yaml",
]

ORCHESTRATOR_TOOL_MCP_CONFIGS = {
    "claude":   Path(".mcp.json"),
    "cursor":   Path(".cursor/mcp.json"),
    "copilot":  Path(".vscode/mcp.json"),
    "opencode": Path("opencode.json"),
    "frida":    Path(".mcp.json"),
}

ORCHESTRATOR_EXECUTOR_PKG_DIR = Path("aidlc-scripts/executors")

ORCHESTRATOR_QUALITY_DOCS = [
    Path("aidlc-docs/quality/slos.md"),
    Path("aidlc-docs/quality/codegraph-baseline.md"),
]

ORCHESTRATOR_CLAUDE_TREES = [
    Path(".claude/agents"),
]
ORCHESTRATOR_CLAUDE_COMMANDS_GLOB = "factory-*.md"

ORCHESTRATOR_PYTHON_DEPS = [
    "jsonschema>=4.0",
    "pyyaml>=6.0",
    "tree-sitter>=0.21",
    "tree-sitter-typescript>=0.21",
    "tree-sitter-javascript>=0.21",
]

ORCHESTRATOR_GITIGNORE_ENTRIES = [
    ".aidlc-orchestrator/runs/",
    ".aidlc-orchestrator/knowledge/",
    ".codegraph/",
    ".venv/",
    "__pycache__/",
    "node_modules/",
    "dist/",
    "build/",
]
ORCHESTRATOR_GITIGNORE_HEADER = "# AIDLC orchestrator runtime state"

ORCHESTRATOR_COPILOT_INSTRUCTION_FILES = (
    "copilot-commit-instructions.md",
    "copilot-review-instructions.md",
    "copilot-pull-request-instructions.md",
)

ORCHESTRATOR_COPILOT_POINTER_BLOCK = (
    "\n<!-- AIDLC-ORCHESTRATOR-POINTER -->\n"
    "## AIDLC Orchestrator (multi-agent factory mode)\n\n"
    "This project ships with the AIDLC orchestrator. Stage agents: `.github/agents/stage/`;\n"
    "cross-cutting agents: `.github/agents/cross-cutting/`; orchestrator: `.github/agents/orchestrator.agent.md`;\n"
    "skills: `.github/skills/`; prompts (user-invocable commands): `.github/prompts/`.\n\n"
    "Invoke from Copilot Chat in **Agent mode** by typing `/` and selecting the prompt:\n\n"
    "- `/factory-code-tour` — dependency-ordered codebase tour: foundations → entry points\n"
    "- `/factory-spec` — workspace scout + requirements + plan\n"
    "- `/factory-plan` — decompose plan into per-unit specs\n"
    "- `/factory-build` — layer-parallel code generation\n"
    "- `/factory-review` — parallel reviewer pool (code, security, performance, simplifier)\n"
    "- `/factory-ship` — release notes, ADRs, CI/CD wiring, CHANGELOG\n"
    "- `/factory-resume` — resume an interrupted run\n"
    "- `/factory-replay` — re-run from a specific stage\n"
    "- `/factory-state` — show run status, stage, budget\n\n"
    "Roles, contracts, budgets: `.aidlc-orchestrator/contracts/`, `.aidlc-orchestrator/budgets/default.yaml`.\n\n"
    "**Required VS Code settings** (enables nested subagent spawning + AIDLC paths):\n"
    "```json\n"
    '{\n'
    '  "chat.subagents.allowInvocationsFromSubagents": true,\n'
    '  "chat.agentFilesLocations": { ".github/agents": true },\n'
    '  "chat.promptFilesLocations": { ".github/prompts": true }\n'
    '}\n'
    "```\n"
)

ORCHESTRATOR_CLAUDE_POINTER_MARKER = "<!-- AIDLC-ORCHESTRATOR-POINTER -->"
ORCHESTRATOR_CLAUDE_POINTER_BLOCK = (
    f"\n{ORCHESTRATOR_CLAUDE_POINTER_MARKER}\n"
    "## AIDLC Orchestrator (multi-agent factory mode)\n\n"
    "This project ships with the AIDLC orchestrator. To run the multi-agent factory:\n\n"
    "- `/factory-onboarding` — guided tour of the orchestrator system\n"
    "- `/factory-code-tour` — guided human tour of any codebase: architecture, key flows, conventions\n"
     "- `/factory-help [command]` — quick command reference\n"
     "- `/factory-state <run-id>` — current stage, next step, budget, timeline\n"
     "- `/factory-self <task>` — run the orchestrator on its own codebase\n"
     "- `/factory-spec <feature>` — workspace scout + (reverse-engineer) + requirements + (stories) + plan\n"
     "- `/factory-plan` — decompose plan into per-unit specs (multi-component features only)\n"
     "- `/factory-build` — layer-parallel code generation with file-glob locks + AST symbol drift checks\n"
     "- `/factory-review` — parallel reviewer pool (code, security, performance, simplifier)\n"
     "- `/factory-ship` — release notes, ADRs, CI/CD wiring, CHANGELOG, migration plan\n"
     "- `/factory-resume <run-id>` — resume an interrupted run (or adopt a legacy `aidlc-docs/` project)\n"
     "- `/factory-replay <run-id> --from <stage>` — re-run from a specific stage\n\n"
    "Roles, contracts, budgets, and parallelism rules: see `.claude/agents/orchestrator.md`,\n"
    "`.aidlc-orchestrator/contracts/`, and `.aidlc-orchestrator/budgets/default.yaml`.\n"
    "Design rationale and phase plan: `ORCHESTRATOR-PLAN.md` in the AIDLC source repo.\n"
)

ORCHESTRATOR_CODEX_POINTER_BLOCK = (
    f"\n{ORCHESTRATOR_CLAUDE_POINTER_MARKER}\n"
    "## AIDLC Orchestrator (multi-agent factory mode)\n\n"
    "This project ships with the AIDLC orchestrator. It is a multi-agent software-factory pipeline\n"
    "that guides AI coding agents through Inception → Construction → Operations.\n\n"
    "When the user asks to build a feature, fix a bug, or refactor code, use the orchestrator scripts:\n\n"
    "- `python3 aidlc-scripts/factory_run.py <run-id>` — start or resume a full AIDLC run\n"
    "- `python3 aidlc-scripts/factory_skill_sync.py sync` — install framework-specific skills\n"
    "- `python3 aidlc-scripts/factory_skill_sync.py select --output json` — list available skills\n"
    "- `python3 aidlc-scripts/factory_validate.py` — validate handoff contracts\n\n"
    "Key directories:\n"
    "- `.aidlc-orchestrator/contracts/` — JSON Schema handoff contracts for every stage I/O\n"
    "- `.aidlc-orchestrator/budgets/default.yaml` — per-stage model assignments\n"
    "- `.agents/skills/` — framework + process skills (loaded by skill protocol)\n"
    "- `.agents/custom-skills/` — custom skills shipped with this fork\n\n"
    "Design rationale and phase plan: `ORCHESTRATOR-PLAN.md` in the AIDLC source repo.\n"
)

ORCHESTRATOR_FRIDA_POINTER_BLOCK = (
    f"\n{ORCHESTRATOR_CLAUDE_POINTER_MARKER}\n"
    "## AIDLC Orchestrator (multi-agent factory mode)\n\n"
    "This project ships with the AIDLC orchestrator. It is a multi-agent software-factory pipeline\n"
    "that guides AI coding agents through Inception → Construction → Operations.\n\n"
    "Factory command skills are loaded from `.agents/skills/<command>/SKILL.md`:\n\n"
    "- `factory-spec` — workspace scout + requirements analysis\n"
    "- `factory-plan` — execution plan + unit decomposition\n"
    "- `factory-build` — parallel code generation + build/test\n"
    "- `factory-review` — parallel reviewer pool (code, security, performance, simplifier)\n"
    "- `factory-ship` — release notes, ADRs, CI/CD wiring, CHANGELOG\n"
    "- `factory-resume` — resume an interrupted run\n"
    "- `factory-replay` — re-run from a specific stage\n"
    "- `factory-state` — show run status, stage, budget\n"
    "- `factory-help` — full command reference\n"
    "- `factory-onboarding` — guided tour of the orchestrator system\n"
    "- `factory-code-tour` — guided human tour of any codebase\n"
    "- `factory-self` — run the orchestrator on its own codebase\n"
    "- `factory-product` — product harness (requirements + personas + stories + plan)\n\n"
    "Key directories:\n"
    "- `.aidlc-orchestrator/contracts/` — JSON Schema handoff contracts for every stage I/O\n"
    "- `.aidlc-orchestrator/budgets/default.yaml` — per-stage model assignments\n"
    "- `.agents/skills/` — framework + process skills + factory command skills\n"
    "- `.agents/custom-skills/` — custom skills shipped with this fork\n\n"
    "Usage: When the user asks to build a feature, fix a bug, or refactor code, "
    "load the `.agents/skills/<command>/SKILL.md` skill for the relevant factory command "
    "and execute the sequence described within.\n\n"
    "Design rationale and phase plan: `ORCHESTRATOR-PLAN.md` in the AIDLC source repo.\n"
)

CURSOR_MDC_FRONTMATTER = (
    "---\n"
    "description: AIDLC Core Workflow — constitution and orchestrator pointer for the AI-Driven Development Life Cycle. "
    "Priority OVERRIDES other built-in workflows.\n"
    "globs: null\n"
    "---\n"
)

WORKFLOW_REQUIRED_SKILLS = [
    "api-and-interface-design",
    "browser-testing-with-devtools",
    "ci-cd-and-automation",
    "code-review-and-quality",
    "code-simplification",
    "context-engineering",
    "debugging-and-error-recovery",
    "deprecation-and-migration",
    "documentation-and-adrs",
    "frontend-ui-engineering",
    "git-workflow-and-versioning",
    "idea-refine",
    "incremental-implementation",
    "performance-optimization",
    "planning-and-task-breakdown",
    "security-and-hardening",
    "shipping-and-launch",
    "source-driven-development",
    "spec-driven-development",
    "test-driven-development",
]

CODEGRAPH_NPM_PACKAGE = "@colbymchenry/codegraph"
CODEGRAPH_NODE_MIN = 18

CODEGRAPH_MCP_CONFIG = {
    "mcpServers": {
        "codegraph": {
            "command": "codegraph",
            "args": ["mcp"],
            "env": {}
        }
    }
}

CODEGRAPH_TOOL_MAP = {
    "claude": "claude",
    "cursor": "cursor",
    "opencode": "opencode",
    "codex": "codex",
    "copilot": "copilot",
}

CODEGRAPH_SAFE_ORCHESTRATOR_TOOLS = [
    "codegraph_search",
    "codegraph_node",
    "codegraph_files",
    "codegraph_status",
]

ENGRAM_CLI_SETUP = {
    "claude": [
        ["claude", "plugin", "marketplace", "add", "Gentleman-Programming/engram"],
        ["claude", "plugin", "install", "engram"],
    ],
    "opencode": [["engram", "setup", "opencode"]],
}

ENGRAM_MCP_TOOLS = frozenset({"cursor", "copilot", "frida", "other"})

ENGRAM_MCP_ENTRY = {"command": "engram", "args": ["mcp"]}
ENGRAM_PROJECT_CONFIG_RELPATH = Path(".engram") / "project.json"

DESIGN_SYSTEM_SRCS = frozenset({
    "design-system",
    ".agents/custom-skills/design-system-composer",
    ".agents/custom-skills/ui-constraint-validator",
})

COOKBOOK_SKILL_NAME = "ai-architecture-cookbook"
COOKBOOK_SKILL_DIR = ".agents/custom-skills/ai-architecture-cookbook"
COOKBOOK_SKILL_RELPATH = ".agents/custom-skills/ai-architecture-cookbook/SKILL.md"

COOKBOOK_MCP_SERVER_ENTRY = {
    "command": "npx",
    "args": ["-y", "@ai-architecture-cookbook/mcp-server"],
}

COOKBOOK_MCP_SERVER_ENTRY_OPENCODE = {
    "type": "local",
    "command": ["npx", "-y", "@ai-architecture-cookbook/mcp-server"],
    "enabled": True,
}

COOKBOOK_MCP_TARGET_FILES = [
    (".mcp.json",      "mcpServers"),
    (".cursor/mcp.json", "mcpServers"),
    ("opencode.json",    "mcp"),
    ("codex.json",       "mcpServers"),
    (".vscode/mcp.json", "servers"),
]

COOKBOOK_MCP_TOOL_FILES = {
    "claude":   [".mcp.json"],
    "cursor":   [".cursor/mcp.json"],
    "copilot":  [".vscode/mcp.json"],
    "opencode": ["opencode.json"],
    "codex":    ["codex.json"],
    "frida":    [".mcp.json"],
    "other":    [".mcp.json"],
}

FRIDA_MCP_FALLBACK_CONTEXT7 = {
    "type": "stdio",
    "command": "npx",
    "args": ["-y", "@upstash/context7-mcp"],
    "env": {},
}

FRIDA_MCP_FALLBACK_CHROME = {
    "type": "stdio",
    "command": "npx",
    "args": ["-y", "chrome-devtools-mcp@latest"],
    "env": {},
}

FRIDA_MCP_FALLBACK_CODEGRAPH = {
    "type": "stdio",
    "command": "codegraph",
    "args": ["serve", "--mcp", "--path", "<PROJECT_PATH>"],
    "env": {},
}

FRIDA_MCP_FALLBACK_ENGRAM = {
    "type": "stdio",
    "command": "engram",
    "args": ["mcp", "--tools=agent"],
}

TOOL_DESCRIPTIONS = {
    "cursor":   "Cursor editor — writes to .cursor/agents/ and .cursor/commands/",
    "claude":   "Claude Code CLI — writes to .claude/agents/ and .claude/commands/",
    "copilot":  "GitHub Copilot in VS Code — writes to .github/agents/, .github/prompts/, .github/skills/",
    "opencode": "OpenCode TUI — writes to .opencode/agents/ and .opencode/commands/",
    "codex":    "OpenAI Codex CLI / IDE agent — writes .codex/agents/ (TOML custom agents) + AGENTS.md pointer",
    "frida":    "Frida AI agent — writes to .aidlc-orchestrator/agents/ + .agents/skills/<command>/SKILL.md factory command skills (no native subagent spawning)",
    "other":    "Generic install — writes to .aidlc-orchestrator/agents/ (no native subagent spawning)",
}

PREFLIGHT_EXIT_CODE = 9
