import { Section, CodeBlock, Card } from "../components/DocUI";

export default function Introduction() {
  return (
    <div className="animate-in fade-in slide-in-from-bottom-4 duration-500">
      <div className="relative w-full bg-[#000007] mb-8 rounded-2xl overflow-hidden">
        <div className="text-white shadow-lg absolute z-20 pt-8 pl-8">
          <h2 className="text-4xl font-bold tracking-tight mb-4">
            AIDLC-Factory
          </h2>
          <p className="text-lg text-indigo-100 max-w-2xl">
            AI-Driven Development Life Cycle &mdash; the multi-agent factory.
          </p>
        </div>
        <div className="absolute z-10 inset-0 bg-gradient-to-b from-slate-900/80 via-slate-900/40 to-transparent pointer-events-none" />

        <div className="relative w-full bg-[#000007] mb-8 rounded-2xl overflow-hidden">
          <div
            className="text-white shadow-lg relative overflow-hidden bg-contain bg-center bg-no-repeat aspect-square max-h-[500px] mx-auto flex flex-col justify-start p-8"
            style={{
              backgroundImage: `url(${import.meta.env.BASE_URL}assets/images/hero.png)`,
            }}
          ></div>
        </div>
      </div>

      <Section title="What is AIDLC-Factory?">
        <p>
          AIDLC-Factory is a multi-agent software-development workflow that
          takes a feature request from specification &rarr; plan &rarr; code
          &rarr; review &rarr; ship, with human approval gates between every
          stage and traceable artifacts at every step.
        </p>
        <p>
          Rather than rigid pipelines, it orchestrates 14 specialized stage
          subagents that collaborate to drive your project from conception to
          deployment. Each stage produces contract-validated handoffs, so
          nothing is lost between phases.
        </p>
        <p>
          Based on the <strong>AWS Labs AI-DLC methodology</strong> (v0.1.8), it
          adds a multi-agent orchestrator, a skills enforcement layer,
          hallucination prevention, CodeGraph integration, persistent memory
          (Engram), and parallel reviewer pools.
        </p>
      </Section>

      <Section title="Key Features">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mt-4">
          <Card
            title="Multi-Agent Orchestrator"
            description="14 specialized subagents — requirements analyst, workflow planner, code generator, reviewers, ship agent — collaborating in sequence."
            features={[
              "Contract-validated handoffs between every stage",
              "Parallel-safe code generation with file-glob locks",
              "Kill and resume: interrupted runs resume from the last checkpoint",
            ]}
          />
          <Card
            title="Parallel Reviewer Pool"
            description="Code quality, security, performance, and simplification reviewers run concurrently."
            features={[
              "Four-axis review with merged findings report",
              "Security scanning: gitleaks, semgrep, grype, bandit, checkov",
              "Static type-check retry loop eliminates hallucinated APIs",
            ]}
          />
          <Card
            title="Persistent Memory"
            description="Engram captures decisions, ADRs, and conventions across sessions."
            features={[
              "Searchable cross-session knowledge",
              "Automatic context injection for stage agents",
              "Never ask the same question twice",
            ]}
          />
          <Card
            title="Codebase Intelligence"
            description="CodeGraph provides a semantic knowledge graph for instant symbol resolution."
            features={[
              "92% fewer tool calls for code exploration",
              "Impact analysis before any change",
              "Dead-code detection and caller tracing",
            ]}
          />
          <Card
            title="Skills Enforcement"
            description="Engineering process skills auto-attach per stage — TDD, security, ADRs, design tokens, and more."
            features={[
              "22 bundled custom skills in this fork",
              "Framework-specific skills via autoskills sync",
              "Version-aware library docs via Context7 MCP",
            ]}
          />
          <Card
            title="Multi-Tool Runtime"
            description="Runs natively on Claude Code, Cursor, GitHub Copilot, OpenCode, and Codex."
            features={[
              "Per-tool subagent trees auto-configured by the installer",
              "Pluggable executor adapters for tool-agnostic orchestration",
              "Slash commands available in every supported tool",
            ]}
          />
        </div>
      </Section>

      <Section title="The Development Lifecycle">
        <p>A complete spec-to-ship sequence follows this flow:</p>
        <div className="flex flex-wrap items-center justify-center gap-2 my-6 text-sm font-mono">
          <span className="px-3 py-1.5 bg-indigo-100 text-indigo-700 dark:bg-indigo-900/40 dark:text-indigo-300 rounded-full">
            spec
          </span>
          <span className="text-slate-400">&rarr;</span>
          <span className="px-3 py-1.5 bg-indigo-100 text-indigo-700 dark:bg-indigo-900/40 dark:text-indigo-300 rounded-full">
            plan
          </span>
          <span className="text-slate-400">&rarr;</span>
          <span className="px-3 py-1.5 bg-indigo-100 text-indigo-700 dark:bg-indigo-900/40 dark:text-indigo-300 rounded-full">
            build
          </span>
          <span className="text-slate-400">&rarr;</span>
          <span className="px-3 py-1.5 bg-indigo-100 text-indigo-700 dark:bg-indigo-900/40 dark:text-indigo-300 rounded-full">
            review
          </span>
          <span className="text-slate-400">&rarr;</span>
          <span className="px-3 py-1.5 bg-indigo-100 text-indigo-700 dark:bg-indigo-900/40 dark:text-indigo-300 rounded-full">
            ship
          </span>
        </div>
        <CodeBlock
          language="text"
          code={`/factory-spec "<feature>"   # Requirements analysis Q&A → spec
/factory-plan <run-id>     # Application design + execution plan
/factory-build <run-id>    # Per-unit code generation + build/test
/factory-review <run-id>   # Parallel reviewer pool → merged findings
/factory-ship <run-id>     # Release notes + ADRs + CHANGELOG`}
        />
      </Section>

      <Section title="Quick Start">
        <p>Install AIDLC-Factory in any project with one command:</p>
        <CodeBlock language="bash" code={`pipx run aidlc-factory-installer`} />
        <p>Then open your agentic coding tool and run:</p>
        <CodeBlock
          language="text"
          code={`/factory-onboarding
/factory-spec "Add user authentication with JWT"`}
        />
      </Section>
    </div>
  );
}
