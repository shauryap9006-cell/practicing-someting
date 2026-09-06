import React from 'react';

export interface ConnectionTrain {
  trainNo: string;
  trainName: string;
  stationCode: string;
  departsTime: string;
  scheduledDeparts?: string;
  minTransferMinutes: number;
  actualTransferMinutes: number;
  status: 'PROTECTED' | 'TIGHT' | 'CRITICAL' | 'MISSED';
  platform?: string;
}

export interface CascadeCardProps {
  connections: ConnectionTrain[];
  currentTrainArrival?: string;
  className?: string;
}

export const CascadeCard: React.FC<CascadeCardProps> = ({
  connections = [],
  currentTrainArrival,
  className = '',
}) => {
  const getStatusBadge = (status: ConnectionTrain['status']) => {
    switch (status) {
      case 'PROTECTED':
        return 'bg-clear/10 border-clear/40 text-clear';
      case 'TIGHT':
        return 'bg-caution/10 border-caution/40 text-caution';
      case 'CRITICAL':
      case 'MISSED':
        return 'bg-restrict/10 border-restrict/40 text-restrict';
      default:
        return 'bg-raised border-line text-muted';
    }
  };

  return (
    <div
      className={`border border-line rounded-[4px] bg-surface overflow-hidden ${className}`}
    >
      <div className="flex items-center justify-between px-4 py-3 border-b border-line/60 bg-surface">
        <div className="flex items-center gap-2">
          <span className="w-2 h-2 rounded-[2px] bg-ink" />
          <span className="font-mono text-micro uppercase tracking-wider text-muted font-medium">
            Connecting Corridor Custody
          </span>
        </div>
        {currentTrainArrival && (
          <span className="font-mono text-[11px] text-muted tabular-nums">
            Estimated Touchdown: {currentTrainArrival}
          </span>
        )}
      </div>

      <div className="p-4 sm:p-5 flex flex-col gap-3">
        {connections.length === 0 ? (
          <div className="py-4 text-center font-mono text-xs text-muted">
            No downstream connections registered for this service window.
          </div>
        ) : (
          <div className="flex flex-col divide-y divide-line/60">
            {connections.map((conn) => {
              const bufferDelta =
                conn.actualTransferMinutes - conn.minTransferMinutes;

              return (
                <div
                  key={conn.trainNo}
                  className="py-3 first:pt-0 last:pb-0 flex flex-col sm:flex-row sm:items-center justify-between gap-2"
                >
                  <div className="flex flex-col gap-0.5">
                    <div className="flex items-center gap-2">
                      <span className="font-mono font-bold text-sm text-ink">
                        #{conn.trainNo}
                      </span>
                      <span className="font-sans font-medium text-xs text-ink">
                        {conn.trainName}
                      </span>
                      {conn.platform && (
                        <span className="font-mono text-[10px] px-1.5 py-0.2 rounded-[2px] bg-raised border border-line text-muted">
                          {conn.platform}
                        </span>
                      )}
                    </div>
                    <span className="font-mono text-[11px] text-muted tabular-nums">
                      Departs {conn.stationCode} at {conn.departsTime} · Min connect:{' '}
                      {conn.minTransferMinutes}m
                    </span>
                  </div>

                  <div className="flex items-center gap-3 justify-between sm:justify-end">
                    <div className="flex flex-col items-end">
                      <span className="font-mono text-xs tabular-nums font-semibold text-ink">
                        {conn.actualTransferMinutes}m transfer window
                      </span>
                      <span
                        className={`font-mono text-[10px] tabular-nums ${
                          bufferDelta >= 0 ? 'text-clear' : 'text-restrict'
                        }`}
                      >
                        {bufferDelta >= 0 ? `+${bufferDelta}m buffer` : `${bufferDelta}m breach`}
                      </span>
                    </div>
                    <span
                      className={`font-mono text-[10px] uppercase font-bold px-2 py-1 border rounded-[3px] tracking-wider ${getStatusBadge(
                        conn.status
                      )}`}
                    >
                      {conn.status}
                    </span>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
};
