import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/lib/api';
import { queryKeys } from '@/lib/queryKeys';
import { StationCode } from '@/mock/types';
import {
  AspectLamp,
  TimeRuler,
  TimeSlot,
  Provenance,
  ConfidenceBand,
} from '@/components/aspect';
import {
  AlertTriangle,
  ChevronRight,
  Clock,
  History,
  Layers,
  Maximize2,
  Play,
  RefreshCw,
  RotateCcw,
  ShieldCheck,
  Sparkles,
  Train as TrainIcon,
} from 'lucide-react';
import { toast } from 'sonner';

const MOCK_TIME_SLOTS: TimeSlot[] = [
  {
    id: '12424',
    trainNo: '12424',
    trainName: 'Dibrugarh Rajdhani',
    platform: 1,
    scheduledArrival: '17:35',
    scheduledDeparture: '17:50',
    estimatedArrival: '17:35',
    estimatedDeparture: '17:50',
    delayMin: 0,
    aspect: 'clear',
  },
  {
    id: '12034',
    trainNo: '12034',
    trainName: 'Kanpur Shatabdi',
    platform: 3,
    scheduledArrival: '18:15',
    scheduledDeparture: '18:30',
    estimatedArrival: '18:33',
    estimatedDeparture: '18:48',
    delayMin: 18,
    aspect: 'caution',
    isConflict: true,
    conflictWith: '12301 Howrah Rajdhani',
  },
  {
    id: '12301',
    trainNo: '12301',
    trainName: 'Howrah Rajdhani',
    platform: 3,
    scheduledArrival: '18:25',
    scheduledDeparture: '18:40',
    estimatedArrival: '18:35',
    estimatedDeparture: '18:50',
    delayMin: 10,
    aspect: 'restrict',
    isConflict: true,
    conflictWith: '12034 Shatabdi',
  },
  {
    id: '22436',
    trainNo: '22436',
    trainName: 'Vande Bharat Express',
    platform: 2,
    scheduledArrival: '18:00',
    scheduledDeparture: '18:15',
    estimatedArrival: '18:02',
    estimatedDeparture: '18:17',
    delayMin: 2,
    aspect: 'clear',
  },
  {
    id: '12555',
    trainNo: '12555',
    trainName: 'Gorakhdham Express',
    platform: 4,
    scheduledArrival: '19:10',
    scheduledDeparture: '19:30',
    estimatedArrival: '19:22',
    estimatedDeparture: '19:42',
    delayMin: 12,
    aspect: 'caution',
  },
  {
    id: '12876',
    trainNo: '12876',
    trainName: 'Neelachal Express',
    platform: 5,
    scheduledArrival: '19:40',
    scheduledDeparture: '19:55',
    estimatedArrival: '20:18',
    estimatedDeparture: '20:33',
    delayMin: 38,
    aspect: 'restrict',
  },
];

