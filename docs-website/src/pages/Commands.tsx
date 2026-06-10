import { Section, CodeBlock } from "../components/DocUI";

export default function Commands() {
  return (
    <div className="animate-in fade-in slide-in-from-bottom-4 duration-500">
      <Section title="Slash Commands Reference">
        <p>
          Commands are invoked from inside your agentic coding tool. They route through the orchestrator
          agent under that tool's agents directory.
        </p>
      </Section>

      <Section title="Setup Commands">
        <div className="space-y-4 mt-4">
          <div className="p-4 rounded-lg bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-800">
            <div className="flex items-center gap-2 mb-2">
              <span className="font-mono text-indigo-600 dark:text-indigo-400 font-bold">/factory-onboarding</span>
              <span className="px-2 py-0.5 text-xs rounded-full bg-slate-200 dark:bg-slate-700 text-slate-600 dark:text-slate-400">Setup</span>
            </div>
            <p className="text-sm text-slate-600 dark:text-slate-400">
              Interactive walkthrough of the AIDLC orchestrator. Recommended first command for new users.
              Covers the lifecycle phases, approval gates, and how to run your first spec.
            </p>
          </div>

          <div className="p-4 rounded-lg bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-800">
            <div className="flex items-center gap-2 mb-2">
              <span className="font-mono text-indigo-600 dark:text-indigo-400 font-bold">/factory-help</span>
              <span className="px-2 py-0.5 text-xs rounded-full bg-slate-200 dark:bg-slate-700 text-slate-600 dark:text-slate-400">Setup</span>
            </div>
            <p className="text-sm text-slate-600 dark:text-slate-400">
              Full command reference and getting-started instructions displayed inline.
            </p>
          </div>
        </div>
      </Section>

      <Section title="Inception Commands">
        <div className="space-y-4 mt-4">
          <div className="p-4 rounded-lg bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-800">
            <div className="flex items-center gap-2 mb-2">
              <span className="font-mono text-indigo-600 dark:text-indigo-400 font-bold">/factory-spec &lt;feature&gt;</span>
              <span className="px-2 py-0.5 text-xs rounded-full bg-indigo-100 text-indigo-700 dark:bg-indigo-900/40 dark:text-indigo-300">Phase 0</span>
            </div>
            <p className="text-sm text-slate-600 dark:text-slate-400">
              Workspace detection + adaptive requirements analysis. Runs a two-pass Q&A session
              using the requirements-intelligence skill. Produces <code>aidlc-docs/&lt;run-id&gt;-requirements.md</code>.
            </p>
          </div>

          <div className="p-4 rounded-lg bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-800">
            <div className="flex items-center gap-2 mb-2">
              <span className="font-mono text-indigo-600 dark:text-indigo-400 font-bold">/factory-plan &lt;run-id&gt;</span>
              <span className="px-2 py-0.5 text-xs rounded-full bg-indigo-100 text-indigo-700 dark:bg-indigo-900/40 dark:text-indigo-300">Phase 1</span>
            </div>
            <p className="text-sm text-slate-600 dark:text-slate-400">
              Generates application design (components, interfaces, services), execution plan with
              Mermaid diagram, optional user stories/personas, and per-unit decomposition.
            </p>
          </div>

          <div className="p-4 rounded-lg bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-800">
            <div className="flex items-center gap-2 mb-2">
              <span className="font-mono text-indigo-600 dark:text-indigo-400 font-bold">/factory-product &lt;feature&gt;</span>
              <span className="px-2 py-0.5 text-xs rounded-full bg-indigo-100 text-indigo-700 dark:bg-indigo-900/40 dark:text-indigo-300">Phase 0-1</span>
            </div>
            <p className="text-sm text-slate-600 dark:text-slate-400">
              Combined run: workspace scout + requirements + personas + stories + execution plan.
              Stops before code generation. Useful for product-only iterations.
            </p>
          </div>
        </div>
      </Section>

      <Section title="Construction Commands">
        <div className="space-y-4 mt-4">
          <div className="p-4 rounded-lg bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-800">
            <div className="flex items-center gap-2 mb-2">
              <span className="font-mono text-indigo-600 dark:text-indigo-400 font-bold">/factory-build &lt;run-id&gt;</span>
              <span className="px-2 py-0.5 text-xs rounded-full bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-300">Phase 5</span>
            </div>
            <p className="text-sm text-slate-600 dark:text-slate-400">
              Per-unit code generation + build/test. Independent units run concurrently (layer-parallel).
              Includes file-glob locks, Python AST symbol-drift detection, and validator-retry feedback loops.
            </p>
          </div>

          <div className="p-4 rounded-lg bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-800">
            <div className="flex items-center gap-2 mb-2">
              <span className="font-mono text-indigo-600 dark:text-indigo-400 font-bold">/factory-review &lt;run-id&gt;</span>
              <span className="px-2 py-0.5 text-xs rounded-full bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-300">Phase 4</span>
            </div>
            <p className="text-sm text-slate-600 dark:text-slate-400">
              Spawns the parallel reviewer pool: code quality, security (OWASP-aware), performance
              (hot-path analysis), and simplification (anti-over-engineering). Merges findings into
              a single report with severity, location, and recommendation.
            </p>
          </div>
        </div>
      </Section>

      <Section title="Operations Commands">
        <div className="space-y-4 mt-4">
          <div className="p-4 rounded-lg bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-800">
            <div className="flex items-center gap-2 mb-2">
              <span className="font-mono text-indigo-600 dark:text-indigo-400 font-bold">/factory-ship &lt;run-id&gt;</span>
              <span className="px-2 py-0.5 text-xs rounded-full bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-300">Phase 6</span>
            </div>
            <p className="text-sm text-slate-600 dark:text-slate-400">
              Release notes, ADRs, CHANGELOG, version proposal, optional CI/CD wiring, and deprecation/migration
              plan. Applies shipping-and-launch, git-workflow, ci-cd, and documentation-and-adrs skills.
            </p>
          </div>
        </div>
      </Section>

      <Section title="Recovery & Utility Commands">
        <div className="space-y-4 mt-4">
          <div className="p-4 rounded-lg bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-800">
            <div className="flex items-center gap-2 mb-2">
              <span className="font-mono text-indigo-600 dark:text-indigo-400 font-bold">/factory-context &lt;run-id&gt;</span>
              <span className="px-2 py-0.5 text-xs rounded-full bg-slate-200 dark:bg-slate-700 text-slate-600 dark:text-slate-400">Utility</span>
            </div>
            <p className="text-sm text-slate-600 dark:text-slate-400">
              Build a contextual snapshot from traceability files (audit.md, state, manifest, timeline)
              to understand project history and decisions before continuing work.
            </p>
          </div>

          <div className="p-4 rounded-lg bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-800">
            <div className="flex items-center gap-2 mb-2">
              <span className="font-mono text-indigo-600 dark:text-indigo-400 font-bold">/factory-state &lt;run-id&gt;</span>
              <span className="px-2 py-0.5 text-xs rounded-full bg-slate-200 dark:bg-slate-700 text-slate-600 dark:text-slate-400">Utility</span>
            </div>
            <p className="text-sm text-slate-600 dark:text-slate-400">
              Show run status: completed stages, current stage, next steps, budget usage, and any
              blocking issues.
            </p>
          </div>

          <div className="p-4 rounded-lg bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-800">
            <div className="flex items-center gap-2 mb-2">
              <span className="font-mono text-indigo-600 dark:text-indigo-400 font-bold">/factory-resume &lt;run-id&gt;</span>
              <span className="px-2 py-0.5 text-xs rounded-full bg-slate-200 dark:bg-slate-700 text-slate-600 dark:text-slate-400">Recovery</span>
            </div>
            <p className="text-sm text-slate-600 dark:text-slate-400">
              Resume an interrupted run from its last checkpoint. Reads the run manifest and restores
              the orchestrator state.
            </p>
          </div>

          <div className="p-4 rounded-lg bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-800">
            <div className="flex items-center gap-2 mb-2">
              <span className="font-mono text-indigo-600 dark:text-indigo-400 font-bold">/factory-replay &lt;run-id&gt; --from &lt;stage&gt;</span>
              <span className="px-2 py-0.5 text-xs rounded-full bg-slate-200 dark:bg-slate-700 text-slate-600 dark:text-slate-400">Recovery</span>
            </div>
            <p className="text-sm text-slate-600 dark:text-slate-400">
              Re-run from a specific stage. Rolls the manifest back and archives prior output handoffs.
            </p>
          </div>
        </div>
      </Section>

      <Section title="Exploration & Meta Commands">
        <div className="space-y-4 mt-4">
          <div className="p-4 rounded-lg bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-800">
            <div className="flex items-center gap-2 mb-2">
              <span className="font-mono text-indigo-600 dark:text-indigo-400 font-bold">/factory-code-tour</span>
              <span className="px-2 py-0.5 text-xs rounded-full bg-slate-200 dark:bg-slate-700 text-slate-600 dark:text-slate-400">Exploration</span>
            </div>
            <p className="text-sm text-slate-600 dark:text-slate-400">
              Dependency-ordered tour of an unfamiliar codebase: foundations &rarr; entry points.
              Uses CodeGraph for fast symbol resolution.
            </p>
          </div>

          <div className="p-4 rounded-lg bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-800">
            <div className="flex items-center gap-2 mb-2">
              <span className="font-mono text-indigo-600 dark:text-indigo-400 font-bold">/factory-self</span>
              <span className="px-2 py-0.5 text-xs rounded-full bg-slate-200 dark:bg-slate-700 text-slate-600 dark:text-slate-400">Meta</span>
            </div>
            <p className="text-sm text-slate-600 dark:text-slate-400">
              Run the AIDLC orchestrator on its own codebase. Use this to add features, fix bugs,
              or refactor the orchestrator scripts themselves.
            </p>
          </div>
        </div>
      </Section>
    </div>
  );
}
