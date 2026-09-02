import React, { useState, useEffect } from 'react';
import { ShieldAlert, Radio, Activity } from 'lucide-react';
import { formatTimeIST } from '@/lib/utils';
import { SITE } from '@/config/site';
import { isAnalyticsActive } from '@/lib/analytics';
import { DataFreshnessBadge } from '@/components/common/DataFreshnessBadge';

export const StatusBar: React.FC = () => {
  const [lastUpdatedTime, setLastUpdatedTime] = useState<string>(() => formatTimeIST());
  const analyticsActive = isAnalyticsActive();

  useEffect(() => {
    const timer = setInterval(() => {
      setLastUpdatedTime(formatTimeIST());
    }, 5000);
    return () => clearInterval(timer);
  }, []);

  return (
    <footer className="h-7 bg-[#0A0B0D] border-t border-[#23272F] px-3 flex items-center justify-between text-[11px] font-mono text-[#A3ABB6] select-none sticky bottom-0 z-30">
      {/* Permanent Advisory Disclaimer */}
      <div className="flex items-center gap-2 truncate">
        <span className="flex items-center gap-1.5 text-[#F5A524] font-semibold tracking-wide uppercase text-[10px]">
          <ShieldAlert className="w-3 h-3 stroke-[1.5]" />
          <span>{SITE.disclaimer}</span>
        </span>
      </div>

      {/* Right side telemetry */}
      <div className="flex items-center gap-3 shrink-0">
        {/* Analytics Active indicator if active */}
        {analyticsActive && (
          <span className="hidden sm:inline text-[#6B7480] text-[10px]">
            analytics active
          </span>
        )}

        {/* Data Freshness & Data-Source State Machine */}
        <DataFreshnessBadge />

        {/* Live Auto Tick & Timestamp */}
        <div className="flex items-center gap-1.5 text-[#E9EBEE]">
          <span className="w-1.5 h-1.5 rounded-full bg-[#3DDC97] shadow-[0_0_6px_rgba(61,220,151,0.6)] inline-block animate-pulse" />
          <span>Updated {lastUpdatedTime}</span>
          <span className="text-[#6B7480] hidden md:inline">· auto 5s</span>
        </div>

        {/* Version Badge */}
        <span className="hidden sm:inline border-l border-[#23272F] pl-3 text-[#6B7480] text-[10px]">
          ASPECT v3.0
        </span>
      </div>
    </footer>
  );
};
