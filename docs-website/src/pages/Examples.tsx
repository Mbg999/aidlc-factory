import { Section, CodeBlock, Card } from "../components/DocUI";

export default function Examples() {
  return (
    <div className="animate-in fade-in slide-in-from-bottom-4 duration-500">
      <Section title="Example: Add User Authentication">
        <p>
          A complete spec-to-ship run for adding JWT authentication to a Node.js API:
        </p>

        <h3 className="text-lg font-medium mt-6 mb-3 text-slate-800 dark:text-slate-200">1. Requirements</h3>
        <CodeBlock 
          language="text"
          code={`/factory-spec "Add user authentication with JWT to the Express API"`}
        />
        <p className="mt-2">
          The requirements-analyst runs an adaptive Q&A session covering Purpose, Needs, Limits,
          Expectations, Context, Risks, Acceptance, and Unknowns. It flags weasel words
          ("robust", "secure", "simple") and converts them to quantifiable criteria.
        </p>
        <p className="mt-2">
          Output: <code>aidlc-docs/&lt;run-id&gt;-requirements.md</code> &mdash; approved by you &rarr; commit.
        </p>

        <h3 className="text-lg font-medium mt-6 mb-3 text-slate-800 dark:text-slate-200">2. Planning</h3>
        <CodeBlock 
          language="text"
          code={`/factory-plan <run-id>`}
        />
        <p className="mt-2">
          The workflow-planner generates:
        </p>
        <ul className="list-disc pl-6 space-y-2 mt-2">
          <li>Application design: auth middleware, user service, token utilities</li>
          <li>Execution plan with Mermaid sequence diagram</li>
          <li>Unit decomposition: (1) auth middleware, (2) user service + repository, (3) login/register routes, (4) tests</li>
        </ul>
        <p className="mt-2">
          Output: <code>aidlc-docs/&lt;run-id&gt;-plan.md</code> &mdash; approved by you &rarr; commit.
        </p>

        <h3 className="text-lg font-medium mt-6 mb-3 text-slate-800 dark:text-slate-200">3. Build</h3>
        <CodeBlock 
          language="text"
          code={`/factory-build <run-id>`}
        />
        <p className="mt-2">
          Layer-parallel code generation. Units 1 and 2 can run concurrently (auth middleware and
          user service are independent). Unit 3 waits for both. Unit 4 (tests) runs after all code.
        </p>
        <p className="mt-2">
          Each code slice goes through validator-retry: TypeScript compilation errors from
          hallucinated APIs are fed back to the generator for correction before the stage exits.
        </p>

        <h3 className="text-lg font-medium mt-6 mb-3 text-slate-800 dark:text-slate-200">4. Review</h3>
        <CodeBlock 
          language="text"
          code={`/factory-review <run-id>`}
        />
        <p className="mt-2">
          Four parallel reviewers produce findings:
        </p>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mt-4">
          <div className="p-4 rounded-lg border border-slate-200 dark:border-slate-800">
            <p className="font-semibold text-slate-900 dark:text-white text-sm">Code Reviewer</p>
            <p className="text-xs text-slate-600 dark:text-slate-400 mt-1">Flags missing input validation in login route, suggests middleware pattern.</p>
          </div>
          <div className="p-4 rounded-lg border border-slate-200 dark:border-slate-800">
            <p className="font-semibold text-slate-900 dark:text-white text-sm">Security Reviewer</p>
            <p className="text-xs text-slate-600 dark:text-slate-400 mt-1">Confirms bcrypt for password hashing, flags missing rate limiting on login endpoint.</p>
          </div>
          <div className="p-4 rounded-lg border border-slate-200 dark:border-slate-800">
            <p className="font-semibold text-slate-900 dark:text-white text-sm">Performance Reviewer</p>
            <p className="text-xs text-slate-600 dark:text-slate-400 mt-1">Recommends caching token blacklist in Redis instead of DB lookups.</p>
          </div>
          <div className="p-4 rounded-lg border border-slate-200 dark:border-slate-800">
            <p className="font-semibold text-slate-900 dark:text-white text-sm">Simplification Reviewer</p>
            <p className="text-xs text-slate-600 dark:text-slate-400 mt-1">Suggests flattening middleware factory to a simpler function.</p>
          </div>
        </div>

        <h3 className="text-lg font-medium mt-6 mb-3 text-slate-800 dark:text-slate-200">5. Ship</h3>
        <CodeBlock 
          language="text"
          code={`/factory-ship <run-id>`}
        />
        <p className="mt-2">
          Produces ADRs for the auth design decisions, updates CHANGELOG, proposes a version bump,
          and generates release notes summarizing what was built.
        </p>
      </Section>

      <Section title="Example: Codebase Tour">
        <p>
          Explore an unfamiliar codebase with dependency-ordered walkthrough:
        </p>
        <CodeBlock 
          language="text"
          code={`/factory-code-tour
# Output: foundations → utilities → services → entry points
# Each symbol is linked to its source location`}
        />
      </Section>

      <Section title="Example: Self-Hosting the Orchestrator">
        <p>
          Run the AIDLC orchestrator on its own codebase to add a feature or fix a bug:
        </p>
        <CodeBlock 
          language="text"
          code={`/factory-self
# Equivalent to /factory-spec → /factory-plan → /factory-build
# but targeting the aidlc-factory repository itself`}
        />
      </Section>

      <Section title="Example: Brownfield Reverse Engineering">
        <p>
          When installing AIDLC-Factory into an existing project, the orchestrator detects
          brownfield state and runs reverse-engineering first:
        </p>
        <CodeBlock 
          language="text"
          code={`/factory-spec "Add payment processing with Stripe"

# Automatically triggers reverse-engineering phase:
# 1. Scans tech stack (detects Express, PostgreSQL, React)
# 2. Produces architecture doc of existing code
# 3. Component inventory and API documentation
# 4. Then proceeds with standard spec → plan → build → review → ship`}
        />
      </Section>

      <Section title="Example: Resuming After Interruption">
        <p>
          If your session times out mid-build, resume right where you left off:
        </p>
        <CodeBlock 
          language="text"
          code={`/factory-state <run-id>
# Shows: build stage 60% complete, 2 of 4 units done

/factory-resume <run-id>
# Continues from unit 3 without re-running units 1-2`}
        />
      </Section>
    </div>
  );
}
