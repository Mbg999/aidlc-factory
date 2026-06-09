import { Section, CodeBlock, Card, Note } from "../components/DocUI";

export default function Installation() {
  return (
    <div className="animate-in fade-in slide-in-from-bottom-4 duration-500">
      <Section title="Prerequisites">
        <ul className="list-disc pl-6 space-y-2 mt-2">
          <li>
            <strong>
              <a
                href="https://www.python.org/downloads/"
                target="_blank"
                rel="noopener noreferrer"
              >
                Python 3.10+
              </a>
            </strong>{" "}
            (a <code>.venv</code> is created automatically by the installer)
          </li>
          <li>
            <strong>
              <a
                href="https://git-scm.com/"
                target="_blank"
                rel="noopener noreferrer"
              >
                Git
              </a>
            </strong>{" "}
            (auto-commit on approval requires a git repo in the destination)
          </li>
          <li>
            <strong>
              <a
                href="https://nodejs.org/"
                target="_blank"
                rel="noopener noreferrer"
              >
                Node &ge; 18
              </a>
            </strong>{" "}
            — only needed for CodeGraph (<code>--with-codegraph</code>)
          </li>
          <li>
            <strong>An agentic coding tool</strong> — Claude Code, Cursor,
            GitHub Copilot, OpenCode, or Codex
          </li>
          <li>
            <strong>
              <a
                href="https://github.com/Gentleman-Programming/engram"
                target="_blank"
                rel="noopener noreferrer"
              >
                Engram
              </a>
            </strong>{" "}
            — required for persistent cross-session memory (install per your
            tool)
          </li>
        </ul>
      </Section>

      <Section title="One-Line Install (Recommended)">
        <p className="mb-2">
          No cloning, no venv setup, no <code>pip install</code>. You can
          install directly into your project with pipx from{" "}
          <a
            href="https://pypi.org/project/aidlc-factory-installer/"
            target="_blank"
            rel="noopener noreferrer"
          >
            https://pypi.org/project/aidlc-factory-installer/
          </a>
          :
        </p>
        <CodeBlock language="bash" code={`pipx run aidlc-factory-installer`} />
        <p className="mt-4">Or with uv (Rust-based, faster cold start):</p>
        <CodeBlock language="bash" code={`uvx aidlc-factory-installer`} />
        <p className="mt-4">If you don't have pipx yet:</p>
        <CodeBlock
          language="bash"
          code={`pip install pipx && pipx ensurepath
# Or: brew install pipx && pipx ensurepath`}
        />
      </Section>

      <Section title="Traditional Install">
        <p>Clone the repository and run the installer locally:</p>
        <CodeBlock
          language="bash"
          code={`git clone https://github.com/Mbg999/aidlc-factory.git
cd aidlc-factory
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python3 aidlc-scripts/install_aidlc.py \\
    --tool claude \\
    --dest /path/to/your/project \\
    --with-agent-skills \\
    --with-codegraph \\
    --with-engram \\
    --yes`}
        />
      </Section>

      <Section title="Installer Flags">
        <div className="overflow-x-auto my-4">
          <table className="w-full text-sm border-collapse">
            <thead>
              <tr className="border-b border-slate-200 dark:border-slate-800">
                <th className="text-left py-2 pr-4 font-medium text-slate-900 dark:text-white">
                  Flag
                </th>
                <th className="text-left py-2 pr-4 font-medium text-slate-900 dark:text-white">
                  Default
                </th>
                <th className="text-left py-2 font-medium text-slate-900 dark:text-white">
                  Description
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200 dark:divide-slate-800">
              <tr>
                <td className="py-2 pr-4 font-mono text-indigo-600 dark:text-indigo-400">
                  --tool
                </td>
                <td className="py-2 pr-4">required</td>
                <td className="py-2 text-slate-600 dark:text-slate-400">
                  Target tool: claude, cursor, copilot, opencode, codex
                </td>
              </tr>
              <tr>
                <td className="py-2 pr-4 font-mono text-indigo-600 dark:text-indigo-400">
                  --dest
                </td>
                <td className="py-2 pr-4">
                  <code>.</code>
                </td>
                <td className="py-2 text-slate-600 dark:text-slate-400">
                  Project to install into
                </td>
              </tr>
              <tr>
                <td className="py-2 pr-4 font-mono text-indigo-600 dark:text-indigo-400">
                  --with-agent-skills
                </td>
                <td className="py-2 pr-4">on</td>
                <td className="py-2 text-slate-600 dark:text-slate-400">
                  Install engineering-process skills
                </td>
              </tr>
              <tr>
                <td className="py-2 pr-4 font-mono text-indigo-600 dark:text-indigo-400">
                  --with-orchestrator
                </td>
                <td className="py-2 pr-4">prompt</td>
                <td className="py-2 text-slate-600 dark:text-slate-400">
                  Install the multi-agent orchestrator
                </td>
              </tr>
              <tr>
                <td className="py-2 pr-4 font-mono text-indigo-600 dark:text-indigo-400">
                  --with-codegraph
                </td>
                <td className="py-2 pr-4">off</td>
                <td className="py-2 text-slate-600 dark:text-slate-400">
                  Install CodeGraph code knowledge graph
                </td>
              </tr>
              <tr>
                <td className="py-2 pr-4 font-mono text-indigo-600 dark:text-indigo-400">
                  --with-engram
                </td>
                <td className="py-2 pr-4">off</td>
                <td className="py-2 text-slate-600 dark:text-slate-400">
                  Set up Engram persistent memory
                </td>
              </tr>
              <tr>
                <td className="py-2 pr-4 font-mono text-indigo-600 dark:text-indigo-400">
                  --with-design-system
                </td>
                <td className="py-2 pr-4">on</td>
                <td className="py-2 text-slate-600 dark:text-slate-400">
                  Install design-system tokens + UI skills
                </td>
              </tr>
              <tr>
                <td className="py-2 pr-4 font-mono text-indigo-600 dark:text-indigo-400">
                  --with-figma-mcp
                </td>
                <td className="py-2 pr-4">off</td>
                <td className="py-2 text-slate-600 dark:text-slate-400">
                  Install Figma MCP server config
                </td>
              </tr>
              <tr>
                <td className="py-2 pr-4 font-mono text-indigo-600 dark:text-indigo-400">
                  --force
                </td>
                <td className="py-2 pr-4">off</td>
                <td className="py-2 text-slate-600 dark:text-slate-400">
                  Re-install / upgrade, overwrite existing config
                </td>
              </tr>
              <tr>
                <td className="py-2 pr-4 font-mono text-indigo-600 dark:text-indigo-400">
                  --dry-run
                </td>
                <td className="py-2 pr-4">off</td>
                <td className="py-2 text-slate-600 dark:text-slate-400">
                  Print planned actions without writing files
                </td>
              </tr>
              <tr>
                <td className="py-2 pr-4 font-mono text-indigo-600 dark:text-indigo-400">
                  --yes
                </td>
                <td className="py-2 pr-4">off</td>
                <td className="py-2 text-slate-600 dark:text-slate-400">
                  Skip all interactive prompts
                </td>
              </tr>
            </tbody>
          </table>
        </div>
        <Note>
          <strong>Note:</strong> Every external dependency degrades gracefully.
          The orchestrator still runs if CodeGraph or Engram is missing — those
          stages just lose the corresponding intelligence.
        </Note>
      </Section>

      <Section title="What Gets Installed">
        <p>
          The installer wires the orchestrator into your project. The exact
          paths vary by <code>--tool</code>:
        </p>
        <div className="overflow-x-auto my-4">
          <table className="w-full text-sm border-collapse">
            <thead>
              <tr className="border-b border-slate-200 dark:border-slate-800">
                <th className="text-left py-2 pr-4 font-medium text-slate-900 dark:text-white">
                  Tool
                </th>
                <th className="text-left py-2 pr-4 font-medium text-slate-900 dark:text-white">
                  Agents
                </th>
                <th className="text-left py-2 font-medium text-slate-900 dark:text-white">
                  Commands
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200 dark:divide-slate-800">
              <tr>
                <td className="py-2 pr-4 font-mono">claude</td>
                <td className="py-2 pr-4">
                  <code>.claude/agents/</code>
                </td>
                <td className="py-2">
                  <code>.claude/commands/</code>
                </td>
              </tr>
              <tr>
                <td className="py-2 pr-4 font-mono">cursor</td>
                <td className="py-2 pr-4">
                  <code>.cursor/agents/</code>
                </td>
                <td className="py-2">
                  <code>.cursor/commands/</code>
                </td>
              </tr>
              <tr>
                <td className="py-2 pr-4 font-mono">copilot</td>
                <td className="py-2 pr-4">
                  <code>.github/agents/</code>
                </td>
                <td className="py-2">
                  <code>.github/prompts/</code>
                </td>
              </tr>
              <tr>
                <td className="py-2 pr-4 font-mono">opencode</td>
                <td className="py-2 pr-4">
                  <code>.opencode/agents/</code>
                </td>
                <td className="py-2">
                  <code>.opencode/commands/</code>
                </td>
              </tr>
              <tr>
                <td className="py-2 pr-4 font-mono">codex</td>
                <td className="py-2 pr-4">
                  <code>.codex/agents/</code>
                </td>
                <td className="py-2">
                  <code>.codex/config.toml</code>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </Section>

      <Section title="Verify the Install">
        <CodeBlock
          language="bash"
          code={`# Check orchestrator wiring
python3 aidlc-scripts/factory_validate.py

# List discovered agents
python3 aidlc-scripts/factory_agent_discover.py list

# Inside your agentic coding tool:
/factory-help
/factory-onboarding`}
        />
      </Section>

      <Section title="Environment Setup (Contributors)">
        <p>If you cloned the repo to contribute to AIDLC itself:</p>
        <CodeBlock
          language="bash"
          code={`python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Verify
pytest tests/`}
        />
      </Section>
    </div>
  );
}
