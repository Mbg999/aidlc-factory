import { Section, CodeBlock, Card, Note } from "../components/DocUI";

export default function Configuration() {
  return (
    <div className="animate-in fade-in slide-in-from-bottom-4 duration-500">
      <Section title="Environment Variables">
        <div className="overflow-x-auto my-4">
          <table className="w-full text-sm border-collapse">
            <thead>
              <tr className="border-b border-slate-200 dark:border-slate-800">
                <th className="text-left py-2 pr-4 font-medium text-slate-900 dark:text-white">Variable</th>
                <th className="text-left py-2 pr-4 font-medium text-slate-900 dark:text-white">Description</th>
                <th className="text-left py-2 font-medium text-slate-900 dark:text-white">Example</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200 dark:divide-slate-800">
              <tr>
                <td className="py-2 pr-4 font-mono text-xs text-indigo-600 dark:text-indigo-400">AIDLC_ROOT</td>
                <td className="py-2 pr-4 text-slate-600 dark:text-slate-400">Override the repo root path for factory scripts</td>
                <td className="py-2 font-mono text-xs text-slate-600 dark:text-slate-400">AIDLC_ROOT=/path/to/repo</td>
              </tr>
              <tr>
                <td className="py-2 pr-4 font-mono text-xs text-indigo-600 dark:text-indigo-400">AIDLC_MODEL_&lt;STAGE&gt;</td>
                <td className="py-2 pr-4 text-slate-600 dark:text-slate-400">Override the model for a specific stage. Uppercase with dashes &rarr; underscores</td>
                <td className="py-2 font-mono text-xs text-slate-600 dark:text-slate-400">AIDLC_MODEL_CODE_GENERATOR=opus</td>
              </tr>
              <tr>
                <td className="py-2 pr-4 font-mono text-xs text-indigo-600 dark:text-indigo-400">AIDLC_FEATURE_&lt;KEY&gt;</td>
                <td className="py-2 pr-4 text-slate-600 dark:text-slate-400">Override a feature flag from default.yaml</td>
                <td className="py-2 font-mono text-xs text-slate-600 dark:text-slate-400">AIDLC_FEATURE_CONTENT_VALIDATOR_STRICT=true</td>
              </tr>
            </tbody>
          </table>
        </div>
      </Section>

      <Section title="Per-Stage Model Assignments">
        <p>
          Stage models are configured in <code>.aidlc-orchestrator/budgets/default.yaml</code>:
        </p>
        <CodeBlock 
          language="yaml"
          code={`concurrency:
  max_parallel: 4

per_stage:
  workspace-scout:        { model: "sonnet" }
  reverse-engineer:       { model: "sonnet" }
  requirements-analyst:   { model: "opus" }
  story-writer:           { model: "sonnet" }
  application-designer:    { model: "sonnet" }
  workflow-planner:       { model: "opus" }
  unit-decomposer:        { model: "sonnet" }
  code-generator:         { model: "opus" }
  build-test-agent:       { model: "sonnet" }
  reviewer-code:          { model: "sonnet" }
  reviewer-security:      { model: "sonnet" }
  reviewer-performance:   { model: "sonnet" }
  reviewer-simplifier:    { model: "sonnet" }
  ship-agent:             { model: "sonnet" }
  custom-agent:           { model: "sonnet" }`}
        />
        <p className="mt-4">
          Notes:
        </p>
        <ul className="list-disc pl-6 space-y-2 mt-2">
          <li>Models use your coding tool's shorthand (sonnet/opus/haiku for Claude Code).</li>
          <li>Cursor ignores these — it uses <code>model: inherit</code> in frontmatter.</li>
          <li>Override any value at runtime via <code>AIDLC_MODEL_&lt;STAGE&gt;</code> env vars.</li>
          <li>Custom agents default to <code>sonnet</code> under the <code>custom-agent</code> key.</li>
        </ul>
      </Section>

      <Section title="Feature Flags">
        <p>
          Feature flags in <code>default.yaml</code> control gating behaviour:
        </p>
        <CodeBlock 
          language="yaml"
          code={`feature_flags:
  content_validator_strict: false    # Reject handoffs with validation warnings
  slo_breach_block: true             # Block the pipeline if stage exceeds its SLO
  knowledge_promotion: true          # Auto-promote stage learnings to Engram
  shared_corpus_injection: true     # Inject shared knowledge corpus into every stage`}
        />
      </Section>

      <Section title="Auto-Commit Configuration">
        <p>
          By default, the orchestrator auto-commits on explicit user approval. To opt out,
          remove this line from <code>.aidlc-orchestrator/runtime/run-manager.md</code>:
        </p>
        <CodeBlock 
          language="yaml"
          code={`auto_commit_on_approval: true  # Remove to disable auto-commit`}
        />
        <p className="mt-4">
          Approval signals:
        </p>
        <div className="flex flex-wrap gap-2 mt-2">
          <span className="px-3 py-1 text-xs font-mono bg-indigo-100 text-indigo-700 dark:bg-indigo-900/40 dark:text-indigo-300 rounded-full">approve</span>
          <span className="px-3 py-1 text-xs font-mono bg-indigo-100 text-indigo-700 dark:bg-indigo-900/40 dark:text-indigo-300 rounded-full">go ahead</span>
          <span className="px-3 py-1 text-xs font-mono bg-indigo-100 text-indigo-700 dark:bg-indigo-900/40 dark:text-indigo-300 rounded-full">lgtm</span>
          <span className="px-3 py-1 text-xs font-mono bg-indigo-100 text-indigo-700 dark:bg-indigo-900/40 dark:text-indigo-300 rounded-full">dale</span>
          <span className="px-3 py-1 text-xs font-mono bg-indigo-100 text-indigo-700 dark:bg-indigo-900/40 dark:text-indigo-300 rounded-full">s&iacute;</span>
          <span className="px-3 py-1 text-xs font-mono bg-indigo-100 text-indigo-700 dark:bg-indigo-900/40 dark:text-indigo-300 rounded-full">proceed</span>
          <span className="px-3 py-1 text-xs font-mono bg-indigo-100 text-indigo-700 dark:bg-indigo-900/40 dark:text-indigo-300 rounded-full">continue</span>
        </div>
      </Section>

      <Section title="Skills Configuration">
        <p>
          The skills resolver follows a three-tier lookup:
        </p>
        <ol className="list-decimal pl-6 space-y-2 mt-2 mb-4">
          <li><code>.agents/custom-skills/&lt;name&gt;/SKILL.md</code> (project-specific, highest priority)</li>
          <li><code>.agents/skills/&lt;name&gt;/SKILL.md</code> (installed via <code>--with-agent-skills</code>)</li>
          <li><code>~/.agents/skills/&lt;name&gt;/SKILL.md</code> (user-global fallback)</li>
        </ol>
        <p>
          Private or custom skills are registered in <code>skill-sources.yaml</code> with SHA-256 pinning:
        </p>
        <CodeBlock 
          language="yaml"
          code={`sources:
  - name: my-internal-skill
    url: https://example.com/skills/my-skill/SKILL.md
    sha256: "abcdef1234567890..."`}
        />
        <p className="mt-4">
          Install pinned skills with:
        </p>
        <CodeBlock 
          language="bash"
          code={`python3 aidlc-scripts/factory_custom_skills.py --skill my-internal-skill`}
        />
      </Section>

      <Section title="Installer Configuration">
        <p>
          The <code>install_aidlc.py</code> script accepts these flags:
        </p>
        <div className="overflow-x-auto my-4">
          <table className="w-full text-sm border-collapse">
            <thead>
              <tr className="border-b border-slate-200 dark:border-slate-800">
                <th className="text-left py-2 pr-4 font-medium text-slate-900 dark:text-white">Flag</th>
                <th className="text-left py-2 pr-4 font-medium text-slate-900 dark:text-white">Default</th>
                <th className="text-left py-2 font-medium text-slate-900 dark:text-white">Description</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200 dark:divide-slate-800">
              <tr><td className="py-2 pr-4 font-mono">--tool</td><td className="py-2 pr-4">required</td><td className="py-2 text-slate-600 dark:text-slate-400">claude, cursor, copilot, opencode, codex</td></tr>
              <tr><td className="py-2 pr-4 font-mono">--dest</td><td className="py-2 pr-4"><code>.</code></td><td className="py-2 text-slate-600 dark:text-slate-400">Target project directory</td></tr>
              <tr><td className="py-2 pr-4 font-mono">--with-agent-skills</td><td className="py-2 pr-4">on</td><td className="py-2 text-slate-600 dark:text-slate-400">Install engineering skills from addyosmani/agent-skills</td></tr>
              <tr><td className="py-2 pr-4 font-mono">--with-orchestrator</td><td className="py-2 pr-4">prompt</td><td className="py-2 text-slate-600 dark:text-slate-400">Install multi-agent orchestrator</td></tr>
              <tr><td className="py-2 pr-4 font-mono">--with-codegraph</td><td className="py-2 pr-4">off</td><td className="py-2 text-slate-600 dark:text-slate-400">CodeGraph MCP code knowledge graph</td></tr>
              <tr><td className="py-2 pr-4 font-mono">--with-engram</td><td className="py-2 pr-4">off</td><td className="py-2 text-slate-600 dark:text-slate-400">Engram persistent memory</td></tr>
              <tr><td className="py-2 pr-4 font-mono">--with-design-system</td><td className="py-2 pr-4">on</td><td className="py-2 text-slate-600 dark:text-slate-400">Design tokens + UI skills</td></tr>
              <tr><td className="py-2 pr-4 font-mono">--with-figma-mcp</td><td className="py-2 pr-4">off</td><td className="py-2 text-slate-600 dark:text-slate-400">Figma MCP server config</td></tr>
              <tr><td className="py-2 pr-4 font-mono">--force</td><td className="py-2 pr-4">off</td><td className="py-2 text-slate-600 dark:text-slate-400">Re-install/overwrite</td></tr>
              <tr><td className="py-2 pr-4 font-mono">--dry-run</td><td className="py-2 pr-4">off</td><td className="py-2 text-slate-600 dark:text-slate-400">Print plans without writing</td></tr>
              <tr><td className="py-2 pr-4 font-mono">--yes</td><td className="py-2 pr-4">off</td><td className="py-2 text-slate-600 dark:text-slate-400">Skip prompts</td></tr>
            </tbody>
          </table>
        </div>
      </Section>
    </div>
  );
}
