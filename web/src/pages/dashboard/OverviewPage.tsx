import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/lib/api';
import { queryKeys } from '@/lib/queryKeys';
import { Train, Advisory, CrewMember, Station } from '@/mock/types';
import {
  AspectLamp,
  CorridorSpine,
  TrainChip,
  Provenance,
  ConfidenceBand,
} from '@/components/aspect';
import {
  AlertTriangle,
  Users,
  TrainTrack,
  Clock,
  ArrowRight,
  ShieldCheck,
  Check,
  X,
  ChevronRight,
  Sparkles,
  Command,
} from 'lucide-react';
import { toast } from 'sonner';

const DEFAULT_STATION: Station = {
  code: 'CNB',
  name: 'Kanpur Central',
  fullName: 'Kanpur Central Junction',
  division: 'Prayagraj',
  zone: 'NCR',
  platformsCount: 10,
  activeTrainsCount: 8,
  platformConflictsCount: 1,
  pendingAdvisoriesCount: 3,
  crewWarningsCount: 2,
  corridorAvgDelayMinutes: 14,
};

export const OverviewPage: React.FC = () => {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [activeTab, setActiveTab] = useState<'departures' | 'advisories' | 'crew'>('departures');

  const { data: stationData, dataUpdatedAt } = useQuery({
    queryKey: queryKeys.station('CNB'),
    queryFn: () => api.getStation('CNB'),
  });
  const station = stationData || DEFAULT_STATION;

  const { data: trains = [] } = useQuery({
    queryKey: queryKeys.board('CNB'),
    queryFn: () => api.getTrains(),
    refetchInterval: 5000,
  });

  const { data: advisories = [] } = useQuery({
    queryKey: queryKeys.advisories(),
    queryFn: () => api.getAdvisories(),
    refetchInterval: 5000,
  });

  const { data: crew = [] } = useQuery({
    queryKey: queryKeys.crew(),
    queryFn: () => api.getCrew(),
    refetchInterval: 5000,
  });

  const acceptMutation = useMutation({
    mutationFn: (adv: Advisory) => api.acceptAdvisory(adv.id, 'One-click sign-off from Duty Board'),
    onSuccess: (_, adv) => {
      queryClient.invalidateQueries({ queryKey: queryKeys.advisories() });
      toast.success(`Advisory ${adv.code} Accepted`, {
        description: `Dispatch plan updated: ${adv.recommendedAction}`,
      });
    },
  });

  const activeConflicts = advisories.filter(a => a.status === 'pending' && a.priority === 'danger');
  const pendingAdvisories = advisories.filter(a => a.status === 'pending');
  const criticalCrew = crew.filter(c => c.status !== 'ok');

  // Next 90 Minutes Trains
  const next90MinTrains = trains.slice(0, 5);

  return (
    <div className="space-y-6 font-mono select-none">
      {/* 1. TOP ATTENTION BANNER — "NEEDS ATTENTION" (ALERTS FIRST) */}
      <div className="bg-[#101216] border border-[#23272F] rounded-lg p-5">
        <div className="flex items-center justify-between pb-3 border-b border-[#23272F]">
          <div className="flex items-center gap-2.5">
            <span className="w-2.5 h-2.5 rounded-full bg-[#F4506A] shadow-[0_0_8px_rgba(244,80,106,0.7)] animate-pulse" />
            <span className="font-bold text-xs uppercase tracking-widest text-[#E9EBEE]">
              NEEDS ATTENTION · {activeConflicts.length + (criticalCrew.length > 0 ? 1 : 0)}
            </span>
          </div>
          <div className="flex items-center gap-3 text-xs">
            <span className="text-[#3DDC97] flex items-center gap-1.5 font-semibold">
              <span className="w-1.5 h-1.5 rounded-full bg-[#3DDC97] animate-ping" />
              LIVE TELEMETRY (5S)
            </span>
            <kbd className="hidden sm:inline-flex items-center gap-1 px-2 py-0.5 bg-[#15181D] border border-[#23272F] text-[10px] text-[#A3ABB6] rounded-sm">
              <Command className="w-3 h-3" /> K
            </kbd>
          </div>
        </div>

        {/* Priority Action Items List */}
        <div className="divide-y divide-[#23272F] mt-2">
          {/* Platform Conflict Alert Item */}
          <div className="py-3.5 flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-[rgba(244,80,106,0.06)] px-3 rounded-sm border-l-2 border-[#F4506A] my-1.5">
            <div className="flex items-center gap-3">
              <span className="w-2 h-2 rounded-full bg-[#F4506A]" />
              <div>
                <span className="font-bold text-xs text-[#E9EBEE]">
                  PF-2 Headway Conflict 19:42 — 12301 Howrah vs 12424 Dibrugarh
                </span>
                <span className="block text-[11px] font-sans text-[#A3ABB6] mt-0.5">
                  Simultaneous 15-min dwell on single berth. MILP solver proposes swapping 12301 to PF-4.
                </span>
              </div>
            </div>

            <div className="flex items-center gap-2 shrink-0">
              <Link
                to="/dashboard/gantt"
                className="px-3 py-1.5 bg-[#F5A524] hover:bg-[#F5A524]/90 text-[#0A0B0D] font-bold text-xs rounded-sm transition-colors shadow-sm flex items-center gap-1"
              >
                <Sparkles className="w-3.5 h-3.5" />
                <span>Re-Optimize Plan</span>
              </Link>
              <Link
                to="/dashboard/gantt"
                className="px-3 py-1.5 bg-[#15181D] hover:bg-[#1B1F26] border border-[#23272F] text-[#E9EBEE] text-xs font-semibold rounded-sm transition-colors"
              >
                Inspect Gantt
              </Link>
            </div>
          </div>

          {/* Crew Relief Warning Item */}
          <div className="py-3.5 flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-[rgba(245,165,36,0.06)] px-3 rounded-sm border-l-2 border-[#F5A524] my-1.5">
            <div className="flex items-center gap-3">
              <span className="w-2 h-2 rounded-full bg-[#F5A524]" />
              <div>
                <span className="font-bold text-xs text-[#E9EBEE]">
                  LP Sharma (12301) — 1h 20m to 10-Hour Statutory Duty Expiry
                </span>
                <span className="block text-[11px] font-sans text-[#A3ABB6] mt-0.5">
                  Running duty hours: 08h 40m. Requires relief crew handover at Kanpur Central.
                </span>
              </div>
            </div>

            <div className="flex items-center gap-2 shrink-0">
              <Link
                to="/dashboard/crew"
                className="px-3 py-1.5 bg-[#15181D] hover:bg-[#1B1F26] border border-[#F5A524] text-[#F5A524] font-bold text-xs rounded-sm transition-colors"
              >
                Plan Relief Handover →
              </Link>
            </div>
          </div>
        </div>
      </div>

      {/* 2. HAIRLINE-DIVIDED COUNTERS STRIP (Aspect Tokens) */}
      <div className="border border-[#23272F] bg-[#101216] rounded-lg grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 divide-y sm:divide-y-0 sm:divide-x divide-[#23272F] overflow-hidden">
        {/* Active Trains */}
        <Link
          to="/dashboard/trains"
          className="p-4 hover:bg-[#15181D] transition-colors group"
        >
          <div className="text-[11px] font-mono uppercase tracking-wider text-[#A3ABB6] group-hover:text-[#E9EBEE]">
            Active Fleet
          </div>
          <div className="text-2xl font-bold text-[#E9EBEE] mt-1 tabular-nums">
            {trains.length}
          </div>
          <div className="text-[10px] text-[#6B7480] mt-0.5">
            {station.code} Corridor Division
          </div>
        </Link>

        {/* Platform Conflicts */}
        <Link
          to="/dashboard/gantt"
          className={`p-4 hover:bg-[#15181D] transition-colors group ${
            activeConflicts.length > 0 ? 'bg-[rgba(244,80,106,0.06)]' : ''
          }`}
        >
          <div className="text-[11px] font-mono uppercase tracking-wider text-[#A3ABB6] group-hover:text-[#E9EBEE]">
            Platform Conflicts
          </div>
          <div
            className={`text-2xl font-bold mt-1 tabular-nums ${
              activeConflicts.length > 0 ? 'text-[#F4506A]' : 'text-[#3DDC97]'
            }`}
          >
            {activeConflicts.length}
          </div>
          <div className="text-[10px] text-[#6B7480] mt-0.5">
            {activeConflicts.length > 0 ? 'PF-2 Headway Overlap' : 'Clear Berthing Slots'}
          </div>
        </Link>

        {/* Pending Advisories */}
        <Link
          to="/dashboard/advisories"
          className="p-4 hover:bg-[#15181D] transition-colors group"
        >
          <div className="text-[11px] font-mono uppercase tracking-wider text-[#A3ABB6] group-hover:text-[#E9EBEE]">
            Pending Advisories
          </div>
          <div
            className={`text-2xl font-bold mt-1 tabular-nums ${
              pendingAdvisories.length > 0 ? 'text-[#F5A524]' : 'text-[#E9EBEE]'
            }`}
          >
            {pendingAdvisories.length}
          </div>
          <div className="text-[10px] text-[#6B7480] mt-0.5">
            {pendingAdvisories.length > 0 ? 'Requires Controller Sign-Off' : 'Nominal State'}
          </div>
        </Link>

        {/* Crew Watch */}
        <Link
          to="/dashboard/crew"
          className="p-4 hover:bg-[#15181D] transition-colors group"
        >
          <div className="text-[11px] font-mono uppercase tracking-wider text-[#A3ABB6] group-hover:text-[#E9EBEE]">
            Crew Limits
          </div>
          <div
            className={`text-2xl font-bold mt-1 tabular-nums ${
              criticalCrew.length > 0 ? 'text-[#F5A524]' : 'text-[#3DDC97]'
            }`}
          >
            {criticalCrew.length}
          </div>
          <div className="text-[10px] text-[#6B7480] mt-0.5">
            {criticalCrew.length > 0 ? '>8h Duty Roster Alert' : '100% HOER Compliant'}
          </div>
        </Link>

        {/* Corridor Mean Delay */}
        <div className="p-4 bg-[#101216]">
          <div className="text-[11px] font-mono uppercase tracking-wider text-[#A3ABB6]">
            Corridor Avg Delay
          </div>
          <div className="text-2xl font-bold text-[#F5A524] mt-1 tabular-nums">
            +14.2m
          </div>
          <div className="text-[10px] text-[#3DDC97] mt-0.5">
            ▼ 38.7% vs NTES Baseline
          </div>
        </div>
      </div>

      {/* 3. NEXT 90 MINUTES TIMELINE BOARD */}
      <div className="bg-[#101216] border border-[#23272F] rounded-lg p-5 space-y-4">
        <div className="flex items-center justify-between pb-3 border-b border-[#23272F]">
          <div className="flex items-center gap-2">
            <span className="font-bold text-xs uppercase tracking-wider text-[#E9EBEE]">
              NEXT 90 MINUTES · INBOUND & PLATFORM BERTHS
            </span>
          </div>
          <Link
            to="/dashboard/trains"
            className="text-xs text-[#F5A524] hover:underline flex items-center gap-1 font-mono"
          >
            <span>View All {trains.length} Trains</span>
            <ChevronRight className="w-3.5 h-3.5" />
          </Link>
        </div>

        {/* Row Entries */}
        <div className="space-y-2">
          {next90MinTrains.map((train, idx) => {
            const aspect = train.delayMinutes <= 5 ? 'clear' : train.delayMinutes <= 25 ? 'caution' : 'restrict';

            return (
              <div
                key={train.number}
                className="p-3 bg-[#0A0B0D] border border-[#23272F] hover:border-[#2E333D] rounded-sm flex flex-col md:flex-row md:items-center justify-between gap-4 transition-colors"
              >
                {/* Left: Expected Time + Train Number + Name */}
                <div className="flex items-center gap-4 min-w-[280px]">
                  <div className="text-sm font-bold text-[#E9EBEE] tabular-nums">
                    {train.predictedArrival || '18:22'}
                  </div>

                  <div className="flex items-center gap-2">
                    <span className="font-bold text-xs text-[#E9EBEE]">{train.number}</span>
                    <span className="text-xs font-sans text-[#A3ABB6] truncate max-w-[140px] sm:max-w-[200px]">
                      {train.name}
                    </span>
                  </div>
                </div>

                {/* Middle: Aspect Lamp + Delay + Platform */}
                <div className="flex items-center gap-4">
                  <AspectLamp
                    aspect={aspect}
                    label={train.delayMinutes <= 0 ? 'CLEAR (ON TIME)' : `+${train.delayMinutes}M`}
                    size="sm"
                  />

                  <span className="px-2 py-0.5 bg-[#15181D] border border-[#23272F] text-xs text-[#E9EBEE] font-bold rounded-xs">
                    PF-{train.platform || (idx % 4 + 1)}
                  </span>

                  <span className="text-xs text-[#A3ABB6]">
                    {train.currentStation ? `at ${train.currentStation}` : `${(idx + 1) * 12} min out`}
                  </span>
                </div>

                {/* Right: Action */}
                <div className="flex items-center gap-2 shrink-0">
                  <Link
                    to={`/dashboard/trains/${train.number}`}
                    className="px-2.5 py-1 bg-[#15181D] hover:bg-[#1B1F26] border border-[#23272F] hover:border-[#F5A524] text-xs text-[#E9EBEE] font-semibold rounded-sm transition-colors"
                  >
                    Autopsy →
                  </Link>
                </div>
              </div>
            );
          })}
        </div>

        {/* Provenance Footer */}
        <Provenance updatedAt={dataUpdatedAt} source="NCR TELEMETRY + F14 LEDGER" />
      </div>

      {/* 4. LIVE CORRIDOR SPINE PANEL */}
      <div className="space-y-2">
        <CorridorSpine density="panel" />
      </div>
    </div>
  );
};
