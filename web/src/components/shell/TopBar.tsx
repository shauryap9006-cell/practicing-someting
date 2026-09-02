import React, { useState, useEffect } from 'react';
import { Menu, Search, Bell, Clock, ChevronDown } from 'lucide-react';
import { useQuery } from '@tanstack/react-query';
import { formatTimeIST } from '@/lib/utils';
import { api } from '@/lib/api';
import { queryKeys } from '@/lib/queryKeys';
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

  const { data: station } = useQuery({
    queryKey: queryKeys.station(),
    queryFn: () => api.getStation('NDLS'),
  });

  const { data: advisories = [] } = useQuery({
    queryKey: queryKeys.advisories(),
    queryFn: () => api.getAdvisories(),
  });

  const pendingAdvisoriesCount = advisories.filter(a => a.status === 'pending').length;
  const stationCode = station?.code || 'CNB';
  const stationName = station?.name || 'Kanpur Central';

  useEffect(() => {
    const timer = setInterval(() => {
      setTimeStr(formatTimeIST());
    }, 1000);
    return () => clearInterval(timer);
  }, []);

  return (
    <header className="h-12 border-b border-[#23272F] bg-[#101216] px-4 flex items-center justify-between sticky top-0 z-30 font-mono select-none">
      {/* Left: Mobile Toggle & Page Title */}
      <div className="flex items-center gap-3">
        <button
          onClick={onOpenMobileMenu}
          className="p-1 text-[#A3ABB6] hover:text-[#E9EBEE] lg:hidden focus-visible:outline-none"
          aria-label="Open Navigation Menu"
        >
          <Menu className="w-5 h-5 stroke-[1.5]" />
        </button>

        <h1 className="text-sm font-bold text-[#E9EBEE] tracking-tight flex items-center gap-2 font-display">
          <span>{title}</span>
        </h1>
      </div>

      {/* Center/Right: Station Switcher, Search, Bell, Live Clock */}
      <div className="flex items-center gap-2 sm:gap-3">
        {/* Station Switcher Button (opens cmdk) */}
        <button
          onClick={onOpenCommandPalette}
          className="flex items-center gap-1.5 px-2.5 py-1 text-xs bg-[#15181D] border border-[#23272F] hover:border-[#F5A524] text-[#E9EBEE] transition-colors rounded-sm"
          title="Switch station or search (⌘K)"
        >
          <span className="w-1.5 h-1.5 rounded-full bg-[#3DDC97] shadow-[0_0_6px_rgba(61,220,151,0.6)] animate-pulse inline-block" />
          <span className="font-bold">{stationCode}</span>
          <span className="hidden md:inline text-[#A3ABB6] font-sans">· {stationName}</span>
          <ChevronDown className="w-3 h-3 text-[#A3ABB6] stroke-[1.5]" />
        </button>

        {/* Global Search Shortcut */}
        <button
          onClick={onOpenCommandPalette}
          className="hidden sm:flex items-center gap-2 px-2.5 py-1 text-xs text-[#A3ABB6] bg-[#15181D] border border-[#23272F] hover:text-[#E9EBEE] hover:border-[#F5A524] transition-colors rounded-sm"
          aria-label="Global Search"
        >
          <Search className="w-3.5 h-3.5 stroke-[1.5]" />
          <span className="text-[11px]">⌘K</span>
        </button>

        {/* Advisory Bell Icon */}
        <Link
          to="/dashboard/advisories"
          className="relative p-1.5 text-[#A3ABB6] hover:text-[#E9EBEE] hover:bg-[#15181D] border border-[#23272F] transition-colors rounded-sm"
          aria-label="Advisories"
        >
          <Bell className="w-3.5 h-3.5 stroke-[1.5]" />
          {pendingAdvisoriesCount > 0 && (
            <span className="absolute -top-1 -right-1 flex h-4 min-w-[16px] items-center justify-center px-1 text-[9px] font-bold bg-[#F4506A] text-[#0A0B0D] rounded-xs shadow-sm">
              {pendingAdvisoriesCount}
            </span>
          )}
        </Link>

        {/* Live IST Clock — Heartbeat of the UI */}
        <div className="flex items-center gap-1.5 px-2.5 py-1 bg-[#15181D] border border-[#23272F] text-[#E9EBEE] text-xs tabular-nums rounded-sm">
          <Clock className="w-3.5 h-3.5 text-[#F5A524] stroke-[1.5]" />
          <span className="font-bold text-[#F5A524]">{timeStr}</span>
          <span className="text-[10px] text-[#6B7480]">IST</span>
        </div>
      </div>
    </header>
  );
};
