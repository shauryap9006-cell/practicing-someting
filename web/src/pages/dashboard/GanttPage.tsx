import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/lib/api';
import { queryKeys } from '@/lib/queryKeys';
import { PlatformInfo, PlatformSlot, StationCode } from '@/mock/types';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { DataFreshnessBadge } from '@/components/common/DataFreshnessBadge';
import { Play, Sparkles, AlertTriangle, CheckCircle2, RefreshCw, ZoomIn } from 'lucide-react';
import { toast } from 'sonner';

export const GanttPage: React.FC = () => {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [stationCode, setStationCode] = useState<StationCode>('NDLS');
  const [isSolving, setIsSolving] = useState(false);
  const [lastResolvedSummary, setLastResolvedSummary] = useState<string | null>(null);
  const [currentTimeMinutes, setCurrentTimeMinutes] = useState(17 * 60 + 40); // 17:40
  const [activeTab, setActiveTab] = useState<'all' | 'conflicts'>('all');

  const containerRef = useRef<HTMLDivElement>(null);

  const { data: platforms = [], dataUpdatedAt } = useQuery({
    queryKey: queryKeys.platforms(stationCode),
    queryFn: () => api.getPlatforms(stationCode),
  });

  // Update virtual time line
  useEffect(() => {
    const timer = setInterval(() => {
      const now = new Date();
      setCurrentTimeMinutes(now.getHours() * 60 + now.getMinutes());
    }, 5000);
    return () => clearInterval(timer);
  }, []);

  const reoptMutation = useMutation({
    mutationFn: () => api.reoptimizePlatforms(stationCode),
    onSuccess: (res) => {
      queryClient.invalidateQueries({ queryKey: queryKeys.platforms(stationCode) });
      setLastResolvedSummary(`Resolved ${res.resolvedCount || 1} conflict via ${res.swapsCount || 1} platform swaps in 1.38s.`);
      toast.success('Platform Plan Re-Optimized', {
        description: `Resolved all headway conflicts. New platform routing broadcast to signal cabin.`,
      });
    },
    onError: (err: any) => {
      toast.error('Optimization Failed', { description: err?.message || 'Solver error' });
    },
  });

  const handleReoptimize = async () => {
    setIsSolving(true);
    try {
      await reoptMutation.mutateAsync();
    } finally {
      setIsSolving(false);
    }
  };

  // Timeline bounds: 16:00 (960 min) to 22:00 (1320 min) -> 360 min window
  const startWindowMins = 16 * 60;
  const endWindowMins = 22 * 60;
  const totalWindowMins = endWindowMins - startWindowMins;

  // Calculate current time position percentage
  const nowPercent = Math.max(0, Math.min(100, ((currentTimeMinutes - startWindowMins) / totalWindowMins) * 100));

  const totalConflicts = platforms.reduce(
    (acc, p) => acc + p.slots.filter(s => s.isConflict).length,
    0
  );

  return (
    <div className="space-y-4 font-sans">
      {/* Header Toolbar */}
      <div className="bg-panel border border-hairline p-4 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 bg-accent inline-block" />
            <h2 className="text-base font-bold font-mono tracking-tight text-text-main">
              {stationCode} PLATFORM OCCUPANCY TIMELINE & CONFLICT SOLVER
            </h2>
          </div>
          <p className="text-xs text-text-dim mt-0.5 font-sans">
            Window: 16:00 – 22:00 IST · Dynamic collision interlock with automatic swap recommendations.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <DataFreshnessBadge dataUpdatedAt={dataUpdatedAt} />
          <Button
            variant="primary"
            size="md"
            isLoading={isSolving}
            onClick={handleReoptimize}
            className="text-xs font-semibold gap-1.5 shrink-0"
          >
            <Sparkles className="w-3.5 h-3.5 stroke-[1.5]" />
            <span>1-Click Re-Optimize Plan</span>
          </Button>
        </div>
      </div>

      {/* Solver summary banner if re-optimized */}
      {lastResolvedSummary && (
        <div className="p-3 bg-ok/10 border border-ok text-ok text-xs font-mono flex items-center justify-between animate-in fade-in">
          <div className="flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 shrink-0 stroke-[2]" />
            <span>{lastResolvedSummary}</span>
          </div>
          <button
            onClick={() => setLastResolvedSummary(null)}
            className="text-ok hover:underline text-[11px]"
          >
            Dismiss
          </button>
        </div>
      )}

      {/* Mobile pinch to zoom hint chip per §12 */}
      <div className="lg:hidden flex items-center gap-1.5 px-2.5 py-1 bg-panel-2 border border-hairline text-text-dim text-[11px] font-mono">
        <ZoomIn className="w-3.5 h-3.5 stroke-[1.5]" />
        <span>Scroll horizontally or pinch to zoom timeline</span>
      </div>

      {/* Interactive Gantt Canvas Container */}
      <div className="bg-panel border border-hairline overflow-x-auto" ref={containerRef}>
        <div className="min-w-[900px] p-4">
          {/* Time axis header */}
          <div className="flex border-b border-hairline pb-2 mb-2 text-[11px] font-mono text-text-dim">
            <div className="w-24 shrink-0 font-semibold text-text-main">PLATFORM</div>
            <div className="flex-1 grid grid-cols-6 text-center">
              <div>16:00</div>
              <div>17:00</div>
              <div>18:00</div>
              <div>19:00</div>
              <div>20:00</div>
              <div>21:00</div>
            </div>
          </div>

          {/* Gantt Rows per Platform */}
          <div className="space-y-2 relative">
            {/* Moving live Time Rule line */}
            {nowPercent >= 0 && nowPercent <= 100 && (
              <div
                className="absolute top-0 bottom-0 w-px bg-accent z-20 pointer-events-none transition-all duration-1000"
                style={{ left: `calc(6rem + (100% - 6rem) * ${nowPercent / 100})` }}
              >
                <div className="absolute -top-3 -left-5 bg-accent text-bg font-mono font-bold text-[9px] px-1 shadow">
                  NOW
                </div>
              </div>
            )}

            {platforms.map(p => {
              const hasConflict = p.slots.some(s => s.isConflict);
              return (
                <div key={p.platformNumber} className="flex items-center group">
                  {/* Platform Label */}
                  <div className="w-24 shrink-0 flex items-center gap-1.5 pr-2">
                    <span className="font-mono font-bold text-xs text-text-main">
                      PF {p.platformNumber.toString().padStart(2, '0')}
                    </span>
                    {hasConflict && (
                      <span className="w-2 h-2 bg-danger rounded-none animate-ping" title="Conflict on platform" />
                    )}
                  </div>

                  {/* Platform Track Bar */}
                  <div className="flex-1 h-9 bg-panel-2 border border-hairline/60 relative overflow-hidden">
                    {/* Hour divider marks */}
                    <div className="absolute inset-0 grid grid-cols-6 pointer-events-none divide-x divide-hairline/30" />

                    {/* Occupancy Slots */}
                    {p.slots.map(slot => {
                      // Calculate slot position within the 16:00-22:00 window
                      const slotStart = Math.max(startWindowMins, slot.startMinutes);
                      const slotEnd = Math.min(endWindowMins, slot.endMinutes);
                      if (slotEnd <= slotStart) return null;

                      const leftPercent = ((slotStart - startWindowMins) / totalWindowMins) * 100;
                      const widthPercent = Math.max(8, ((slotEnd - slotStart) / totalWindowMins) * 100);

                      return (
                        <div
                          key={slot.id}
                          onClick={() => navigate(`/dashboard/trains/${slot.trainNo}`)}
                          className={`absolute top-1 bottom-1 px-2 flex items-center justify-between text-xs font-mono cursor-pointer transition-all hover:brightness-125 z-10 select-none ${
                            slot.isConflict
                              ? 'bg-danger/25 border-2 border-danger text-danger font-bold animate-pulse'
                              : slot.status === 'reassigned'
                              ? 'bg-ok/20 border border-ok text-ok font-semibold'
                              : 'bg-panel border border-hairline hover:border-accent text-text-main'
                          }`}
                          style={{
                            left: `${leftPercent}%`,
                            width: `${widthPercent}%`,
                          }}
                          title={`Train ${slot.trainNo}: ${slot.trainName} (${slot.arrivalTime} - ${slot.departureTime})`}
                        >
                          <div className="truncate flex items-center gap-1.5">
                            <span className="font-bold">{slot.trainNo}</span>
                            <span className="text-[10px] opacity-80 hidden md:inline truncate">{slot.trainName}</span>
                          </div>
                          <span className="text-[10px] opacity-75 shrink-0 ml-1">
                            {slot.arrivalTime}
                          </span>
                        </div>
                      );
                    })}
                  </div>
                </div>
              );
            })}
          </div>

          {/* Legend */}
          <div className="mt-6 pt-3 border-t border-hairline flex flex-wrap items-center justify-between gap-4 text-[11px] font-mono text-text-dim">
            <div className="flex items-center gap-4">
              <div className="flex items-center gap-1.5">
                <span className="w-3 h-3 bg-panel border border-hairline inline-block" />
                <span>Scheduled / Nominal</span>
              </div>
              <div className="flex items-center gap-1.5">
                <span className="w-3 h-3 bg-danger/30 border border-danger inline-block" />
                <span>Headway Collision / Conflict</span>
              </div>
              <div className="flex items-center gap-1.5">
                <span className="w-3 h-3 bg-ok/20 border border-ok inline-block" />
                <span>Re-Optimized Slot</span>
              </div>
              <div className="flex items-center gap-1.5">
                <span className="w-0.5 h-3 bg-accent inline-block" />
                <span>Current Time Rule</span>
              </div>
            </div>

            <div>
              Click any block to inspect train journey & delay autopsy →
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
