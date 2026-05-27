# Contributing Guidelines

Thank you for your interest in contributing to aidlc-factory. Whether it's a bug report, new rule, correction, or documentation improvement, we welcome your contributions.

Please read through this document before submitting any issues or pull requests.

## Developer Quickstart

```bash
# 1. Clone and enter the repo
git clone <your-fork-url>
cd aidlc-factory

# 2. Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate          # macOS/Linux
# .venv\Scripts\activate           # Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run all tests
python -m pytest tests/ -q

# 5. Install skills into a target project
python aidlc-scripts/install_aidlc.py --tool copilot --with-agent-skills
```

## Reporting Bugs/Feature Requests

Use GitHub issues to report bugs or suggest features. Before filing, check existing issues to avoid duplicates.

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

## Licensing

See the [LICENSE](LICENSE) file for our project's licensing. We will ask you to confirm the licensing of your contribution.
