import React, { useMemo } from 'react';
import { NATIONAL_CORRIDORS, NationalCorridor } from '../lib/corridors';
import type { LivePosition } from '@railtwin/shared-types';

interface CorridorSelectorProps {
  activeCorridorId: string;
  onSelectCorridor: (corridorId: string) => void;
  positions: LivePosition[];
}

export const CorridorSelector: React.FC<CorridorSelectorProps> = ({
  activeCorridorId,
  onSelectCorridor,
  positions,
}) => {
  // Count how many active trains are currently operating on each corridor
  const corridorTrainCounts = useMemo(() => {
    const counts = new Map<string, number>();

    for (const c of NATIONAL_CORRIDORS) {
      const stationSet = new Set(c.stations.map((s) => s.code.toUpperCase()));
      let count = 0;

      for (const p of positions) {
        const cur = p.current_station_code?.toUpperCase();
        const nxt = p.next_station_code?.toUpperCase();
        if ((cur && stationSet.has(cur)) || (nxt && stationSet.has(nxt))) {
          count++;
        }
      }
      counts.set(c.id, count);
    }
    return counts;
  }, [positions]);

  return (
    <div className="corridor-selector-strip">
      <div className="corridor-selector-label">
        <span className="corridor-selector-tag">[SELECT CORRIDOR]</span>
        <span className="corridor-selector-title">ACTIVE NATIONAL CTC CORRIDORS:</span>
      </div>

      <div className="corridor-chips-scroll">
        {NATIONAL_CORRIDORS.map((c: NationalCorridor) => {
          const isActive = c.id === activeCorridorId;
          const trainCount = corridorTrainCounts.get(c.id) || 0;

          return (
            <button
              key={c.id}
              className={`corridor-chip-btn ${isActive ? 'active' : ''}`}
              onClick={() => onSelectCorridor(c.id)}
              title={`${c.name} (${c.totalKm} km)`}
            >
              <span className="corridor-chip-name">{c.shortName}</span>
              <span className="corridor-chip-dist">{c.totalKm} km</span>
              <span className={`corridor-chip-badge ${trainCount > 0 ? 'has-trains' : ''}`}>
                {trainCount} {trainCount === 1 ? 'TRN' : 'TRNS'}
              </span>
            </button>
          );
        })}
      </div>
    </div>
  );
};

export default CorridorSelector;
