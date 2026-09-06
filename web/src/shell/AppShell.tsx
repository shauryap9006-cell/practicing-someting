import React, { useState, useEffect } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { Sidebar } from './Sidebar';
import { CommandPalette } from './CommandPalette';
import { useConnectionState } from '../lib/api';

interface AppShellProps {
  children: React.ReactNode;
}

export const AppShell: React.FC<AppShellProps> = ({ children }) => {
  const [isSearchOpen, setIsSearchOpen] = useState(false);
  const location = useLocation();
  const connection = useConnectionState();

  // Listen for global ⌘K / Ctrl+K keyboard shortcut
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        setIsSearchOpen((prev) => !prev);
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  const mobileNavItems = [
    { path: '/t', label: 'Tracker' },
    { path: '/network', label: 'Twin' },
    { path: '/compare', label: 'Lab' },
    { path: '/proof', label: 'Proof' },
    { path: '/kiosk', label: 'PIDS' },
  ];

  const isNavActive = (path: string) => {
    if (path === '/t') {
      return location.pathname === '/t' || location.pathname.startsWith('/t/');
    }
    return location.pathname === path;
  };

  const getStatusColor = () => {
    switch (connection.status) {
      case 'LIVE':
        return 'bg-clear';
      case 'STALE':
        return 'bg-caution';
      case 'OFFLINE':
      default:
        return 'bg-restrict';
    }
  };

  return (
    <div className="min-h-screen bg-paper text-ink selection:bg-raised selection:text-ink flex flex-col relative antialiased">
      {/* Paper Grain Overlay */}
      <div
        className="fixed inset-0 pointer-events-none opacity-[0.035] z-40"
        style={{
          backgroundImage: `url("data:image/svg+xml,%3Csvg viewBox='0 0 200 200' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noiseFilter'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.8' numOctaves='3' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noiseFilter)'/%3E%3C/svg%3E")`,
        }}
      />

      {/* Desktop Sidebar (Pinned Left 232px) */}
      <Sidebar onOpenSearch={() => setIsSearchOpen(true)} />

      {/* Mobile Top Header */}
      <header className="md:hidden sticky top-0 z-30 bg-surface border-b border-line px-4 py-2.5 flex items-center justify-between">
        <Link to="/" className="flex items-center gap-2">
          <span className="font-serif text-base font-bold tracking-tight text-ink">
            RAILTWIN-X
          </span>
          <span
            className={`w-2 h-2 rounded-[2px] ${getStatusColor()}`}
            title={`Status: ${connection.status}`}
          />
        </Link>
        <button
          type="button"
          onClick={() => setIsSearchOpen(true)}
          className="flex items-center gap-1.5 px-2.5 py-1 bg-raised border border-line rounded-[3px] text-xs font-mono text-muted"
        >
          <span>Search</span>
          <span className="text-[10px]">⌘K</span>
        </button>
      </header>

      {/* Main Content Area */}
      <main className="flex-1 md:pl-[232px] pb-16 md:pb-0 flex flex-col">
        {children}
      </main>

      {/* Mobile Bottom Navigation Bar */}
      <nav className="md:hidden fixed bottom-0 left-0 right-0 z-30 bg-surface border-t border-line grid grid-cols-5 py-1 select-none">
        {mobileNavItems.map((item) => {
          const active = isNavActive(item.path);
          return (
            <Link
              key={item.path}
              to={item.path}
              className={`flex flex-col items-center justify-center py-1.5 text-center transition-colors ${
                active
                  ? 'text-ink font-bold border-t-2 border-ink -mt-1 pt-1 bg-raised/50'
                  : 'text-muted hover:text-ink'
              }`}
            >
              <span className="font-mono text-[11px] tracking-tight">
                {item.label}
              </span>
            </Link>
          );
        })}
      </nav>

      {/* Quick Search Command Palette */}
      <CommandPalette
        isOpen={isSearchOpen}
        onClose={() => setIsSearchOpen(false)}
      />
    </div>
  );
};
