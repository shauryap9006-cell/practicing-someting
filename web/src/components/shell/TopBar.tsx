import React, { useState, useEffect } from 'react';
import { Menu, Search, Bell, Clock, ChevronDown } from 'lucide-react';
import { formatTimeIST } from '@/lib/utils';
import { mockStore } from '@/mock/store';
import { Badge } from '@/components/ui/Badge';
import { Link } from 'react-router-dom';

interface TopBarProps {
  title: string;
  onOpenMobileMenu?: () => void;
  onOpenCommandPalette: () => void;
}

export const TopBar: React.FC<TopBarProps> = ({
  title,
  onOpenMobileMenu,
  onOpenCommandPalette,
}) => {
  const [timeStr, setTimeStr] = useState(formatTimeIST());
  const activeStationCode = mockStore.getActiveStation();
  const station = mockStore.getStation(activeStationCode);
  const pendingAdvisoriesCount = mockStore.getAdvisories().filter(a => a.status === 'pending').length;

  useEffect(() => {
    const timer = setInterval(() => {
      setTimeStr(formatTimeIST());
    }, 1000);
    return () => clearInterval(timer);
  }, []);

  return (
    <header className="h-12 border-b border-hairline bg-panel px-4 flex items-center justify-between sticky top-0 z-30">
      {/* Left: Mobile Toggle & Page Title */}
      <div className="flex items-center gap-3">
        <button
          onClick={onOpenMobileMenu}
          className="p-1 text-text-dim hover:text-text-main lg:hidden focus-visible:outline-none"
          aria-label="Open Navigation Menu"
        >
          <Menu className="w-5 h-5 stroke-[1.5]" />
        </button>

        <h1 className="text-sm font-semibold text-text-main tracking-tight flex items-center gap-2">
          <span>{title}</span>
        </h1>
      </div>

      {/* Center/Right: Station Switcher, Search, Bell, Live Clock */}
      <div className="flex items-center gap-2 sm:gap-3">
        {/* Station Switcher Button (opens cmdk) */}
        <button
          onClick={onOpenCommandPalette}
          className="flex items-center gap-1.5 px-2.5 py-1 text-xs font-mono bg-panel-2 border border-hairline hover:border-text-dim/50 text-text-main transition-colors rounded-none"
          title="Switch station or search (⌘K)"
        >
          <span className="w-1.5 h-1.5 bg-ok inline-block rounded-none" />
          <span className="font-semibold">{station.code}</span>
          <span className="hidden md:inline text-text-dim">· {station.name}</span>
          <ChevronDown className="w-3 h-3 text-text-dim stroke-[1.5]" />
        </button>

        {/* Global Search Shortcut */}
        <button
          onClick={onOpenCommandPalette}
          className="hidden sm:flex items-center gap-2 px-2 py-1 text-xs text-text-dim bg-panel-2 border border-hairline hover:text-text-main hover:border-text-dim/50 transition-colors rounded-none"
          aria-label="Global Search"
        >
          <Search className="w-3.5 h-3.5 stroke-[1.5]" />
          <span className="text-[11px] font-mono">⌘K</span>
        </button>

        {/* Advisory Bell Icon */}
        <Link
          to="/dashboard/advisories"
          className="relative p-1.5 text-text-dim hover:text-text-main hover:bg-panel-2 border border-hairline transition-colors rounded-none"
          aria-label="Advisories"
        >
          <Bell className="w-3.5 h-3.5 stroke-[1.5]" />
          {pendingAdvisoriesCount > 0 && (
            <span className="absolute -top-1 -right-1 flex h-4 min-w-[16px] items-center justify-center px-1 text-[9px] font-mono font-bold bg-danger text-bg">
              {pendingAdvisoriesCount}
            </span>
          )}
        </Link>

        {/* Live IST Clock — Heartbeat of the UI */}
        <div className="flex items-center gap-1.5 px-2.5 py-1 bg-panel-2 border border-hairline text-text-main text-xs font-mono tabular-nums">
          <Clock className="w-3.5 h-3.5 text-accent stroke-[1.5]" />
          <span className="font-semibold">{timeStr}</span>
          <span className="text-[10px] text-text-dim">IST</span>
        </div>
      </div>
    </header>
  );
};
