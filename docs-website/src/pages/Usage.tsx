import { Section, CodeBlock, Card } from "../components/DocUI";

export default function Usage() {
  return (
    <div className="animate-in fade-in slide-in-from-bottom-4 duration-500">
      <Section title="Development Lifecycle">
        <p>
          AIDLC-Factory follows the <strong>AI-Driven Development Life Cycle</strong> through three
          phases: <strong>Inception</strong> (what to build), <strong>Construction</strong> (how to
          build it), and <strong>Operations</strong> (deployment and monitoring).
        </p>
        <p>
          Each phase is broken into stages, with human approval gates between them. The orchestrator
          pauses after each stage, presents the artifact for review, and proceeds only on explicit
          approval.
        </p>
      </Section>

      <Section title="The Orchestrator Flow">
        <p>
          A typical session follows this sequence:
        </p>
        <div className="space-y-4 mt-4">
          <div className="p-4 rounded-lg border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900">
            <div className="flex items-center gap-2 mb-1">
              <span className="px-2 py-0.5 text-xs font-mono bg-indigo-100 text-indigo-700 dark:bg-indigo-900/40 dark:text-indigo-300 rounded">Phase 0</span>
              <span className="font-semibold text-slate-900 dark:text-white">Inception</span>
            </div>
            <p className="text-sm text-slate-600 dark:text-slate-400">
              <strong>Requirements:</strong> <code>/factory-spec "feature"</code> &rarr; adaptive Q&A session &rarr; requirements document approved by you.
            </p>
            <p className="text-sm text-slate-600 dark:text-slate-400 mt-1">
              <strong>Planning:</strong> <code>/factory-plan &lt;run-id&gt;</code> &rarr; application design, execution plan with Mermaid diagram, per-unit decomposition. Reviewed and approved by you.
            </p>
          </div>
          <div className="p-4 rounded-lg border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900">
            <div className="flex items-center gap-2 mb-1">
              <span className="px-2 py-0.5 text-xs font-mono bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-300 rounded">Phase 1</span>
              <span className="font-semibold text-slate-900 dark:text-white">Construction</span>
            </div>
            <p className="text-sm text-slate-600 dark:text-slate-400">
              <strong>Code Generation:</strong> <code>/factory-build &lt;run-id&gt;</code> &rarr; per-unit code generation with file-glob locks, parallel layers, AST drift detection. Each slice goes through TDD + validator-retry.
            </p>
            <p className="text-sm text-slate-600 dark:text-slate-400 mt-1">
              <strong>Review:</strong> <code>/factory-review &lt;run-id&gt;</code> &rarr; four parallel reviewers (code quality, security, performance, simplification). Merged findings presented for fixes.
            </p>
          </div>
          <div className="p-4 rounded-lg border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900">
            <div className="flex items-center gap-2 mb-1">
              <span className="px-2 py-0.5 text-xs font-mono bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-300 rounded">Phase 2</span>
              <span className="font-semibold text-slate-900 dark:text-white">Operations</span>
            </div>
            <p className="text-sm text-slate-600 dark:text-slate-400">
              <strong>Ship:</strong> <code>/factory-ship &lt;run-id&gt;</code> &rarr; release notes, ADRs, CHANGELOG, version proposal, optional CI/CD wiring.
            </p>
          </div>
        </div>
      </Section>

      <Section title="Stage Subagents">
        <p>
          The orchestrator spawns 14 specialized subagents across the lifecycle:
        </p>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mt-4">
          <div className="p-4 rounded-lg bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-800">
            <h4 className="font-semibold text-slate-900 dark:text-white text-sm mb-1">workspace-scout</h4>
            <p className="text-xs text-slate-600 dark:text-slate-400">Detects greenfield vs brownfield, analyzes tech stack, and decides the next AIDLC phase.</p>
          </div>
          <div className="p-4 rounded-lg bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-800">
            <h4 className="font-semibold text-slate-900 dark:text-white text-sm mb-1">requirements-analyst</h4>
            <p className="text-xs text-slate-600 dark:text-slate-400">Adaptive requirements elicitation with Socratic probing, ambiguity detection, and assumption mining.</p>
          </div>
          <div className="p-4 rounded-lg bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-800">
            <h4 className="font-semibold text-slate-900 dark:text-white text-sm mb-1">workflow-planner</h4>
            <p className="text-xs text-slate-600 dark:text-slate-400">Generates the execution plan with Mermaid visualization and decomposed task tree with acceptance criteria.</p>
          </div>
          <div className="p-4 rounded-lg bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-800">
            <h4 className="font-semibold text-slate-900 dark:text-white text-sm mb-1">code-generator</h4>
            <p className="text-xs text-slate-600 dark:text-slate-400">Per-unit construction: functional design, NFRs, code generation, and tests. Runs TDD thin slices with validator-retry.</p>
          </div>
          <div className="p-4 rounded-lg bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-800">
            <h4 className="font-semibold text-slate-900 dark:text-white text-sm mb-1">build-test-agent</h4>
            <p className="text-xs text-slate-600 dark:text-slate-400">Runs build + tests. Applies debugging-and-error-recovery skill on failures. Produces build-instructions.md.</p>
          </div>
          <div className="p-4 rounded-lg bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-800">
            <h4 className="font-semibold text-slate-900 dark:text-white text-sm mb-1">reviewer-{'{code,security,performance,simplifier}'}</h4>
            <p className="text-xs text-slate-600 dark:text-slate-400">Four parallel reviewers covering code quality, OWASP security, hot-path performance, and over-engineering detection.</p>
          </div>
          <div className="p-4 rounded-lg bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-800">
            <h4 className="font-semibold text-slate-900 dark:text-white text-sm mb-1">ship-agent</h4>
            <p className="text-xs text-slate-600 dark:text-slate-400">Release notes, ADRs, CHANGELOG, version proposal, CI/CD wiring, and deprecation/migration plans.</p>
          </div>
          <div className="p-4 rounded-lg bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-800">
            <h4 className="font-semibold text-slate-900 dark:text-white text-sm mb-1">reverse-engineer</h4>
            <p className="text-xs text-slate-600 dark:text-slate-400">Brownfield support: produces architecture docs, component inventory, API docs, and tech stack from existing code.</p>
          </div>
        </div>
      </Section>

      <Section title="Auto-Commit on Approval">
        <p>
          When you explicitly approve a stage (signals: <code>approve</code>, <code>go ahead</code>,
          <code>lgtm</code>, or equivalent.), the orchestrator stages
          and commits the produced artifacts with a stage-tagged message. Commits never fire on internal
          <code>status: complete</code> alone.
        </p>
        <CodeBlock 
          language="text"
          code={`# Approval triggers:
approve
continue
go ahead
lgtm
or equivalent

# Commit pattern:
git commit -m "feat(requirements): user authentication with JWT"`}
        />
      </Section>
    </div>
  );
}
