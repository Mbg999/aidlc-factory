# Contributing Guidelines

Thank you for your interest in contributing to AI-DLC. Whether it's a bug report, new rule, correction, or documentation improvement, we welcome your contributions.

Please read through this document before submitting any issues or pull requests.

## Developer Quickstart

```bash
# 1. Clone and enter the repo
git clone <your-fork-url>
cd custom\ aidlc

# 2. Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate          # macOS/Linux
# .venv\Scripts\activate           # Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run all tests
python -m pytest aidlc-scripts/tests/ -q

# 5. Install skills into a target project
python aidlc-scripts/install_aidlc.py --tool copilot --with-agent-skills
```

**What to expect:**

- All tests pass quickly
- Skills are installed to `.agents/skills/` in the target project
- The workflow uses skills defined in stage rule files

## Tenets

Before contributing, familiarize yourself with our [tenets](README.md#tenets).

## Contributing Rules

AI-DLC rules live in `aidlc-rules/aws-aidlc-rule-details/`. When contributing:

- **Be reproducible**: Changes should be consistently reproducible either via test case or a series of steps.
- **Single source of truth**: Don't duplicate content. If guidance applies to multiple stages, put it in `common/` and reference it.
- **Keep it agnostic**: The core methodology must not assume specific IDEs, agents, cloud providers, or models. Tool-specific files go in `aidlc-rules/adapters/`.

### Directory Structure

```text
aidlc-rules/
├── aws-aidlc-rules/            # Core workflow entry point
│   └── core-workflow.md
├── aws-aidlc-rule-details/          # Detailed rules referenced by the workflow
│   ├── common/
│   ├── inception/
│   ├── construction/
│   ├── extensions/
│   └── operations/
└── adapters/              # Tool-specific setup guides (informational only)
    ├── copilot.md
    ├── cursor.md
    ├── claude-code.md
    ├── cline.md
    └── generic.md
```

### Rule Structure

Rules are organized by phase:

- `common/` - Shared guidance across all phases
- `inception/` - Planning and architecture rules
- `construction/` - Design and implementation rules
- `operations/` - Deployment and monitoring rules
- `extensions/` - Optional cross-cutting constraint rules

### Testing Changes

Run the full test suite before submitting:

```bash
python -m pytest aidlc-scripts/tests/ -v
```

When adding or modifying rule files, verify them against at least one supported coding agent.
When adding or modifying skills, follow the SKILL.md anatomy documented in `stage-conventions.md`.

## Contributing to the Orchestrator

The multi-agent orchestrator (`.claude/agents/`, `.aidlc-orchestrator/`, `aidlc-scripts/factory_*.py`) has three coupled surfaces that must stay in sync. A change in one almost always demands matching changes in the others — otherwise validation rejects handoffs, agents read undeclared fields, or rules drift between platforms.

### Cross-cutting change checklist

When you change a stage agent's input or output, walk through this list:

1. **Contract** — update the JSON Schema in `.aidlc-orchestrator/contracts/<stage>.<input|output>.v1.json`. Schemas use `additionalProperties: false`; any field the orchestrator sets MUST be declared, or the handoff fails validation silently.
2. **Agent body — all four platforms** — apply the same change to every platform copy of the agent file:
   - `.claude/agents/stage/<stage>.md`
   - `.cursor/agents/stage/<stage>.md`
   - `.opencode/agents/stage/<stage>.md`
   - `.github/agents/stage/<stage>.agent.md`
   Frontmatter conventions differ per platform (Claude uses `model:`; Copilot uses `*.agent.md`, `tools`, `agents`, `user-invocable`; OpenCode adds `mode` and `permission`; Cursor uses `model: inherit`, `readonly`, `is_background`); body content stays identical.
3. **Orchestrator commands** — if a command builds the handoff or consumes the output, mirror the change across:
   - `.aidlc-orchestrator/runtime/cmd-factory-<phase>.md` (canonical)
   - `.claude/commands/factory-<phase>.md`
   - `.cursor/commands/factory-<phase>.md`
   - `.opencode/commands/factory-<phase>.md`
   - `.github/prompts/factory-<phase>.prompt.md`
4. **Strict validation** — content-level invariants (e.g. "if `sub_stage == generated` then a `kind: plan` artifact must exist on disk") belong in `aidlc-scripts/factory_validate.py` under `_strict_check`, and the orchestrator command must invoke `factory_validate.py … --strict` for that stage. Schema validation alone is not enough — schemas can't express "the file at this path exists."
5. **Installer wiring** — any new file added under the orchestrator must be registered in `aidlc-scripts/install_aidlc.py` under the correct install flag, or downstream installs won't ship it.

### Sanity-check your change

Before opening the PR:

```bash
# Confirm every contract still parses
python3 -c "import json, pathlib; [json.loads(p.read_text()) for p in pathlib.Path('.aidlc-orchestrator/contracts').glob('*.json')]"

# If you touched a stage agent, confirm the four platform copies are in sync
diff .claude/agents/stage/<stage>.md .opencode/agents/stage/<stage>.md
diff .claude/agents/stage/<stage>.md .cursor/agents/stage/<stage>.md
diff .claude/agents/stage/<stage>.md .github/agents/stage/<stage>.agent.md
# (frontmatter will differ; body should not)
```

## Reporting Bugs/Feature Requests

Use GitHub issues to report bugs or suggest features. Before filing, check existing issues to avoid duplicates.

Include:

- Which rule or stage is affected
- Expected vs actual behavior
- The platform/model you tested with

## Contributing via Pull Requests

Before sending a pull request:

1. Work against the latest `main` branch
2. Check existing open and recently merged PRs
3. Open an issue first for significant changes

To submit:

1. Fork the repository
2. Make your changes (keep them focused)
3. Use clear commit messages following [conventional commits](https://www.conventionalcommits.org/) (e.g., `feat:`, `fix:`, `docs:`)
4. Submit the PR and respond to feedback

## Code of Conduct

This project follows the [Contributor Covenant Code of Conduct](CODE_OF_CONDUCT.md).

## Security Issue Notifications

If you discover a potential security issue in this project, please open a GitHub issue with the `security` label or contact the maintainers directly. Do not post sensitive details publicly.

## Licensing

See the [LICENSE](LICENSE) file for our project's licensing. We will ask you to confirm the licensing of your contribution.
