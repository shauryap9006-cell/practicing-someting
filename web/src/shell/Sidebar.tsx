import React, { useState, useEffect } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { useConnectionState } from '../lib/api';

interface SidebarProps {
  onOpenSearch?: () => void;
}

export const Sidebar: React.FC<SidebarProps> = ({ onOpenSearch }) => {
  const location = useLocation();
  const connection = useConnectionState();
  const [istTime, setIstTime] = useState<string>('');

  // Live IST Clock (ticking every 1s)
  useEffect(() => {
    const updateTime = () => {
      const now = new Date();
      const formatted = new Intl.DateTimeFormat('en-GB', {
        timeZone: 'Asia/Kolkata',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
        hour12: false,
      }).format(now);
      setIstTime(`${formatted} IST`);
    };

    updateTime();
    const timer = setInterval(updateTime, 1000);
    return () => clearInterval(timer);
  }, []);

  const navItems = [
    { path: '/t', label: 'Train Tracker', micro: 'LIVE ETA' },
    { path: '/network', label: 'Corridor Twin', micro: 'FLEET 1D' },
    { path: '/compare', label: 'Shock Lab', micro: 'VS NTES' },
    { path: '/proof', label: 'Model Proof', micro: 'LEDGER' },
    { path: '/neural-flow', label: 'Neural Flow', micro: 'AI PIPELINE' },
    { path: '/kiosk', label: 'Station PIDS', micro: 'DISPLAY' },
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
    <aside className="w-[232px] fixed left-0 top-0 bottom-0 bg-surface border-r border-line flex flex-col justify-between z-30 select-none hidden md:flex">
      {/* Top Header & Brand */}
      <div className="flex flex-col">
        {/* Masthead */}
        <div className="p-4 border-b border-line/60">
          <Link to="/" className="group flex flex-col gap-0.5">
            <span className="font-serif text-lg font-bold tracking-tight text-ink group-hover:text-ochre transition-colors">
              RAILTWIN-X
            </span>
            <span className="font-mono text-[9px] uppercase tracking-widest text-muted">
              Working Timetable · PS 26028
            </span>
          </Link>
        </div>

        {/* Live IST Clock & Telemetry Lamp */}
        <div className="px-4 py-2.5 bg-raised/40 border-b border-line/60 flex items-center justify-between text-[11px] font-mono">
          <div className="flex items-center gap-2">
            <span
              className={`w-2 h-2 rounded-[2px] ${getStatusColor()} ${
                connection.status === 'LIVE' ? 'animate-pulse' : ''
              }`}
              title={`Connection Status: ${connection.status}`}
            />
            <span className="text-ink font-semibold uppercase tracking-wider text-[10px]">
              {connection.status}
            </span>
          </div>
          <span className="text-muted tabular-nums">{istTime || '--:--:-- IST'}</span>
        </div>

        {/* Search Trigger Button */}
        <div className="p-3">
          <button
            type="button"
            onClick={onOpenSearch}
            className="w-full flex items-center justify-between px-3 py-1.5 bg-raised/60 hover:bg-raised border border-line rounded-[4px] text-xs font-mono text-muted hover:text-ink transition-colors cursor-pointer text-left"
          >
            <span className="flex items-center gap-1.5">
              <span>Find Train</span>
            </span>
            <kbd className="px-1.5 py-0.5 text-[10px] bg-surface border border-line rounded-[3px] text-muted">
              ⌘K
            </kbd>
          </button>
        </div>

        {/* Primary Navigation */}
        <nav className="flex flex-col gap-0.5 px-2 py-1">
          {navItems.map((item) => {
            const active = isNavActive(item.path);

            return (
              <Link
                key={item.path}
                to={item.path}
                className={`flex items-center justify-between px-3 py-2 rounded-[3px] transition-all text-xs ${
                  active
                    ? 'bg-raised font-semibold text-ink border-r-2 border-ink'
                    : 'text-muted hover:text-ink hover:bg-raised/40'
                }`}
              >
                <span className="font-sans text-[13px]">{item.label}</span>
                <span className="font-mono text-[9px] uppercase tracking-wider text-muted">
                  {item.micro}
                </span>
              </Link>
            );
          })}
        </nav>
      </div>

      {/* Bottom Footer & System Info */}
      <div className="p-3 border-t border-line/60 flex flex-col gap-2 bg-surface">
        <div className="flex flex-col gap-0.5">
          <span className="font-mono text-[9px] uppercase tracking-wider text-muted font-medium">
            Active Corridor
          </span>
          <span className="font-sans text-[11px] text-ink font-medium leading-snug">
            NDLS — HWH Main Trunk
          </span>
          <span className="font-mono text-[10px] text-muted tabular-nums">
            1,447 km · 16 Divisions
          </span>
        </div>

        <div className="pt-2 border-t border-line/40 flex items-center justify-between text-[10px] font-mono text-muted">
          <span>Engine v4.0</span>
          <span>Zero-Mock Twin</span>
        </div>
      </div>
    </aside>
  );
};
