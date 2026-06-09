import { useState, useLayoutEffect, useRef } from 'react';
import { HelmetProvider } from 'react-helmet-async';
import { Menu } from 'lucide-react';
import { Sidebar } from './components/Sidebar';
import { SEO, getDocSchema } from './components/SEO';
import Introduction from './pages/Introduction';
import Installation from './pages/Installation';
import Usage from './pages/Usage';
import Commands from './pages/Commands';
import Architecture from './pages/Architecture';
import Configuration from './pages/Configuration';
import Examples from './pages/Examples';
import { PAGES } from './config/pages';
import { PAGES_META } from './config/seo';

export default function App() {
  const [currentPage, setCurrentPage] = useState('intro');
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const mainRef = useRef<HTMLElement>(null);

  useLayoutEffect(() => {
    const el = mainRef.current;
    if (el) el.scrollTop = 0;
    document.documentElement.scrollTop = 0;
    document.body.scrollTop = 0;
  }, [currentPage]);

  const renderContent = () => {
    switch (currentPage) {
      case 'intro': return <Introduction />;
      case 'install': return <Installation />;
      case 'usage': return <Usage />;
      case 'commands': return <Commands />;
      case 'architecture': return <Architecture />;
      case 'configuration': return <Configuration />;
      case 'examples': return <Examples />;
      default: return <Introduction />;
    }
  };

  const currentPageTitle = PAGES.find(p => p.id === currentPage)?.title || 'Documentation';
  const pageMeta = PAGES_META.find(p => p.id === currentPage);

  return (
    <HelmetProvider>
      <SEO {...pageMeta} jsonLd={pageMeta ? getDocSchema(pageMeta) : undefined} />

      <div className="min-h-screen bg-slate-50">
        <Sidebar 
          currentPage={currentPage}
          setPage={setCurrentPage}
          isOpen={sidebarOpen}
          setIsOpen={setSidebarOpen}
        />

        <div className="lg:pl-72 flex flex-col h-screen transition-all">
          <header className="sticky top-0 z-30 h-16 flex items-center justify-between px-4 sm:px-6 border-b border-slate-200 dark:border-slate-800 bg-white/80 dark:bg-slate-950/80 backdrop-blur-md">
            <div className="flex items-center">
              <button
                onClick={() => setSidebarOpen(true)}
                className="lg:hidden p-2 -ml-2 mr-2 text-slate-500 hover:text-slate-900 dark:text-slate-400 dark:hover:text-white"
              >
                <Menu className="w-5 h-5" />
              </button>
              <h1 className="text-lg font-medium text-slate-900 dark:text-white">
                {currentPageTitle}
              </h1>
            </div>
          </header>

          <main ref={mainRef} className="flex-1 overflow-y-auto min-h-0">
            <div className="max-w-4xl mx-auto p-6 lg:p-8">
              {renderContent()}
            </div>
          </main>
        </div>
      </div>
    </HelmetProvider>
  );
}
