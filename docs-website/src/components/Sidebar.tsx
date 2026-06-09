import React from "react";
import { PAGES } from "../config/pages";
import { BookOpen, Download, Terminal, Code, Settings, Github } from "lucide-react";

const ICON_MAP: Record<string, React.ElementType> = {
  BookOpen,
  Download,
  Terminal,
  Code,
  Settings
};

export function Sidebar({ 
  currentPage, 
  setPage, 
  isOpen, 
  setIsOpen 
}: { 
  currentPage: string, 
  setPage: (p: string) => void,
  isOpen: boolean,
  setIsOpen: (o: boolean) => void
}) {
  return (
    <>
      {isOpen && (
        <div 
          className="fixed inset-0 bg-slate-900/50 backdrop-blur-sm z-40 lg:hidden"
          onClick={() => setIsOpen(false)}
        />
      )}

      <aside className={`
        fixed top-0 left-0 z-50 h-screen w-72 bg-slate-50 dark:bg-slate-900 border-r border-slate-200 dark:border-slate-800 
        transform transition-transform duration-300 ease-in-out lg:translate-x-0
        ${isOpen ? 'translate-x-0' : '-translate-x-full'}
      `}>
        <div className="h-16 flex items-center px-6 border-b border-slate-200 dark:border-slate-800">
          <img src="/assets/images/logo.png" alt="AIDLC Factory" className="w-8 h-8 mr-3" />
          <span className="font-semibold text-slate-900 dark:text-white tracking-wide">AIDLC Factory</span>
        </div>

        <nav className="p-4 space-y-1">
          <p className="px-3 py-2 text-xs font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400">
            Navigation
          </p>
          {PAGES.map(page => {
            const Icon = ICON_MAP[page.icon];
            const isActive = currentPage === page.id;
            return (
              <button
                key={page.id}
                onClick={() => {
                  setPage(page.id);
                  setIsOpen(false);
                }}
                className={`
                  w-full flex items-center px-3 py-2 rounded-md transition-colors duration-200 text-sm font-medium
                  ${isActive 
                    ? 'bg-indigo-50 text-indigo-700 dark:bg-indigo-500/10 dark:text-indigo-400' 
                    : 'text-slate-700 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800/50'}
                `}
              >
                {Icon && <Icon className={`w-4 h-4 mr-3 ${isActive ? 'text-indigo-600 dark:text-indigo-400' : 'text-slate-400'}`} />}
                {page.title}
              </button>
            );
          })}
        </nav>

        <div className="absolute bottom-0 left-0 right-0 p-4 border-t border-slate-200 dark:border-slate-800">
          <a
            href="https://github.com/Mbg999/aidlc-factory"
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center justify-center w-full px-4 py-2 text-sm font-medium text-slate-700 bg-white border border-slate-300 rounded-md shadow-sm hover:bg-slate-50 dark:bg-slate-800 dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-700 transition"
          >
            <Github className="w-4 h-4 mr-2" />
            View on GitHub
          </a>
        </div>
      </aside>
    </>
  );
}
