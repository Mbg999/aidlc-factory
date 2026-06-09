import { ReactNode, useState } from "react";
import { Check, Copy } from "lucide-react";

export function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="mb-10">
      <h2 className="text-2xl font-semibold tracking-tight text-slate-900 dark:text-white mb-4 border-b border-slate-200 dark:border-slate-800 pb-2">
        {title}
      </h2>
      <div className="space-y-4 text-slate-700 dark:text-slate-300 leading-relaxed">
        {children}
      </div>
    </section>
  );
}

export function CodeBlock({ code, language = "bash" }: { code: string; language?: string }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(code);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error('Failed to copy code:', err);
    }
  };

  return (
    <div className="relative my-6 rounded-lg bg-slate-900 border border-slate-800 overflow-hidden">
      <div className="flex items-center justify-between px-4 py-2 bg-slate-800/50 border-b border-slate-800">
        <span className="text-xs text-slate-400 font-mono">{language}</span>
        <button
          onClick={handleCopy}
          className="text-slate-400 hover:text-slate-200 transition-colors flex items-center gap-1.5 cursor-pointer"
          title="Copy code"
        >
          {copied ? <Check className="w-4 h-4 text-emerald-400" /> : <Copy className="w-4 h-4" />}
          <span className="text-xs">{copied ? "Copied!" : "Copy"}</span>
        </button>
      </div>
      <pre className="p-4 overflow-x-auto text-sm text-slate-50 font-mono leading-relaxed">
        <code>{code}</code>
      </pre>
    </div>
  );
}

export function Card({ title, description, features }: { title: string, description: string, features?: string[] }) {
  return (
    <div className="p-6 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 shadow-sm hover:shadow-md transition-shadow">
      <h3 className="text-xl font-medium text-slate-900 dark:text-white mb-2">{title}</h3>
      <p className="text-slate-600 dark:text-slate-400 mb-4 text-sm">{description}</p>
      {features && (
        <ul className="space-y-2">
          {features.map((feature, i) => (
            <li key={i} className="flex items-start text-sm text-slate-700 dark:text-slate-300">
              <Check className="w-5 h-5 text-indigo-500 mr-2 shrink-0" />
              <span>{feature}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

export function Note({ children }: { children: ReactNode }) {
  return (
    <div className="mt-4 text-sm px-4 py-3 bg-amber-50 dark:bg-amber-950/30 text-amber-800 dark:text-amber-400 rounded-lg border border-amber-200 dark:border-amber-800">
      {children}
    </div>
  );
}
