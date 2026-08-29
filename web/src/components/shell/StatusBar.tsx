import React, { useState, useEffect } from 'react';
import { ShieldAlert, Radio, Activity } from 'lucide-react';
import { mockStore } from '@/mock/store';
import { formatTimeIST } from '@/lib/utils';
import { SITE } from '@/config/site';
import { isAnalyticsActive } from '@/lib/analytics';
import { DataFreshnessBadge } from '@/components/common/DataFreshnessBadge';


export const StatusBar: React.FC = () => {
  const [lastUpdatedTime, setLastUpdatedTime] = useState<string>(formatTimeIST(mockStore.getLastUpdated()));
  const analyticsActive = isAnalyticsActive();

  useEffect(() => {
    const unsubscribe = mockStore.subscribe(() => {
      setLastUpdatedTime(formatTimeIST(mockStore.getLastUpdated()));
    });
    return unsubscribe;
  }, []);

  return (
    <footer className="h-7 bg-panel border-t border-hairline px-3 flex items-center justify-between text-[11px] font-mono text-text-dim select-none sticky bottom-0 z-30">
      {/* Permanent Advisory Disclaimer */}
      <div className="flex items-center gap-2 truncate">
        <span className="flex items-center gap-1 text-accent font-semibold tracking-wide uppercase">
          <ShieldAlert className="w-3 h-3 stroke-[1.5]" />
          <span>{SITE.disclaimer}</span>
        </span>
      </div>

      {/* Right side telemetry */}
      <div className="flex items-center gap-3 shrink-0">
        {/* Analytics Active indicator if active */}
        {analyticsActive && (
          <span className="hidden sm:inline text-text-dim text-[10px]">
            analytics active
          </span>
        )}

        {/* Data Freshness & Data-Source State Machine (F38) */}
        <DataFreshnessBadge />


        {/* Live Auto Tick & Timestamp */}
        <div className="flex items-center gap-1.5 text-text-main">
          <span className="w-1.5 h-1.5 bg-ok inline-block rounded-none animate-pulse" />
          <span>Updated {lastUpdatedTime}</span>
          <span className="text-text-dim hidden md:inline">· auto 5s</span>
        </div>

        {/* Version Badge */}
        <span className="hidden sm:inline border-l border-hairline pl-3 text-text-dim">
          v3.0-final
        </span>
      </div>
    </footer>
  );
};
