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
python -m pytest scripts/tests/ -q

# 5. Explore available skills
python scripts/subagents/mcp_bridge.py --list-skills

# 6. List available pipelines
python scripts/subagents/pipeline.py --list

# 7. Run a single agent (dry-run against this repo)
python scripts/subagents/manager.py code-reviewer '{"path": "."}'
```

**What to expect:**

- All tests pass in ~1 second (29 tests)
- `--list-skills` shows skills installed in `~/.agents/skills/`
- `--list` shows `construction-full` and `review-only` pipelines
- The `code-reviewer` agent produces a report in `../aidlc-docs/reporting/`

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
python -m pytest scripts/tests/ -v
```

When adding or modifying subagent scripts, add tests to `scripts/tests/test_mcp_bridge_and_pipeline.py`.
When adding or modifying rule files, verify them against at least one supported coding agent.

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
