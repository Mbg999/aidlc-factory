# Generic Agent Adapter for AI-DLC

This adapter covers any AI coding assistant not listed in the other adapters
(Windsurf, Aider, Continue, custom agents, etc.).

## Setup

Point your agent at the core workflow file:

```
aidlc-rules/aws-aidlc-rules/core-workflow.md
```

And the rule details root:

```
aidlc-rules/aws-aidlc-rule-details/
```

Most agents support one of these mechanisms:
- **System prompt / instructions file**: Paste or reference the core-workflow content
- **Context file injection**: Include `aidlc-rules/aws-aidlc-rules/core-workflow.md` as a context file at session start
- **RAG / embedding**: Index `aidlc-rules/` into your agent's retrieval system

## Skills

Install engineering process skills for full workflow enforcement:

```bash
python scripts/install_aidlc.py --tool other --with-agent-skills --dest .
```

Skills are installed to `.agents/skills/<name>/SKILL.md`. Each stage rule file
references mandatory skills and includes inline fallback processes when skills
are not installed.

## Key Paths

| Purpose | Path |
|---------|------|
| Core workflow | `aidlc-rules/aws-aidlc-rules/core-workflow.md` |
| Rule details | `aidlc-rules/aws-aidlc-rule-details/` |
| Extensions | `aidlc-rules/aws-aidlc-rule-details/extensions/` |
| Skills | `.agents/skills/` |
| State file | `aidlc-docs/aidlc-state.md` |
| Run outputs | `aidlc-docs/` |

## Verification

Ask your agent: "What phase are we in according to AI-DLC?" — it should respond
with the current phase from `aidlc-docs/aidlc-state.md`.
