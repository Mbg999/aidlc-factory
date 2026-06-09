export type PageConfig = {
  id: string;
  title: string;
  icon: string;
};

export const PAGES: PageConfig[] = [
  { id: 'intro', title: 'Introduction', icon: 'BookOpen' },
  { id: 'install', title: 'Installation', icon: 'Download' },
  { id: 'usage', title: 'Usage Guide', icon: 'Terminal' },
  { id: 'commands', title: 'Commands', icon: 'Terminal' },
  { id: 'architecture', title: 'Architecture', icon: 'BookOpen' },
  { id: 'configuration', title: 'Configuration', icon: 'Settings' },
  { id: 'examples', title: 'Examples', icon: 'Code' },
];
