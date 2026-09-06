import React, { useState, useEffect } from 'react';

export interface LoadingStateProps {
  rows?: number;
  height?: string;
  message?: string;
  delayMs?: number;
  className?: string;
}

export const LoadingState: React.FC<LoadingStateProps> = ({
  rows = 3,
  height,
  message = 'Polling corridor telemetry...',
  delayMs = 200,
  className = '',
}) => {
  const [show, setShow] = useState(delayMs === 0);

  useEffect(() => {
    if (delayMs === 0) return;
    const timer = setTimeout(() => setShow(true), delayMs);
    return () => clearTimeout(timer);
  }, [delayMs]);

  if (!show) return null;

  return (
    <div
      className={`p-5 bg-surface border border-line rounded-[4px] flex flex-col gap-3 animate-pulse ${className}`}
      aria-busy="true"
      aria-live="polite"
    >
      <div className="flex items-center justify-between">
        <div className="h-3 w-28 bg-raised rounded-[2px]" />
        <span className="font-mono text-[11px] text-muted">{message}</span>
      </div>

      {height ? (
        <div className={`w-full bg-raised/70 rounded-[3px] ${height}`} />
      ) : (
        <div className="flex flex-col gap-2.5 pt-1">
          {Array.from({ length: rows }).map((_, i) => (
            <div
              key={i}
              className="h-7 bg-raised/70 rounded-[3px]"
              style={{ opacity: 1 - i * 0.2 }}
            />
          ))}
        </div>
      )}
    </div>
  );
};
