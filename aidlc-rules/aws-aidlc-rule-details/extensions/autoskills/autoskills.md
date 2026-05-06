# AutoSkills integration

Purpose: integrate AutoSkills (<https://github.com/midudev/autoskills>) as an optional
extension to automatically detect and propose (or optionally install) curated AI-agent
skills for this project.

When enabled (user chooses A or B in the opt-in prompt), the following behavior applies:

- Brownfield (existing codebase): run AutoSkills during the **Reverse Engineering** stage.
  - Execute the `midudev-autoskills` subagent in `dry-run` mode by default.
  - Attach the AutoSkills report to the Reverse Engineering artifacts and write a short
    summary to `aidlc-docs/autoskills-recommendations.md` with the proposed skills,
    rationale and any command suggestions.
  - If the user chose the install option (B), request an explicit approval step before
    performing the install. If approved, run the subagent with `install=true` and
    persist `skills-lock.json` and files under `.autoskills/` in the workspace.

- Greenfield (no repo code detected): run AutoSkills at **Workflow Planning** time
  using the Vision and Technical Environment documents as inputs (dry-run recommended).
  - Propose a curated list of skills and where each skill should be applied in the
    generated workflow (e.g., developer experience, CI, test harness, codegen adapters).
  - Do not install by default; installation requires user approval.

Security & Verification:

- Respect AutoSkills security model: only install skill files that are verified by the
  AutoSkills registry manifest. Do not fetch or run arbitrary third-party code without
  verification.
- Before writing any skill files to the workspace, run content validation per
  `common/content-validation.md` and record results in `aidlc-docs/audit.md`.

Subagent invocation (example):

```text
python3 scripts/subagents/manager.py midudev-autoskills '{"path":".", "install": false}'
```

Result handling:

- Parse the subagent output and generate `aidlc-docs/autoskills-recommendations.md`.
- Present the recommendations to the user as a two-option completion: "Request Changes"
  or "Approve and (optionally) Install".

Enforcement:

- This extension is opt-in. When enabled, recommended skills are advisory unless the
  user explicitly approves installation.

## Relationship with Custom Skills

AutoSkills and Custom Skills are complementary:

- **AutoSkills** are discovered per-project and may be installed into
  `.agents/skills/` in the workspace.  They require explicit approval.
- **Custom Skills** are pre-installed by the user (under `~/.agents/skills/`)
  or committed to the repo (under `<repo>/.agents/skills/`).  They are
  immediately available without installation.

When both sources are present, subagents receive:
- `context['autoskills']` — the AutoSkills lock file and directory
- `context['skills']` — the loaded SKILL.md content from custom skills

AutoSkills may discover skills that overlap with already-installed custom
skills.  In that case, custom skills take precedence (they're already
present and trusted).  The AutoSkills recommendation report should note
which proposed skills are already covered by existing custom skills.

To list currently installed custom skills:
```bash
python3 scripts/subagents/mcp_bridge.py --list-skills
```
