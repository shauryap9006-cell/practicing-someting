import React from 'react';

export interface TimelineStation {
  code: string;
  name: string;
  scheduledArrival: string;
  predictedMin?: string;
  predictedMax?: string;
  distanceKm: number;
  isPassed: boolean;
  isCurrent?: boolean;
  delayMinutes?: number;
  platform?: string;
}

export interface ConeTimelineProps {
  stations: TimelineStation[];
  currentKm?: number;
  className?: string;
}

export const ConeTimeline: React.FC<ConeTimelineProps> = ({
  stations,
  currentKm,
  className = '',
}) => {
  if (!stations || stations.length === 0) {
    return (
      <div className="p-4 text-xs font-mono text-muted text-center border border-line rounded-[4px]">
        No station timeline data available
      </div>
    );
  }

  const currentIndex = stations.findIndex((s) => s.isCurrent);
  const activeIdx = currentIndex >= 0 ? currentIndex : stations.findIndex((s) => !s.isPassed);
  const trainIdx = activeIdx >= 0 ? activeIdx : stations.length - 1;

  const totalStations = stations.length;
  const svgWidth = 800;
  const svgHeight = 110;
  const paddingX = 40;
  const trackY = 55;
  const usableWidth = svgWidth - paddingX * 2;

  const getStationX = (index: number) => {
    if (totalStations <= 1) return paddingX + usableWidth / 2;
    return paddingX + (index / (totalStations - 1)) * usableWidth;
  };

  const trainX = getStationX(trainIdx);
  const downstreamPointsUpper: string[] = [];
  const downstreamPointsLower: string[] = [];

  for (let i = trainIdx; i < totalStations; i++) {
    const x = getStationX(i);
    const progress = totalStations - 1 > trainIdx ? (i - trainIdx) / (totalStations - 1 - trainIdx) : 0;
    const halfSpread = 4 + progress * 24;
    downstreamPointsUpper.push(`${x},${trackY - halfSpread}`);
    downstreamPointsLower.unshift(`${x},${trackY + halfSpread}`);
  }

  const conePolygonPath =
    downstreamPointsUpper.length > 1
      ? `${downstreamPointsUpper.join(' ')} ${downstreamPointsLower.join(' ')}`
      : '';

  return (
    <div className={`flex flex-col gap-2 overflow-x-auto select-none ${className}`}>
      <div className="min-w-[620px] w-full">
        <svg
          viewBox={`0 0 ${svgWidth} ${svgHeight}`}
          className="w-full h-auto overflow-visible"
          preserveAspectRatio="xMidYMid meet"
        >
          {/* Background track line */}
          <line
            x1={paddingX}
            y1={trackY}
            x2={svgWidth - paddingX}
            y2={trackY}
            stroke="#E1DAC9"
            strokeWidth="3"
            strokeLinecap="round"
          />

          {/* Passed track line in darker tone */}
          {trainX > paddingX && (
            <line
              x1={paddingX}
              y1={trackY}
              x2={trainX}
              y2={trackY}
              stroke="#B3AA99"
              strokeWidth="3"
              strokeLinecap="round"
            />
          )}

          {/* Uncertainty Cone Band: Graphite (#4A453D) at 14% alpha */}
          {conePolygonPath && (
            <polygon
              points={conePolygonPath}
              fill="#4A453D"
              fillOpacity="0.14"
              stroke="#4A453D"
              strokeOpacity="0.25"
              strokeWidth="1"
              strokeDasharray="3 3"
            />
          )}

          {/* Station markers */}
          {stations.map((stn, idx) => {
            const x = getStationX(idx);
            const isPassed = stn.isPassed;
            const isCurrent = idx === trainIdx;

            return (
              <g key={stn.code || idx}>
                <line
                  x1={x}
                  y1={trackY - 8}
                  x2={x}
                  y2={trackY + 8}
                  stroke={isPassed ? '#B3AA99' : isCurrent ? '#191712' : '#8A8477'}
                  strokeWidth={isCurrent ? '2.5' : '1.5'}
                />

                <circle
                  cx={x}
                  cy={trackY}
                  r={isCurrent ? 6 : 4}
                  fill={isPassed ? '#ECE7DB' : isCurrent ? '#191712' : '#FDFCF8'}
                  stroke={isCurrent ? '#C25E00' : isPassed ? '#B3AA99' : '#191712'}
                  strokeWidth={isCurrent ? '2' : '1.5'}
                />

                <text
                  x={x}
                  y={trackY - 16}
                  textAnchor="middle"
                  className={`font-mono text-[11px] font-bold ${
                    isCurrent ? 'fill-ink' : isPassed ? 'fill-muted/60' : 'fill-ink'
                  }`}
                >
                  {stn.code}
                </text>

                <text
                  x={x}
                  y={trackY + 24}
                  textAnchor="middle"
                  className={`font-mono text-[10px] tabular-nums ${
                    isCurrent
                      ? 'fill-ochre font-bold'
                      : isPassed
                      ? 'fill-muted/60'
                      : 'fill-ink font-medium'
                  }`}
                >
                  {stn.predictedMin ? stn.predictedMin : stn.scheduledArrival}
                </text>

                {stn.delayMinutes && stn.delayMinutes > 0 && !isPassed && (
                  <text
                    x={x}
                    y={trackY + 38}
                    textAnchor="middle"
                    className="font-mono text-[9px] fill-restrict font-medium"
                  >
                    +{stn.delayMinutes}m
                  </text>
                )}
              </g>
            );
          })}

          {/* Current Live Train Indicator */}
          <g transform={`translate(${trainX}, ${trackY})`}>
            <circle
              r="10"
              fill="none"
              stroke="#C25E00"
              strokeWidth="1.5"
              className="animate-ping opacity-60"
            />
            <circle r="4" fill="#C25E00" />
            <polygon
              points="0,-10 -5,-18 5,-18"
              fill="#C25E00"
            />
          </g>
        </svg>
      </div>

      <div className="flex flex-wrap items-center justify-between text-[11px] font-mono text-muted pt-2 border-t border-line/40 px-1">
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-[2px] bg-ochre inline-block" />
            <span>Train Position</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-3 h-2 border border-graphite/40 bg-graphite/15 inline-block" />
            <span>Uncertainty Cone (P10–P90)</span>
          </div>
        </div>
        <span className="text-[10px] text-muted">
          Widening downstream indicates forward corridor entropy
        </span>
      </div>
    </div>
  );
};
