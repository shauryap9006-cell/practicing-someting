import React, { useState } from 'react';

export interface DelayCauseItem {
  category: string;
  label: string;
  minutes: number;
  confidence?: number;
  location?: string;
}

export interface WhyLateCardProps {
  narrative?: string;
  causes: DelayCauseItem[];
  totalDelayMinutes: number;
  className?: string;
  defaultOpen?: boolean;
}

export const WhyLateCard: React.FC<WhyLateCardProps> = ({
  narrative,
  causes = [],
  totalDelayMinutes,
  className = '',
  defaultOpen = true,
}) => {
  const [isOpen, setIsOpen] = useState(defaultOpen);

  const netCausesMinutes = causes.reduce((acc, c) => acc + c.minutes, 0);
  const discrepancy = Math.abs(netCausesMinutes - totalDelayMinutes);
  const isBalanced = discrepancy <= 1;

  const maxAbsMinutes = Math.max(
    ...causes.map((c) => Math.abs(c.minutes)),
    Math.abs(totalDelayMinutes),
    15
  );

  return (
    <div
      className={`border border-line rounded-[4px] bg-surface overflow-hidden ${className}`}
    >
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        className="w-full flex items-center justify-between px-4 py-3 bg-surface hover:bg-raised/40 transition-colors text-left border-b border-line/60"
      >
        <div className="flex items-center gap-2">
          <span className="w-2 h-2 rounded-[2px] bg-ochre" />
          <span className="font-mono text-micro uppercase tracking-wider text-muted font-medium">
            Root-Cause Delay Attribution
          </span>
          <span className="font-mono text-xs font-semibold text-ink px-2 py-0.5 bg-raised border border-line rounded-[3px]">
            {totalDelayMinutes > 0 ? `+${totalDelayMinutes}m Total` : 'On Time'}
          </span>
        </div>
        <div className="flex items-center gap-2 font-mono text-xs text-muted">
          <span>{isOpen ? 'COLLAPSE' : 'EXPAND'}</span>
          <span className="font-mono text-sm">{isOpen ? '−' : '+'}</span>
        </div>
      </button>

      {isOpen && (
        <div className="p-4 sm:p-5 flex flex-col gap-4">
          {narrative && (
            <p className="font-sans text-sm text-ink/90 leading-relaxed border-l-2 border-ochre pl-3 py-0.5 bg-raised/30 rounded-r-[3px]">
              {narrative}
            </p>
          )}

          <div className="flex flex-col gap-2 pt-1">
            <div className="flex items-center justify-between font-mono text-[11px] text-muted border-b border-line/50 pb-1">
              <span className="w-1/2 text-left">RECOVERY / SLACK (−)</span>
              <span className="w-1/2 text-right">ADDED DELAY (+)</span>
            </div>

            {causes.length === 0 ? (
              <div className="py-3 text-center font-mono text-xs text-muted">
                No active delay anomalies reported in corridor log.
              </div>
            ) : (
              <div className="flex flex-col gap-2.5">
                {causes.map((cause, idx) => {
                  const isPositive = cause.minutes > 0;
                  const isNegative = cause.minutes < 0;
                  const absMinutes = Math.abs(cause.minutes);
                  const barWidthPercent = Math.min(
                    100,
                    Math.round((absMinutes / maxAbsMinutes) * 100)
                  );

                  return (
                    <div
                      key={`${cause.category}-${cause.label}-${idx}`}
                      className="flex flex-col gap-1 text-xs"
                    >
                      <div className="flex items-center justify-between">
                        <span className="font-sans font-medium text-ink flex items-center gap-1.5">
                          <span className="font-mono text-[10px] uppercase px-1 py-0.5 bg-raised border border-line rounded-[2px] text-muted">
                            {cause.category}
                          </span>
                          {cause.label}
                          {cause.location && (
                            <span className="font-mono text-[10px] text-muted">
                              @{cause.location}
                            </span>
                          )}
                        </span>
                        <span
                          className={`font-mono font-bold tabular-nums ${
                            isNegative
                              ? 'text-clear'
                              : isPositive
                              ? 'text-restrict'
                              : 'text-muted'
                          }`}
                        >
                          {isPositive ? `+${absMinutes}m` : isNegative ? `−${absMinutes}m` : '0m'}
                        </span>
                      </div>

                      <div className="grid grid-cols-2 gap-0 h-4 bg-raised/40 border border-line/60 rounded-[2px] relative overflow-hidden">
                        <div className="flex justify-end items-center pr-0.5 border-r border-line">
                          {isNegative && (
                            <div
                              className="h-2.5 bg-clear rounded-l-[1px]"
                              style={{ width: `${barWidthPercent}%` }}
                            />
                          )}
                        </div>

                        <div className="flex justify-start items-center pl-0.5">
                          {isPositive && (
                            <div
                              className={`h-2.5 rounded-r-[1px] ${
                                cause.minutes >= 10 ? 'bg-restrict' : 'bg-caution'
                              }`}
                              style={{ width: `${barWidthPercent}%` }}
                            />
                          )}
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          <div className="flex flex-wrap items-center justify-between gap-2 pt-3 border-t border-line/60 text-xs">
            <div className="font-mono text-[11px] text-muted flex items-center gap-1.5">
              <span>Additivity check:</span>
              <span className="font-semibold tabular-nums text-ink">
                Σ causes ({netCausesMinutes > 0 ? `+${netCausesMinutes}` : netCausesMinutes}m) = net delay ({totalDelayMinutes > 0 ? `+${totalDelayMinutes}` : totalDelayMinutes}m)
              </span>
            </div>
            <div>
              {isBalanced ? (
                <span className="font-mono text-[11px] px-2 py-0.5 rounded-[3px] bg-clear/10 border border-clear/30 text-clear font-medium">
                  Balanced ✓
                </span>
              ) : (
                <span className="font-mono text-[11px] px-2 py-0.5 rounded-[3px] bg-caution/10 border border-caution/30 text-caution font-medium">
                  Residual ±{discrepancy}m (unattributed drift)
                </span>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
