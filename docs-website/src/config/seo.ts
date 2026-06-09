export type PageMeta = {
  id: string;
  title: string;
  description: string;
  path: string;
  keywords?: string;
  type?: 'website' | 'article';
};

export const SITE = {
  name: 'AIDLC-Factory',
  tagline: 'Multi-Agent AI-Driven Development Life Cycle',
  url: import.meta.env.VITE_SITE_URL || 'https://mbg999.github.io/aidlc-factory',
  description:
    'AIDLC-Factory is a multi-agent software-development workflow that takes a feature request from specification to plan to code to review to ship, with human approval gates and contract-validated handoffs.',
  language: 'en',
  locale: 'en_US',
  twitterHandle: '@aidlc_factory',
};

export const PAGES_META: PageMeta[] = [
  {
    id: 'intro',
    title: 'Introduction',
    description:
      'AIDLC-Factory is a multi-agent orchestrator for AI-driven development. 14 specialized agents collaborate to drive your project from spec to ship.',
    path: '/',
    keywords: 'AIDLC, AI-driven development, multi-agent, software factory, AI development workflow',
    type: 'website',
  },
  {
    id: 'install',
    title: 'Installation',
    description:
      'Install AIDLC-Factory in any project with pipx or uv. One-line installer with flags for agent skills, CodeGraph, Engram, and design-system tokens.',
    path: '/installation',
    keywords: 'install AIDLC, pipx, uv, setup, configuration, CLI installer',
    type: 'article',
  },
  {
    id: 'usage',
    title: 'Usage Guide',
    description:
      'Complete usage guide for AIDLC-Factory slash commands: factory-spec, factory-plan, factory-build, factory-review, factory-ship.',
    path: '/usage',
    keywords: 'AIDLC usage, factory commands, AI development workflow, slash commands',
    type: 'article',
  },
  {
    id: 'commands',
    title: 'Commands Reference',
    description:
      'Full reference for all AIDLC-Factory slash commands: factory-spec, factory-plan, factory-build, factory-review, factory-ship, factory-resume, and more.',
    path: '/commands',
    keywords: 'AIDLC commands, factory CLI, slash commands reference',
    type: 'article',
  },
  {
    id: 'architecture',
    title: 'Architecture',
    description:
      'AIDLC-Factory architecture: flat orchestration pattern, 14 stage subagents, JSON Schema contracts, skills layer, parallel reviewer pool, and multi-tool support.',
    path: '/architecture',
    keywords: 'AIDLC architecture, orchestration, stage pipeline, contracts, skills layer, parallel processing',
    type: 'article',
  },
  {
    id: 'configuration',
    title: 'Configuration',
    description:
      'Configure AIDLC-Factory: model budgets, stage assignments, concurrency limits, tool adapters, and environment variables.',
    path: '/configuration',
    keywords: 'AIDLC configuration, model budget, YAML config, environment variables, tool setup',
    type: 'article',
  },
  {
    id: 'examples',
    title: 'Examples',
    description:
      'Real-world AIDLC-Factory examples: end-to-end feature delivery from specification through plan, build, review, and ship.',
    path: '/examples',
    keywords: 'AIDLC examples, demo, feature delivery, end-to-end workflow, AI development example',
    type: 'article',
  },
];
