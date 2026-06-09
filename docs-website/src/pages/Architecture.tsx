import { Section, CodeBlock, Card } from "../components/DocUI";

export default function Architecture() {
  return (
    <div className="animate-in fade-in slide-in-from-bottom-4 duration-500">
      <Section title="System Architecture">
        <p>
          AIDLC-Factory's architecture follows a <strong>flat orchestration</strong> pattern:
          the orchestrator agent reads the execution plan, spawns stage subagents sequentially or in
          parallel, validates their output against JSON Schema contracts, and presents artifacts for
          human approval at each gate.
        </p>
      </Section>

      <Section title="Orchestrator Pattern">
        <p>
          The orchestrator is not a daemon or server. It is an agent prompt (located at
          <code>&lt;tool&gt;/agents/orchestrator.md</code>) that the coding tool loads when a
          <code>/factory-*</code> slash command fires. Execution:
        </p>
        <ol className="list-decimal pl-6 space-y-2 mt-4">
          <li><strong>Slash command invokes</strong> the orchestrator agent via the tool's command/prompt system.</li>
          <li><strong>Plan reading:</strong> loads the execution plan from <code>.aidlc-orchestrator/runs/&lt;run-id&gt;/</code>.</li>
          <li><strong>Spawn decision:</strong> resolves stage type, concurrency budget, and model assignment from <code>default.yaml</code>.</li>
          <li><strong>Subagent execution:</strong> for <code>build</code> and <code>review</code> stages, subagents run via <code>Task()</code> spawns with JSON Schema validation. All other stages run inline in the same session.</li>
          <li><strong>Contract validation:</strong> every stage output is validated against its <code>.aidlc-orchestrator/contracts/*.v1.json</code> schema before the handoff is accepted.</li>
          <li><strong>Approval gate:</strong> presents the artifact and pauses. On user approval, auto-commits with a stage-tagged message and advances the manifest.</li>
          <li><strong>Recovery:</strong> if interrupted, <code>/factory-resume</code> reads the manifest and continues from the last completed stage.</li>
        </ol>
      </Section>

      <Section title="Stage Pipeline">
        <div className="overflow-x-auto my-4">
          <table className="w-full text-sm border-collapse">
            <thead>
              <tr className="border-b border-slate-200 dark:border-slate-800">
                <th className="text-left py-2 pr-4 font-medium text-slate-900 dark:text-white">Stage</th>
                <th className="text-left py-2 pr-4 font-medium text-slate-900 dark:text-white">Spawn</th>
                <th className="text-left py-2 font-medium text-slate-900 dark:text-white">Input Contract</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200 dark:divide-slate-800">
              <tr><td className="py-2 pr-4 font-mono">workspace-scout</td><td className="py-2 pr-4">inline</td><td className="py-2 text-slate-600 dark:text-slate-400">feature-request</td></tr>
              <tr><td className="py-2 pr-4 font-mono">reverse-engineer</td><td className="py-2 pr-4">inline</td><td className="py-2 text-slate-600 dark:text-slate-400">workspace-profile (optional)</td></tr>
              <tr><td className="py-2 pr-4 font-mono">requirements-analyst</td><td className="py-2 pr-4">inline</td><td className="py-2 text-slate-600 dark:text-slate-400">workspace-profile</td></tr>
              <tr><td className="py-2 pr-4 font-mono">story-writer</td><td className="py-2 pr-4">inline</td><td className="py-2 text-slate-600 dark:text-slate-400">requirements + plan</td></tr>
              <tr><td className="py-2 pr-4 font-mono">application-designer</td><td className="py-2 pr-4">inline</td><td className="py-2 text-slate-600 dark:text-slate-400">requirements</td></tr>
              <tr><td className="py-2 pr-4 font-mono">workflow-planner</td><td className="py-2 pr-4">inline</td><td className="py-2 text-slate-600 dark:text-slate-400">app-design + requirements</td></tr>
              <tr><td className="py-2 pr-4 font-mono">unit-decomposer</td><td className="py-2 pr-4">inline</td><td className="py-2 text-slate-600 dark:text-slate-400">execution-plan</td></tr>
              <tr><td className="py-2 pr-4 font-mono">code-generator</td><td className="py-2 pr-4"><strong>Task()</strong></td><td className="py-2 text-slate-600 dark:text-slate-400">per-unit-spec</td></tr>
              <tr><td className="py-2 pr-4 font-mono">build-test-agent</td><td className="py-2 pr-4"><strong>Task()</strong></td><td className="py-2 text-slate-600 dark:text-slate-400">per-unit-output</td></tr>
              <tr><td className="py-2 pr-4 font-mono">reviewer-* (4x)</td><td className="py-2 pr-4"><strong>Task()</strong></td><td className="py-2 text-slate-600 dark:text-slate-400">per-unit-output</td></tr>
              <tr><td className="py-2 pr-4 font-mono">ship-agent</td><td className="py-2 pr-4">inline</td><td className="py-2 text-slate-600 dark:text-slate-400">all unit outputs</td></tr>
            </tbody>
          </table>
        </div>
      </Section>

      <Section title="Contracts">
        <p>
          Every stage input and output is governed by a JSON Schema contract in
          <code>.aidlc-orchestrator/contracts/</code>. This ensures:
        </p>
        <ul className="list-disc pl-6 space-y-2 mt-2">
          <li><strong>Structural integrity:</strong> downstream stages always receive well-formed data.</li>
          <li><strong>Fail-fast validation:</strong> a malformed handoff is caught at the stage boundary, not deep in execution.</li>
          <li><strong>Auditability:</strong> every handoff is a versioned, validated artifact that can be inspected and replayed.</li>
        </ul>
        <CodeBlock 
          language="text"
          code={`.aidlc-orchestrator/contracts/
  approval.v1.json
  audit-block.v1.json
  executor-conformance.v1.json
  shared/
    execution-context.v1.json
    stage-output.v1.json
    …
  stage/
    workspace-scope.output.v1.json
    requirements.output.v1.json
    execution-plan.output.v1.json
    per-unit-spec.v1.json
    per-unit-output.v1.json
    …`}
        />
      </Section>

      <Section title="Skills Layer">
        <p>
          Skills are reusable instruction sets that stage agents auto-attach during execution.
          Resolution order (first found wins):
        </p>
        <ol className="list-decimal pl-6 space-y-2 mt-2 mb-4">
          <li><code>.agents/custom-skills/&lt;name&gt;/SKILL.md</code> — project-specific</li>
          <li><code>.agents/skills/&lt;name&gt;/SKILL.md</code> — installed via <code>--with-agent-skills</code></li>
          <li><code>~/.agents/skills/&lt;name&gt;/SKILL.md</code> — user-global fallback</li>
        </ol>
        <p>This fork ships 22 custom skills, including:</p>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 mt-4">
          <Card title="validator-retry" description="Static type-check + linter feedback loop after every code generation unit. Catches hallucinated APIs at generation time." />
          <Card title="library-docs-with-context7" description="Routes every library/framework question through Context7 MCP before falling back to training data." />
          <Card title="design-system-composer" description="Composes UIs exclusively from approved primitives; never invents tokens." />
          <Card title="codegraph-aware-exploration" description="Prefer codegraph MCP tools over grep/glob when the code graph index exists." />
          <Card title="ai-architecture-cookbook" description="43 YAML architecture standards with pattern recommendation, checklist verification, and decision tree evaluation via MCP tools or inline YAML fallback." />
          <Card title="requirements-intelligence" description="Adaptive elicitation: Socratic probing, ambiguity detection, assumption mining, pre-mortem. Enforces 8-axis coverage." />
          <Card title="ui-constraint-validator" description="Scans generated UI for hardcoded values and snaps them to the nearest canonical token. Blocks slices with >3 violations." />
        </div>
      </Section>

      <Section title="Concurrency & Parallelism">
        <p>
          The orchestrator runs two kinds of parallelism:
        </p>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mt-4">
          <Card 
            title="Layer-Parallel Code Generation" 
            description="Independent units (e.g., frontend, backend, database) run concurrently. Layers (shared library &rarr; services &rarr; UI) run sequentially."
            features={[
              "File-glob lock registry in factory_conflict.py",
              "Python AST symbol-drift detection between parallel writers",
              "Configurable max_parallel in default.yaml"
            ]}
          />
          <Card 
            title="Parallel Reviewer Pool" 
            description="Code, security, performance, and simplification reviewers run simultaneously."
            features={[
              "Independent Task() spawns per reviewer",
              "Merged findings report with severity levels",
              "Per-reviewer model assignments from budget"
            ]}
          />
        </div>
      </Section>

      <Section title="Multi-Tool Support">
        <p>
          The orchestrator runs natively on Claude Code, Cursor, GitHub Copilot, OpenCode, and Codex.
          Each tool has its own subagent tree under <code>&lt;tool&gt;/agents/</code> and its own
          command/prompt directory. The executor adapter pattern abstracts away tool-specific spawning
          mechanics:
        </p>
        <CodeBlock 
          language="text"
          code={`aidlc-scripts/executors/
  base.py              # StageExecutor abstract base class
  claude_code_executor.py   # Production: uses Task() + stream
  cursor_executor.py        # Stub: inline execution
  opencode_executor.py       # Stub: inline execution
  codex_executor.py          # Stub: inline execution
  registry.yaml             # Maps --tool values to implementations
  runner.py                 # Spawn orchestrator for any tool`}
        />
      </Section>
    </div>
  );
}
