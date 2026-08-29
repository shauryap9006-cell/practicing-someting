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
      <div className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-amber-500/20 text-amber-300 border border-amber-500/30">
        <span className="w-2 h-2 rounded-full bg-amber-400 animate-pulse" />
        DEMO MODE (SYNTHETIC)
      </div>
    );
  }

  if (status.state === 'OFFLINE' || isDead) {
    return (
      <div className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-red-500/20 text-red-300 border border-red-500/30 animate-pulse">
        <span className="w-2 h-2 rounded-full bg-red-500" />
        BACKEND OFFLINE {secondsAgo > 0 ? `(${secondsAgo}s ago)` : ''}
      </div>
    );
  }

  if (isStale) {
    return (
      <div className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-yellow-500/20 text-yellow-300 border border-yellow-500/30">
        <span className="w-2 h-2 rounded-full bg-yellow-400" />
        STALE ({secondsAgo}s ago)
      </div>
    );
  }

  return (
    <div className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
      <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
      LIVE {(dataUpdatedAt || status.lastSuccessfulFetch) ? `· ${secondsAgo}s ago` : ''}
    </div>
  );
};
