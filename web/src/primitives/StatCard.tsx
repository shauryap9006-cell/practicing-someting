import React from 'react';

export interface StatCardProps {
  label: string;
  value: string | number;
  subtext?: string;
  delta?: string;
  deltaType?: 'positive' | 'negative' | 'neutral';
  action?: React.ReactNode;
  className?: string;
}

export const StatCard: React.FC<StatCardProps> = ({
  label,
  value,
  subtext,
  delta,
  deltaType = 'neutral',
  action,
  className = '',
}) => {
  const getDeltaColor = () => {
    switch (deltaType) {
      case 'positive':
        return 'text-clear';
      case 'negative':
        return 'text-restrict';
      default:
        return 'text-muted';
    }
  };

  return (
    <div
      className={`bg-surface border border-line rounded-[4px] p-4 flex flex-col justify-between gap-2 transition-colors ${className}`}
    >
      <div className="flex items-start justify-between gap-2">
        <span className="font-mono text-micro uppercase tracking-wider text-muted font-medium">
          {label}
        </span>
        {action && <div>{action}</div>}
      </div>

      <div className="flex flex-col gap-1">
        <span className="font-mono text-2xl sm:text-3xl font-bold tracking-tight text-ink tabular-nums">
          {value}
        </span>
        {(subtext || delta) && (
          <div className="flex items-center justify-between text-[11px] pt-1 border-t border-line/40">
            {subtext && <span className="font-sans text-muted">{subtext}</span>}
            {delta && (
              <span className={`font-mono font-medium tabular-nums ${getDeltaColor()}`}>
                {delta}
              </span>
            )}
          </div>
        )}
      </div>
    </div>
  );
};