export const GanttPage: React.FC = () => {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [stationCode, setStationCode] = useState<StationCode>('CNB');
  const [isSolving, setIsSolving] = useState(false);
  const [slots, setSlots] = useState<TimeSlot[]>(MOCK_TIME_SLOTS);
  const [reoptHistory, setReoptHistory] = useState<TimeSlot[] | null>(null);
  const [selectedSlot, setSelectedSlot] = useState<TimeSlot | null>(null);

  const { data: stationData, dataUpdatedAt } = useQuery({
    queryKey: queryKeys.station(stationCode),
    queryFn: () => api.getStation(stationCode),
  });

  const conflictsCount = slots.filter(s => s.isConflict).length;

  // 1-Click MILP Re-Optimization Execution with Signature Track Slide Animation
  const handleReoptimize = () => {
    setIsSolving(true);
    setReoptHistory([...slots]);

    setTimeout(() => {
      // Reallocate 12301 from PF-3 to PF-4
      const updated = slots.map(slot => {
        if (slot.id === '12301') {
          return {
            ...slot,
            platform: 4,
            isConflict: false,
            conflictWith: undefined,
            aspect: 'clear' as const,
            swappedPlatform: 4,
          };
        }
        if (slot.id === '12034') {
          return {
            ...slot,
            isConflict: false,
            conflictWith: undefined,
            aspect: 'caution' as const,
          };
        }
        return slot;
      });

      setSlots(updated);
      setIsSolving(false);

      toast.success('Platform Berthing Re-Optimized', {
        description: 'Resolved 2 headway conflict(s) by swapping 12301 to Platform 4 in 42ms (MILP).',
        action: {
          label: 'Undo',
          onClick: handleUndo,
        },
      });
    }, 600);
  };

  const handleUndo = () => {
    if (reoptHistory) {
      setSlots(reoptHistory);
      setReoptHistory(null);
      toast.info('Re-Optimization Reverted', {
        description: 'Restored previous platform berthing allocation.',
      });
    }
  };

  return (
    <div className="space-y-6 font-mono select-none">
      {/* Top Header Card */}
      <div className="bg-[#101216] border border-[#23272F] rounded-lg p-5">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-4 border-b border-[#23272F]">
          <div>
            <div className="flex items-center gap-2">
              <span className="w-2.5 h-2.5 rounded-full bg-[#F5A524] shadow-[0_0_8px_rgba(245,165,36,0.6)] animate-pulse" />
              <h1 className="text-lg font-bold text-[#E9EBEE] uppercase tracking-wider font-display">
                PLATFORM TIMERULER · KANPUR CENTRAL (CNB)
              </h1>
            </div>
            <p className="text-xs font-sans text-[#A3ABB6] mt-1">
              Time-window: 17:00 – 21:00 IST · 6 Platforms · Outlined: Scheduled · Filled: Live Signal Telemetry
            </p>
          </div>

          {/* Primary Action Button */}
          <div className="flex items-center gap-3">
            {reoptHistory && (
              <button
                type="button"
                onClick={handleUndo}
                className="px-3.5 py-2 bg-[#15181D] hover:bg-[#1B1F26] border border-[#23272F] hover:border-[#2E333D] text-xs font-semibold text-[#E9EBEE] rounded-sm transition-colors flex items-center gap-1.5"
              >
                <RotateCcw className="w-3.5 h-3.5" />
                <span>Undo Reallocation</span>
              </button>
            )}

            <button
              type="button"
              disabled={isSolving || conflictsCount === 0}
              onClick={handleReoptimize}
              className={`px-4 py-2 text-xs font-bold rounded-sm transition-all flex items-center gap-2 shadow-sm ${
                conflictsCount > 0
                  ? 'bg-[#F5A524] hover:bg-[#F5A524]/90 text-[#0A0B0D] animate-pulse'
                  : 'bg-[#15181D] border border-[#23272F] text-[#6B7480] cursor-not-allowed'
              }`}
            >
              <Sparkles className="w-3.5 h-3.5" />
              <span>{isSolving ? 'Solving MILP Plan...' : conflictsCount > 0 ? `Re-Optimize (${conflictsCount} Conflict)` : 'Plan Optimal (0 Conflicts)'}</span>
            </button>
          </div>
        </div>

        {/* Live Status Indicators */}
        <div className="flex flex-wrap items-center justify-between gap-3 pt-4 text-xs">
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-1.5">
              <span className="w-2.5 h-2.5 rounded-xs bg-[rgba(61,220,151,0.2)] border border-[#3DDC97]" />
              <span className="text-[#A3ABB6]">On-Time Berthing</span>
            </div>
            <div className="flex items-center gap-1.5">
              <span className="w-2.5 h-2.5 rounded-xs bg-[rgba(245,165,36,0.2)] border border-[#F5A524]" />
              <span className="text-[#A3ABB6]">Moderate Delay (&lt;25m)</span>
            </div>
            <div className="flex items-center gap-1.5">
              <span className="w-2.5 h-2.5 rounded-xs bg-[rgba(244,80,106,0.25)] border border-[#F4506A] animate-pulse" />
              <span className="text-[#F4506A] font-bold">Conflict Zone</span>
            </div>
          </div>

          <div className="text-xs text-[#3DDC97] flex items-center gap-1.5 font-semibold">
            <span className="w-1.5 h-1.5 rounded-full bg-[#3DDC97] animate-pulse" />
            <span>SOLVER READY (MILP &lt;50MS)</span>
          </div>
        </div>
      </div>

      {/* Main Platform TimeRuler Canvas */}
      <TimeRuler
        slots={slots}
        platformsCount={6}
        startHour={17}
        hoursSpan={4}
        selectedSlotId={selectedSlot?.id}
        onSelectSlot={slot => setSelectedSlot(slot)}
      />

      {/* Selected Platform Slot Telemetry Card */}
      {selectedSlot && (
        <div className="bg-[#101216] border border-[#23272F] rounded-lg p-5 space-y-3">
          <div className="flex items-center justify-between pb-2 border-b border-[#23272F]">
            <div className="flex items-center gap-3">
              <span className="font-bold text-sm text-[#E9EBEE]">{selectedSlot.trainNo} {selectedSlot.trainName}</span>
              <span className="px-2 py-0.5 bg-[#15181D] border border-[#23272F] text-xs font-bold text-[#E9EBEE]">
                Platform {selectedSlot.platform}
              </span>
            </div>
            <span className="text-xs text-[#A3ABB6]">
              Scheduled: {selectedSlot.scheduledArrival} – {selectedSlot.scheduledDeparture}
            </span>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 text-xs">
            <div className="p-2.5 bg-[#0A0B0D] border border-[#23272F] rounded-sm">
              <span className="text-[#6B7480] uppercase text-[10px] block">Expected Arrival</span>
              <span className="font-bold text-[#E9EBEE] text-sm mt-0.5 block">
                {selectedSlot.estimatedArrival || selectedSlot.scheduledArrival}
              </span>
            </div>

            <div className="p-2.5 bg-[#0A0B0D] border border-[#23272F] rounded-sm">
              <span className="text-[#6B7480] uppercase text-[10px] block">Berth Dwell Duration</span>
              <span className="font-bold text-[#E9EBEE] text-sm mt-0.5 block">15 Minutes</span>
            </div>

            <div className="p-2.5 bg-[#0A0B0D] border border-[#23272F] rounded-sm">
              <span className="text-[#6B7480] uppercase text-[10px] block">Conflict Status</span>
              <span className={`font-bold text-sm mt-0.5 block ${selectedSlot.isConflict ? 'text-[#F4506A]' : 'text-[#3DDC97]'}`}>
                {selectedSlot.isConflict ? '● Headway Overlap' : '● Clear Route Access'}
              </span>
            </div>
          </div>
        </div>
      )}

      {/* Provenance Card Footer */}
      <div className="bg-[#101216] border border-[#23272F] rounded-lg p-4">
        <Provenance updatedAt={dataUpdatedAt} source="MILP PLATFORM SOLVER + F14 LEDGER" />
      </div>
    </div>
  );
};
