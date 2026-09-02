import React, { useState, useEffect } from 'react';

interface ProvenanceProps {
  updatedAt?: number | Date | string;
  source?: string;
  refreshIntervalSeconds?: number;
  isVerified?: boolean;
  className?: string;
}

export const Provenance: React.FC<ProvenanceProps> = ({
  updatedAt,
  source = 'NTES + F14 TELEMETRY LEDGER',
  refreshIntervalSeconds = 5,
  isVerified = true,
  className = '',
}) => {
  const [now, setNow] = useState(new Date());

  useEffect(() => {
    const timer = setInterval(() => setNow(new Date()), 1000);
    return () => clearInterval(timer);
  }, []);

  const formatTime = (d: Date | number | string | undefined) => {
    if (!d) return now.toTimeString().split(' ')[0];
    const dateObj = typeof d === 'number' ? new Date(d) : typeof d === 'string' ? new Date(d) : d;
    return dateObj.toTimeString().split(' ')[0];
  };

  const timeStr = formatTime(updatedAt);

  return (
    <div
      className={`flex items-center justify-between text-[10px] font-mono text-[#6B7480] uppercase tracking-wider select-none pt-2 border-t border-[#23272F] ${className}`}
    >
      <div className="flex items-center gap-2">
        <span className="w-1.5 h-1.5 rounded-full bg-[#3DDC97] animate-pulse" />
        <span>
          AS OF <span className="text-[#A3ABB6] font-bold">{timeStr} IST</span> · AUTO {refreshIntervalSeconds}S
        </span>
      </div>

      <div className="flex items-center gap-2">
        <span className="hidden sm:inline text-[#6B7480]">SRC: {source}</span>
        {isVerified && (
          <span className="text-[#3DDC97] font-semibold flex items-center gap-1">
            <span>●</span> VERIFIED
          </span>
        )}
      </div>
    </div>
  );
};
