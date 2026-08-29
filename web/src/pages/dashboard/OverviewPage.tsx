import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/lib/api';
import { queryKeys } from '@/lib/queryKeys';
import { Train, Advisory, CrewMember, Station } from '@/mock/types';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { DataFreshnessBadge } from '@/components/common/DataFreshnessBadge';
import { formatMinutes } from '@/lib/utils';
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
} from 'lucide-react';
import { toast } from 'sonner';

const DEFAULT_STATION: Station = {
  code: 'NDLS',
  name: 'New Delhi',
  fullName: 'New Delhi Railway Station',
  division: 'Delhi',
  zone: 'NR',
  platformsCount: 16,
  activeTrainsCount: 8,
  platformConflictsCount: 1,
  pendingAdvisoriesCount: 3,
  crewWarningsCount: 2,
  corridorAvgDelayMinutes: 14,
};

export const OverviewPage: React.FC = () => {
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const { data: stationData, dataUpdatedAt } = useQuery({
    queryKey: queryKeys.station('NDLS'),
    queryFn: () => api.getStation('NDLS'),
  });
  const station = stationData || DEFAULT_STATION;

  const { data: trains = [] } = useQuery({
    queryKey: queryKeys.board('NDLS'),
    queryFn: () => api.getTrains(),
  });

  const { data: advisories = [] } = useQuery({
    queryKey: queryKeys.advisories(),
    queryFn: () => api.getAdvisories(),
  });

  const { data: crew = [] } = useQuery({
    queryKey: queryKeys.crew(),
    queryFn: () => api.getCrew(),
  });

  const acceptMutation = useMutation({
    mutationFn: (adv: Advisory) => api.acceptAdvisory(adv.id, 'One-click sign-off from control room overview'),
    onSuccess: (_, adv) => {
      queryClient.invalidateQueries({ queryKey: queryKeys.advisories() });
      toast.success(`Advisory ${adv.code} Accepted`, {
        description: `Plan updated: ${adv.recommendedAction}`,
      });
    },
  });

  const dismissMutation = useMutation({
    mutationFn: (adv: Advisory) => api.dismissAdvisory(adv.id, 'Dispatcher override'),
    onSuccess: (_, adv) => {
      queryClient.invalidateQueries({ queryKey: queryKeys.advisories() });
      toast.info(`Advisory ${adv.code} Dismissed`, {
        description: 'Retained current dispatch plan.',
      });
    },
  });

  const handleQuickAccept = (adv: Advisory) => {
    acceptMutation.mutate(adv);
  };

  const handleQuickDismiss = (adv: Advisory) => {
    dismissMutation.mutate(adv);
  };

  const activeConflictsCount = advisories.filter(a => a.status === 'pending' && a.priority === 'danger').length;
  const pendingAdvList = advisories.filter(a => a.status === 'pending').slice(0, 3);
  const criticalCrewList = crew.filter(c => c.status !== 'ok').slice(0, 4);

  return (
    <div className="space-y-6">
      {/* 1. Hairline-Divided Counters Strip (not cards) per §9 */}
      <div className="border border-hairline bg-panel grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 divide-y sm:divide-y-0 sm:divide-x divide-hairline">
        {/* Active Trains */}
        <Link
          to="/dashboard/trains"
          className="p-3 sm:p-4 hover:bg-panel-2 transition-colors group"
        >
          <div className="text-[11px] font-mono uppercase tracking-wider text-text-dim group-hover:text-text-main">
            Active Corridor Trains
          </div>
          <div className="text-xl sm:text-2xl font-bold font-mono text-text-main mt-1">
            {trains.length}
          </div>
          <div className="text-[10px] text-text-dim font-mono mt-0.5">
            {station.code} Junction Area
          </div>
        </Link>

        {/* Platform Conflicts */}
        <Link
          to="/dashboard/gantt"
          className={`p-3 sm:p-4 hover:bg-panel-2 transition-colors group ${
            activeConflictsCount > 0 ? 'bg-danger/5' : ''
          }`}
        >
          <div className="text-[11px] font-mono uppercase tracking-wider text-text-dim group-hover:text-text-main">
            Platform Conflicts
          </div>
          <div
            className={`text-xl sm:text-2xl font-bold font-mono mt-1 ${
              activeConflictsCount > 0 ? 'text-danger' : 'text-ok'
            }`}
          >
            {activeConflictsCount}
          </div>
          <div className="text-[10px] text-text-dim font-mono mt-0.5">
            {activeConflictsCount > 0 ? 'Action required on PF3' : 'No headway overlap'}
          </div>
        </Link>

        {/* Pending Advisories */}
        <Link
          to="/dashboard/advisories"
          className="p-3 sm:p-4 hover:bg-panel-2 transition-colors group"
        >
          <div className="text-[11px] font-mono uppercase tracking-wider text-text-dim group-hover:text-text-main">
            Pending Advisories
          </div>
          <div
            className={`text-xl sm:text-2xl font-bold font-mono mt-1 ${
              advisories.filter(a => a.status === 'pending').length > 0 ? 'text-warn' : 'text-text-main'
            }`}
          >
            {advisories.filter(a => a.status === 'pending').length}
          </div>
          <div className="text-[10px] text-text-dim font-mono mt-0.5">
            Awaiting Human Sign-Off
          </div>
        </Link>

        {/* Crew Duty Warnings */}
        <Link
          to="/dashboard/crew"
          className={`p-3 sm:p-4 hover:bg-panel-2 transition-colors group ${
            criticalCrewList.length > 0 ? 'bg-warn/5' : ''
          }`}
        >
          <div className="text-[11px] font-mono uppercase tracking-wider text-text-dim group-hover:text-text-main">
            Crew Breach Warnings
          </div>
          <div
            className={`text-xl sm:text-2xl font-bold font-mono mt-1 ${
              criticalCrewList.length > 0 ? 'text-warn' : 'text-ok'
            }`}
          >
            {criticalCrewList.length}
          </div>
          <div className="text-[10px] text-text-dim font-mono mt-0.5">
            &lt;2.0h to 10h Limit
          </div>
        </Link>

        {/* Corridor Avg Delay */}
        <div className="p-3 sm:p-4 col-span-2 sm:col-span-1">
          <div className="text-[11px] font-mono uppercase tracking-wider text-text-dim">
            Corridor Avg Delay
          </div>
          <div className="text-xl sm:text-2xl font-bold font-mono text-text-main mt-1">
            {station.corridorAvgDelayMinutes}m
          </div>
          <div className="text-[10px] text-ok font-mono mt-0.5">
            -38.7% vs NTES error
          </div>
        </div>
      </div>

      {/* Main Grid: Live Departure Station Board (Left 8 cols) + Right Rail Advisories & Crew (Right 4 cols) */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left: Live Station Departure Board */}
        <div className="lg:col-span-8 space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span className="w-2 h-2 bg-ok inline-block" />
              <h2 className="text-sm font-semibold font-mono tracking-tight text-text-main">
                {station.code} · LIVE STATION BOARD (UPCOMING ARRIVALS)
              </h2>
            </div>
            <Link
              to="/dashboard/trains"
              className="text-xs font-mono text-text-dim hover:text-accent flex items-center gap-1 transition-colors"
            >
              <span>Full Directory ({trains.length})</span>
              <ChevronRight className="w-3.5 h-3.5 stroke-[1.5]" />
            </Link>
          </div>

          {/* Departure-Board Table */}
          <div className="border border-hairline bg-panel overflow-x-auto">
            <table className="w-full text-left text-xs font-mono border-collapse" role="table">
              <thead>
                <tr className="bg-panel-2 border-b border-hairline text-text-dim text-[11px] uppercase">
                  <th scope="col" className="p-2.5">Train</th>
                  <th scope="col" className="p-2.5">Route</th>
                  <th scope="col" className="p-2.5">Sched</th>
                  <th scope="col" className="p-2.5">ETA Band (p10 / p50 / p90)</th>
                  <th scope="col" className="p-2.5">PF</th>
                  <th scope="col" className="p-2.5">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-hairline">
                {trains.slice(0, 10).map(train => {
                  const isConflict = train.platform === 3 && train.status === 'critical';
                  return (
                    <tr
                      key={train.number}
                      onClick={() => navigate(`/dashboard/trains/${train.number}`)}
                      className="hover:bg-panel-2/60 cursor-pointer transition-colors group"
                    >
                      <td className="p-2.5 whitespace-nowrap">
                        <div className="font-bold text-accent group-hover:underline">
                          {train.number}
                        </div>
                        <div className="font-sans text-[11px] text-text-dim truncate max-w-[150px]">
                          {train.name}
                        </div>
                      </td>
                      <td className="p-2.5 whitespace-nowrap text-text-dim text-[11px]">
                        <div>{train.origin} → {train.destination}</div>
                        <div className="text-[10px] text-text-dim/80">{train.routePosition}</div>
                      </td>
                      <td className="p-2.5 whitespace-nowrap text-text-dim">
                        {train.scheduledArrival}
                      </td>
                      <td className="p-2.5 whitespace-nowrap">
                        <div key={`${train.number}-${dataUpdatedAt}`} className="flex items-center gap-1.5 flash-updated">
                          <span className="text-text-dim text-[11px]">{train.etaBand.p10}</span>
                          <span className="font-bold text-text-main">{train.etaBand.p50}</span>
                          <span className="text-text-dim text-[11px]">{train.etaBand.p90}</span>
                        </div>
                      </td>
                      <td className="p-2.5 whitespace-nowrap">
                        <span
                          className={`px-2 py-0.5 font-bold ${
                            isConflict
                              ? 'bg-danger/20 border border-danger text-danger'
                              : 'bg-panel-2 border border-hairline text-text-main'
                          }`}
                        >
                          PF{train.platform}
                        </span>
                      </td>
                      <td className="p-2.5 whitespace-nowrap">
                        {train.delayMinutes === 0 ? (
                          <Badge variant="ok">ON TIME</Badge>
                        ) : train.delayMinutes > 20 ? (
                          <Badge variant="danger">{formatMinutes(train.delayMinutes)}</Badge>
                        ) : (
                          <Badge variant="warn">{formatMinutes(train.delayMinutes)}</Badge>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>

        {/* Right Rail: Top Advisories + Critical Crew List */}
        <div className="lg:col-span-4 space-y-6">
          {/* Top Advisories */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <AlertTriangle className="w-4 h-4 text-accent stroke-[1.5]" />
                <h3 className="text-xs font-mono font-semibold uppercase tracking-wider text-text-main">
                  Priority Advisories
                </h3>
              </div>
              <Link to="/dashboard/advisories" className="text-[11px] font-mono text-text-dim hover:text-accent">
                All ({advisories.length}) →
              </Link>
            </div>

            <div className="space-y-2">
              {pendingAdvList.length === 0 ? (
                <div className="p-4 bg-panel border border-hairline text-center text-xs text-text-dim font-mono">
                  No pending advisories. Corridor nominal.
                </div>
              ) : (
                pendingAdvList.map(adv => (
                  <div
                    key={adv.id}
                    className={`p-3 bg-panel border text-xs space-y-2 ${
                      adv.priority === 'danger'
                        ? 'border-danger/80 bg-danger/5'
                        : 'border-hairline'
                    }`}
                  >
                    <div className="flex items-start justify-between gap-2">
                      <span className="font-mono font-bold text-text-main text-[11px]">
                        {adv.code} · {adv.trainNo}
                      </span>
                      <Badge variant={adv.priority === 'danger' ? 'danger' : adv.priority === 'warn' ? 'warn' : 'neutral'}>
                        {adv.priority.toUpperCase()}
                      </Badge>
                    </div>

                    <div className="font-semibold text-text-main font-sans text-xs">
                      {adv.title}
                    </div>

                    <p className="text-[11px] text-text-dim leading-relaxed font-sans">
                      {adv.rationale}
                    </p>

                    <div className="pt-1 border-t border-hairline flex items-center justify-between gap-2">
                      <span className="text-[10px] font-mono text-ok">
                        +{adv.simulatedImpact.delaySavingsMinutes}m saved
                      </span>
                      <div className="flex items-center gap-1.5">
                        <Button
                          variant="primary"
                          size="sm"
                          onClick={() => handleQuickAccept(adv)}
                          className="h-6 px-2 text-[11px]"
                        >
                          <Check className="w-3 h-3 stroke-[2] mr-1" />
                          Accept
                        </Button>
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => handleQuickDismiss(adv)}
                          className="h-6 px-2 text-[11px]"
                        >
                          <X className="w-3 h-3 stroke-[2]" />
                        </Button>
                      </div>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>

          {/* Critical Crew Duty Section */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Users className="w-4 h-4 text-text-dim stroke-[1.5]" />
                <h3 className="text-xs font-mono font-semibold uppercase tracking-wider text-text-main">
                  Crew Duty Watch
                </h3>
              </div>
              <Link to="/dashboard/crew" className="text-[11px] font-mono text-text-dim hover:text-accent">
                Roster →
              </Link>
            </div>

            <div className="bg-panel border border-hairline divide-y divide-hairline">
              {criticalCrewList.map(member => (
                <div key={member.id} className="p-3 text-xs space-y-1.5">
                  <div className="flex items-center justify-between">
                    <span className="font-semibold text-text-main font-sans">{member.name}</span>
                    <Badge variant={member.status === 'critical' ? 'danger' : 'warn'}>
                      {member.remainingHours}h remaining
                    </Badge>
                  </div>
                  <div className="flex items-center justify-between text-[11px] font-mono text-text-dim">
                    <span>Train {member.trainNo}</span>
                    <span>Relief: {member.reliefStation}</span>
                  </div>
                  {/* Inline visual duty bar per §9 */}
                  <div className="w-full bg-panel-2 h-1.5 border border-hairline/60 overflow-hidden">
                    <div
                      className={`h-full ${
                        member.status === 'critical' ? 'bg-danger' : 'bg-warn'
                      }`}
                      style={{
                        width: `${Math.min(100, (member.dutyHoursSoFar / member.maxAllowedHours) * 100)}%`,
                      }}
                    />
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
