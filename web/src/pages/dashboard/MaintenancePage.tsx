import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/api';
import { queryKeys } from '@/lib/queryKeys';
import { MaintenanceBlock } from '@/mock/types';
import { Badge } from '@/components/ui/Badge';
import { DataFreshnessBadge } from '@/components/common/DataFreshnessBadge';
import { Wrench, Clock, ShieldAlert, AlertTriangle, CheckCircle2 } from 'lucide-react';

export const MaintenancePage: React.FC = () => {
  const { data: blocks = [], dataUpdatedAt } = useQuery({
    queryKey: queryKeys.maintenance(),
    queryFn: () => api.getMaintenance(),
  });

  return (
    <div className="space-y-4 font-sans">
      {/* Header */}
      <div className="bg-panel border border-hairline p-4 space-y-2 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <h2 className="text-base font-bold font-mono text-text-main flex items-center gap-2">
            <Wrench className="w-4 h-4 text-accent stroke-[1.5]" />
            <span>24-HOUR CORRIDOR TRACK MAINTENANCE BLOCKS</span>
          </h2>
          <p className="text-xs text-text-dim">
            Permanent Speed Restrictions (PSR), power blocks, and civil engineering work. Dynamic speed curves inject section delay buffers into upcoming train ETA confidence bands.
          </p>
        </div>
        <DataFreshnessBadge dataUpdatedAt={dataUpdatedAt} />
      </div>

      {/* 24-Hour Visual Timeline Grid */}
      <div className="bg-panel border border-hairline p-4 space-y-3 font-mono text-xs">
        <div className="flex items-center justify-between border-b border-hairline pb-2 text-[11px] text-text-dim uppercase">
          <span>Corridor Track Timeline</span>
          <span>Active Window: 00:00 – 24:00 IST</span>
        </div>

        {/* 24h Axis Marks */}
        <div className="grid grid-cols-6 text-center text-[10px] text-text-dim border-b border-hairline/60 pb-1">
          <div>00:00</div>
          <div>04:00</div>
          <div>08:00</div>
          <div>12:00</div>
          <div>16:00</div>
          <div>20:00</div>
        </div>

        <div className="space-y-3 pt-2">
          {blocks.map(block => {
            const startHour = parseInt(block.startTime.split(':')[0], 10);
            const startMin = parseInt(block.startTime.split(':')[1], 10);
            const startMins = startHour * 60 + startMin;
            const durationMins = block.durationHours * 60;
            const leftPercent = (startMins / 1440) * 100;
            const widthPercent = Math.max(10, (durationMins / 1440) * 100);

            return (
              <div key={block.id} className="space-y-1">
                <div className="flex items-center justify-between text-xs">
                  <div className="flex items-center gap-2">
                    <span className="font-bold text-text-main">{block.blockRef}</span>
                    <span className="text-text-dim text-[11px] font-sans">({block.section} · {block.trackId})</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-accent font-bold">PSR {block.speedRestrictionKmph} km/h</span>
                    <Badge variant={block.status === 'active' ? 'warn' : block.status === 'upcoming' ? 'neutral' : 'ok'}>
                      {block.status.toUpperCase()}
                    </Badge>
                  </div>
                </div>

                {/* Track visual block */}
                <div className="h-7 bg-panel-2 border border-hairline/60 relative overflow-hidden">
                  <div
                    className={`absolute top-0 bottom-0 px-2 flex items-center justify-between text-[11px] font-bold truncate ${
                      block.status === 'active'
                        ? 'bg-warn/25 border-l-2 border-r-2 border-warn text-warn'
                        : block.status === 'upcoming'
                        ? 'bg-panel border border-hairline text-text-dim'
                        : 'bg-ok/20 border border-ok text-ok'
                    }`}
                    style={{ left: `${leftPercent}%`, width: `${widthPercent}%` }}
                  >
                    <span className="truncate">{block.workType}</span>
                    <span className="text-[10px] opacity-80 shrink-0 ml-1">{block.startTime}–{block.endTime}</span>
                  </div>
                </div>

                <div className="text-[11px] text-text-dim font-sans">
                  {block.advisoryNote} <span className="font-mono text-text-main">Affected trains: {block.affectedTrains.join(', ')}</span>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Block Details Cards List */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {blocks.map(block => (
          <div key={block.id} className="bg-panel border border-hairline p-4 space-y-2 text-xs">
            <div className="flex items-start justify-between">
              <div>
                <span className="font-mono font-bold text-accent">{block.blockRef}</span>
                <h3 className="font-bold text-text-main font-sans mt-0.5">{block.workType}</h3>
              </div>
              <Badge variant={block.status === 'active' ? 'warn' : block.status === 'upcoming' ? 'neutral' : 'ok'}>
                {block.status.toUpperCase()}
              </Badge>
            </div>

            <div className="grid grid-cols-2 gap-2 text-xs font-mono bg-panel-2 p-2.5 border border-hairline">
              <div>
                <span className="text-text-dim text-[10px] block">Section:</span>
                <span className="text-text-main font-semibold">{block.section}</span>
              </div>
              <div>
                <span className="text-text-dim text-[10px] block">Track / Line:</span>
                <span className="text-text-main font-semibold">{block.trackId}</span>
              </div>
              <div>
                <span className="text-text-dim text-[10px] block">Time Window:</span>
                <span className="text-text-main font-semibold">{block.startTime} – {block.endTime} ({block.durationHours}h)</span>
              </div>
              <div>
                <span className="text-text-dim text-[10px] block">Speed Caution (PSR):</span>
                <span className="text-accent font-bold">{block.speedRestrictionKmph} km/h</span>
              </div>
            </div>

            <p className="text-[11px] text-text-dim font-sans leading-relaxed">
              {block.advisoryNote}
            </p>

            <div className="pt-2 border-t border-hairline text-[11px] font-mono text-text-dim flex items-center justify-between">
              <span>Rerouted / Impacted:</span>
              <span className="font-bold text-text-main">{block.affectedTrains.join(', ')}</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
