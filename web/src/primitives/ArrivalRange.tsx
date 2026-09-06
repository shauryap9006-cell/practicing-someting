import React from 'react';

export interface ArrivalRangeProps {
  minTime: string;
  maxTime: string;
  delayMinutes: number;
  scheduledTime?: string;
  confidence?: number;
  destination?: string;
  platform?: string;
  status?: 'clear' | 'caution' | 'restrict';
  className?: string;
}

export const ArrivalRange: React.FC<ArrivalRangeProps> = ({
  minTime,
  maxTime,
  delayMinutes,
  scheduledTime,
  confidence = 80,
  destination,
  platform,
  status: manualStatus,
  className = '',
}) => {
  const status =
    manualStatus ||
    (delayMinutes <= 5 ? 'clear' : delayMinutes <= 25 ? 'caution' : 'restrict');

  const statusColorClass =
    status === 'clear'
      ? 'bg-clear'
      : status === 'caution'
      ? 'bg-caution'
      : 'bg-restrict';

  const statusTextColorClass =
    status === 'clear'
      ? 'text-clear'
      : status === 'caution'
      ? 'text-caution'
      : 'text-restrict';

  const statusBorderColorClass =
    status === 'clear'
      ? 'border-clear/30 bg-clear/5'
      : status === 'caution'
      ? 'border-caution/30 bg-caution/5'
      : 'border-restrict/30 bg-restrict/5';

  const isSameTime = minTime === maxTime;
  const confPercent =
    confidence > 1 ? Math.round(confidence) : Math.round(confidence * 100);

  return (
    <div className={`flex flex-col gap-3 ${className}`}>
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <span
            className={`w-2.5 h-2.5 rounded-[2px] ${statusColorClass} shrink-0 animate-pulse`}
            title={`Status: ${status.toUpperCase()}`}
          />
          <span className="font-mono text-micro uppercase tracking-wider text-muted font-medium">
            Dynamic Arrival Window {destination ? `· ${destination}` : ''}
          </span>
        </div>
        <div className="flex items-center gap-2">
          {platform && (
            <span className="font-mono text-xs px-2 py-0.5 rounded-[3px] bg-raised border border-line text-ink font-medium">
              {platform}
            </span>
          )}
          <span
            className={`font-mono text-xs px-2 py-0.5 rounded-[3px] border font-medium tabular-nums ${statusBorderColorClass} ${statusTextColorClass}`}
          >
            {delayMinutes > 0
              ? `+${delayMinutes}m Late`
              : delayMinutes < 0
              ? `${delayMinutes}m Early`
              : 'Right Time'}
          </span>
        </div>
      </div>

      <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
        <span className="font-mono text-3xl sm:text-5xl font-bold tracking-tight text-ink tabular-nums">
          {isSameTime ? minTime : `${minTime} — ${maxTime}`}
        </span>
        {scheduledTime && (
          <span className="font-mono text-sm sm:text-base text-muted/80 tabular-nums">
            (Sch {scheduledTime})
          </span>
        )}
      </div>

      <div className="flex flex-wrap items-center justify-between text-xs text-muted gap-2 pt-1 border-t border-line/40">
        <span className="font-mono text-[11px] tabular-nums">
          P10 {minTime} · P90 {maxTime} ({confPercent}% confidence interval)
        </span>
        <span className="font-sans text-[11px] text-muted hidden sm:inline">
          Dynamic cone updated from corridor telemetry
        </span>
      </div>
    </div>
  );
};
