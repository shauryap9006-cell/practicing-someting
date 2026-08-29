import React, { useState, useEffect } from 'react';
import { Outlet, useLocation } from 'react-router-dom';
import { Sidebar } from '@/components/shell/Sidebar';
import { TopBar } from '@/components/shell/TopBar';
import { StatusBar } from '@/components/shell/StatusBar';
import { CommandPalette } from '@/components/shell/CommandPalette';
import { mockStore } from '@/mock/store';
import { SEO } from '@/lib/seo';

export const DashboardLayout: React.FC = () => {
  const location = useLocation();
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const [isCmdkOpen, setIsCmdkOpen] = useState(false);
  const [theme, setTheme] = useState<'dark' | 'light'>('dark');
  const [pendingAdvisoriesCount, setPendingAdvisoriesCount] = useState(
    mockStore.getAdvisories().filter(a => a.status === 'pending').length
  );

  useEffect(() => {
    const unsubscribe = mockStore.subscribe(() => {
      setPendingAdvisoriesCount(
        mockStore.getAdvisories().filter(a => a.status === 'pending').length
      );
    });
    return unsubscribe;
  }, []);

  // Theme Management
  useEffect(() => {
    const savedTheme = localStorage.getItem('rtx-theme') as 'dark' | 'light' | null;
    if (savedTheme === 'light') {
      setTheme('light');
      document.documentElement.classList.remove('dark');
      document.documentElement.classList.add('light');
    } else {
      setTheme('dark');
      document.documentElement.classList.remove('light');
      document.documentElement.classList.add('dark');
    }
  }, []);

  const toggleTheme = () => {
    const nextTheme = theme === 'dark' ? 'light' : 'dark';
    setTheme(nextTheme);
    localStorage.setItem('rtx-theme', nextTheme);
    if (nextTheme === 'light') {
      document.documentElement.classList.remove('dark');
      document.documentElement.classList.add('light');
    } else {
      document.documentElement.classList.remove('light');
      document.documentElement.classList.add('dark');
    }
  };

  const getPageTitle = (path: string): string => {
    if (path.startsWith('/dashboard/gantt')) return 'Platform Gantt';
    if (path.startsWith('/dashboard/trains/')) return 'Train Journey & Delay Autopsy';
    if (path.startsWith('/dashboard/trains')) return 'Trains Directory';
    if (path.startsWith('/dashboard/advisories')) return 'Advisory Triage Queue';
    if (path.startsWith('/dashboard/crew')) return 'Crew Duty Management';
    if (path.startsWith('/dashboard/maintenance')) return 'Corridor Maintenance Blocks';
    if (path.startsWith('/dashboard/audit')) return 'Regulatory Audit Log';
    if (path.startsWith('/dashboard/model')) return 'Model Proof & F14 Backtest';
    return 'Control Room Overview';
  };

  const pageTitle = getPageTitle(location.pathname);
  const activeStation = mockStore.getActiveStation();

  return (
    <div className="min-h-screen bg-bg text-text-main flex flex-col font-sans">
      <SEO
        title={`${pageTitle} · ${activeStation}`}
        description="Decision-support digital twin for Indian Railways station operations."
        noindex={true}
      />

      {/* Fixed Desktop / Drawer Mobile Sidebar */}
      <Sidebar
        isOpen={isMobileMenuOpen}
        onClose={() => setIsMobileMenuOpen(false)}
        theme={theme}
        onToggleTheme={toggleTheme}
      />

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col lg:pl-60 min-h-screen">
        <TopBar
          title={pageTitle}
          onOpenMobileMenu={() => setIsMobileMenuOpen(true)}
          onOpenCommandPalette={() => setIsCmdkOpen(true)}
        />

        <main className="flex-1 p-4 sm:p-6 overflow-x-hidden">
          <Outlet />
        </main>

        <StatusBar />
      </div>

      {/* Global ⌘K Command Palette */}
      <CommandPalette open={isCmdkOpen} onOpenChange={setIsCmdkOpen} />
    </div>
  );
};
