# NOTICES

This product includes software developed by third parties. Their original
copyright notices and licenses are reproduced below.

The combined work is distributed under the Apache License, Version 2.0
(see [`LICENSE`](LICENSE)). The licenses below apply only to the original
upstream portions identified in each section; they continue to govern those
portions in this distribution.

---

## 1. AWS Labs — AI-DLC Workflows

**Source:** https://github.com/awslabs/aidlc-workflows (v0.2.0)
**License:** MIT No Attribution (MIT-0)
**Bundled in this repository:** `aidlc-rules/` (core workflow rules and rule
details) and the original `LICENSE` text from upstream.

```
MIT No Attribution

Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

Permission is hereby granted, free of charge, to any person obtaining a copy of
this software and associated documentation files (the "Software"), to deal in
the Software without restriction, including without limitation the rights to
use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of
the Software, and to permit persons to whom the Software is furnished to do so.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS
FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR
COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER
IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
```

**Modifications made in this fork** include but are not limited to:
- Added a multi-agent orchestrator under `.claude/agents/` and
  `.aidlc-orchestrator/`.
- Added contract-validated stage handoffs (JSON Schema) in
  `.aidlc-orchestrator/contracts/`.
- Added ~33 runtime scripts under `aidlc-scripts/factory_*.py`.
- Added skills enforcement, hallucination prevention, persistent memory,
  and CodeGraph integration.

---

## 2. Agent Skills (addyosmani)

**Source:** https://github.com/addyosmani/agent-skills
**Usage:** Cloned at install time when the installer is invoked with
`--with-agent-skills` (default on). Not bundled in this repository.
**License:** See the upstream repository for the current license terms
(`https://github.com/addyosmani/agent-skills/blob/main/LICENSE`).

Users who install AIDLC with `--with-agent-skills` receive a copy of
`agent-skills` from its upstream source under that project's own license,
independent of this repository's Apache-2.0 license.

---

## 3. CodeGraph MCP Server

**Source:** https://www.npmjs.com/package/@colbymchenry/codegraph (npm)
**Usage:** Installed as an npm package at install time when the installer
is invoked with `--with-codegraph`. Not bundled in this repository — only
the project-local `.mcp.json` configuration is written.
**License:** See the npm package metadata for the current license terms.

---

## 4. Engram Persistent Memory

**Source:** MCP-based external server.
**Usage:** Configured at install time when the installer is invoked with
`--with-engram`. Not bundled in this repository.
**License:** Governed by the upstream Engram distribution's terms.

---

## 5. Claude Code

**Source:** Anthropic (CLI, IDE extensions, web app).
**Usage:** The multi-agent orchestrator targets Claude Code as its host
harness via the `Task()` spawn primitive. Claude Code is not bundled in
this repository — users install it independently.
**License:** Governed by Anthropic's terms of service.

---

## 6. autoskills (midudev)

**Source:** https://github.com/midudev/autoskills
**Usage:** Invoked at runtime as `npx --yes autoskills --yes` by
`aidlc-scripts/factory_skill_sync.py` to install framework-specific skills
detected in the user's workspace. Not bundled in this repository — the
`autoskills` package is fetched on demand from the public npm registry by
the end user's environment.
**License:** See the upstream repository for the current license terms
(`https://github.com/midudev/autoskills/blob/main/LICENSE`). Skills
installed by `autoskills` into `.agents/skills/` carry their own
upstream licenses, independent of this repository's Apache-2.0 license.

---

## 7. The Book of Secret Knowledge (trimstray)

**Source:** https://github.com/trimstray/the-book-of-secret-knowledge
**License:** Creative Commons Attribution-NonCommercial-ShareAlike 4.0
International (CC BY-NC-SA 4.0) — see
`https://github.com/trimstray/the-book-of-secret-knowledge/blob/master/LICENSE`.
**Usage in this repository:** The structure, topic taxonomy, and tool
selection of `.agents/custom-skills/secret-knowledge/` (catalog of CLI
tools, security toolkits, web-security scanners, performance diagnostics,
DevOps cheatsheets, and shell one-liners) is inspired by and adapted
from the upstream Book of Secret Knowledge. The bundled content in this
repository has been rewritten and restructured for use as an AIDLC stage
skill — it is not a verbatim copy.

> **License-compatibility note.** CC BY-NC-SA 4.0 is not a permissive
> license: it forbids commercial use (NC) and requires derivative works
> to be licensed under CC BY-NC-SA (SA). Both clauses are in tension with
> this repository's Apache-2.0 license. Bundled content under
> `.agents/custom-skills/secret-knowledge/` should be limited to
> non-copyrightable facts (tool names, command syntax, public CLI
> options) and original prose. If any section of the upstream is copied
> verbatim or closely paraphrased, that section inherits CC BY-NC-SA 4.0
> and should be either rewritten or scoped out of the Apache-2.0 grant.
> See the "How to update this file" guidance below.

---

## How to update this file

When you bundle new third-party code:

1. Add a section to this file with: source URL, license name, what's
   bundled vs referenced, and the upstream copyright/license text if the
   upstream license requires reproduction (most do).
2. If the upstream uses a copyleft license (GPL, AGPL, LGPL), confirm
   compatibility with this project's Apache-2.0 license before bundling.
3. If the upstream license requires retaining copyright notices in
   modified files, do so — Apache-2.0 § 4(c) makes this binding regardless
   of upstream terms.

When a third-party component is only *referenced* (downloaded at install
time, not committed to this repo), a short reference section is sufficient.
