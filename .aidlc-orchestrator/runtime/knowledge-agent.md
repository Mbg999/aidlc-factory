# Knowledge Agent

PRIORITY: P3

Engram-backed persistent memory (MCP, NOT Task()). Full spec:
[`cross-cutting/knowledge-agent.md`](../../.claude/agents/cross-cutting/knowledge-agent.md).
- **Pre-spawn**: `mem_search` → top-5 priors into `context_pointers[]` (~2.5K tokens).
- **Post-return**: persist `emitted_knowledge[]` as `aidlc/<slug>/<kind>/<title>`.
- **Degraded**: engram unavailable → log, continue with empty priors.
