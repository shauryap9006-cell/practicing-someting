import React, { useEffect, useState } from 'react';
import { DataSourceStatus, subscribeDataSourceStatus } from '@/lib/api';

interface DataFreshnessBadgeProps {
  dataUpdatedAt?: number;
}

export const DataFreshnessBadge: React.FC<DataFreshnessBadgeProps> = ({ dataUpdatedAt }) => {
  const [status, setStatus] = useState<DataSourceStatus>({
    state: 'LIVE',
    lastSuccessfulFetch: dataUpdatedAt || null,
    lastAttempt: null,
    isDemoMode: false,
  });
  const [secondsAgo, setSecondsAgo] = useState<number>(0);

  useEffect(() => {
    const unsub = subscribeDataSourceStatus((st) => {
      setStatus(st);
    });

    const interval = setInterval(() => {
      const ts = dataUpdatedAt || status.lastSuccessfulFetch;
      if (ts) {
        setSecondsAgo(Math.floor((Date.now() - ts) / 1000));
      }
    }, 1000);

    return () => {
      unsub();
      clearInterval(interval);
    };
  }, [dataUpdatedAt, status.lastSuccessfulFetch]);

  const isStale = secondsAgo > 30 && status.state === 'LIVE';
  const isDead = secondsAgo > 120 && status.state === 'LIVE';

  if (status.isDemoMode || status.state === 'DEMO') {
    return (
      <div className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-sm text-[11px] font-mono uppercase tracking-wider font-semibold bg-[rgba(108,159,255,0.13)] text-[#6C9FFF] border border-[#6C9FFF]/40">
        <span className="w-1.5 h-1.5 rounded-full bg-[#6C9FFF] shadow-[0_0_6px_rgba(108,159,255,0.6)]" />
        DEMO REPLAY
      </div>
    );
  }

  if (status.state === 'OFFLINE' || isDead) {
    return (
      <div className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-sm text-[11px] font-mono uppercase tracking-wider font-semibold bg-[rgba(244,80,106,0.13)] text-[#F4506A] border border-[#F4506A]/40 animate-pulse">
        <span className="w-1.5 h-1.5 rounded-full bg-[#F4506A] shadow-[0_0_6px_rgba(244,80,106,0.6)]" />
        OFFLINE {secondsAgo > 0 ? `(${secondsAgo}s)` : ''}
      </div>
    );
  }

  if (isStale) {
    return (
      <div className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-sm text-[11px] font-mono uppercase tracking-wider font-semibold bg-[rgba(245,165,36,0.13)] text-[#F5A524] border border-[#F5A524]/40">
        <span className="w-1.5 h-1.5 rounded-full bg-[#F5A524] shadow-[0_0_6px_rgba(245,165,36,0.6)]" />
        STALE ({secondsAgo}s)
      </div>
    );
  }

  return (
    <div className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-sm text-[11px] font-mono uppercase tracking-wider font-semibold bg-[rgba(61,220,151,0.13)] text-[#3DDC97] border border-[#3DDC97]/40">
      <span className="w-1.5 h-1.5 rounded-full bg-[#3DDC97] shadow-[0_0_6px_rgba(61,220,151,0.6)] animate-pulse" />
      LIVE {(dataUpdatedAt || status.lastSuccessfulFetch) ? `· ${secondsAgo}s` : ''}
    </div>
  );
};
