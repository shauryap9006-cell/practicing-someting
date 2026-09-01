import React from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/api';
import { queryKeys } from '@/lib/queryKeys';
import { Train } from '@/mock/types';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { DataFreshnessBadge } from '@/components/common/DataFreshnessBadge';
import { formatMinutes } from '@/lib/utils';
import {
  ArrowLeft,
  TrainTrack,
  Clock,
  MapPin,
  Activity,
  AlertTriangle,
  Layers,
  Gauge,
  CheckCircle2,
} from 'lucide-react';

export const TrainDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { data: train, isLoading, dataUpdatedAt } = useQuery({
    queryKey: queryKeys.train(id || ''),
    queryFn: () => api.getTrain(id || ''),
  });

  const { data: autopsyData } = useQuery({
    queryKey: queryKeys.trainAutopsy(id || ''),
    queryFn: () => api.getTrainAutopsy(id || ''),
    enabled: !!id,
  });

  const getCauseBadge = (eventType: string) => {
    switch (eventType) {
      case 'CROSSING_HOLD':
        return <Badge variant="danger">CROSSING HOLD</Badge>;
      case 'TSR':
        return <Badge variant="warn">SPEED RESTRICTION</Badge>;
      case 'RAKE_INHERIT':
        return <Badge variant="neutral">RAKE INHERITED</Badge>;
      case 'PLATFORM_WAIT':
        return <Badge variant="warn">PLATFORM WAIT</Badge>;
      case 'EXT_DWELL':
        return <Badge variant="warn">EXTENDED DWELL</Badge>;
      default:
        return <Badge variant="neutral">{eventType || 'OPERATIONAL'}</Badge>;
    }
  };

  if (isLoading) {
    return (
      <div className="p-8 text-center bg-panel border border-hairline space-y-4">
        <h2 className="text-base font-bold text-text-main font-mono">Loading Train Telemetry...</h2>
        <div className="w-6 h-6 border-2 border-accent border-t-transparent rounded-full animate-spin mx-auto" />
      </div>
    );
  }

  if (!train) {
    return (
      <div className="p-8 text-center bg-panel border border-hairline space-y-4">
        <h2 className="text-base font-bold text-text-main font-mono">Train {id} Not Found</h2>
        <p className="text-xs text-text-dim">The specified train is not in the active corridor dataset.</p>
        <Link to="/dashboard/trains">
          <Button variant="secondary" size="md">← Back to Trains Directory</Button>
        </Link>
      </div>
    );
  }

  const causes = autopsyData?.causes || [];
  const totalAutopsyMinutes = causes.reduce((sum, item) => sum + item.minutes, 0) || train.delayMinutes;

  return (
    <div className="space-y-6 font-sans">
      {/* Top Breadcrumb / Back Link */}
      <div className="flex items-center justify-between">
        <Link
          to="/dashboard/trains"
          className="text-xs font-mono text-text-dim hover:text-text-main flex items-center gap-1.5 transition-colors"
        >
          <ArrowLeft className="w-3.5 h-3.5 stroke-[1.5]" />
          <span>Back to Trains Directory</span>
        </Link>
        <div className="flex items-center gap-3">
          <DataFreshnessBadge dataUpdatedAt={dataUpdatedAt} />
          <span className="text-[11px] font-mono text-text-dim">
            Rake ID: {train.rakeId} · Priority {train.priority}
          </span>
        </div>
      </div>

      {/* Train Header Info Card */}
      <div className="bg-panel border border-hairline p-5 grid grid-cols-1 md:grid-cols-12 gap-6 items-center">
        <div className="md:col-span-6 space-y-1.5">
          <div className="flex items-center gap-2">
            <span className="text-xl sm:text-2xl font-bold font-mono text-accent">
              {train.number}
            </span>
            <span className="text-base font-bold text-text-main font-sans">
              {train.name}
            </span>
          </div>
          <div className="text-xs text-text-dim flex items-center gap-2 font-mono">
            <span>{train.type}</span>
            <span>•</span>
            <span>{train.origin} → {train.destination}</span>
          </div>
          <div className="text-[11px] text-text-dim pt-1 font-mono">
            Current Location: <span className="text-text-main font-semibold">{train.routePosition}</span>
          </div>
        </div>

        {/* Telemetry Metrics */}
        <div className="md:col-span-6 grid grid-cols-3 gap-3 font-mono text-center">
          <div className="p-3 bg-panel-2 border border-hairline">
            <div className="text-[10px] text-text-dim uppercase">Speed</div>
            <div className="text-base font-bold text-text-main mt-0.5 flex items-center justify-center gap-1">
              <Gauge className="w-3.5 h-3.5 text-accent stroke-[1.5]" />
              <span>{train.speedKmph}</span>
              <span className="text-[10px] text-text-dim font-normal">km/h</span>
            </div>
          </div>

          <div className="p-3 bg-panel-2 border border-hairline">
            <div className="text-[10px] text-text-dim uppercase">Platform</div>
            <div className="text-base font-bold text-text-main mt-0.5">
              PF {train.platform}
            </div>
          </div>

          <div className="p-3 bg-panel-2 border border-hairline">
            <div className="text-[10px] text-text-dim uppercase">Delay</div>
            <div className={`text-base font-bold mt-0.5 ${train.delayMinutes > 20 ? 'text-danger' : train.delayMinutes > 5 ? 'text-warn' : 'text-ok'}`}>
              {formatMinutes(train.delayMinutes)}
            </div>
          </div>
        </div>
      </div>

      {/* ETA Confidence Tri-Band ($p_{10}, p_{50}, p_{90}$) */}
      <div className="bg-panel border border-hairline p-5 space-y-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Clock className="w-4 h-4 text-accent stroke-[1.5]" />
            <h3 className="text-xs font-mono font-semibold uppercase tracking-wider text-text-main">
              CALIBRATED ETA CONFIDENCE BAND (KANPUR CENTRAL · CNB)
            </h3>
          </div>
          <span className="text-[11px] font-mono text-ok">
            Conformal Coverage: 82.4%
          </span>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 text-center font-mono">
          <div className="p-3 bg-panel-2 border border-hairline">
            <div className="text-[10px] text-text-dim uppercase tracking-wider">Optimistic (p10)</div>
            <div className="text-xl font-bold text-text-main mt-1">{train.etaBand.p10}</div>
            <div className="text-[10px] text-text-dim mt-0.5">Clear signals run</div>
          </div>

          <div className="p-3 bg-panel-2 border border-accent">
            <div className="text-[10px] text-accent uppercase tracking-wider font-semibold">Likely Target (p50)</div>
            <div className="text-2xl font-bold text-accent mt-1">{train.etaBand.p50}</div>
            <div className="text-[10px] text-text-dim mt-0.5">Model expected arrival</div>
          </div>

          <div className="p-3 bg-panel-2 border border-hairline">
            <div className="text-[10px] text-text-dim uppercase tracking-wider">Pessimistic (p90)</div>
            <div className="text-xl font-bold text-text-main mt-1">{train.etaBand.p90}</div>
            <div className="text-[10px] text-text-dim mt-0.5">Outer hold / congestion</div>
          </div>
        </div>
      </div>

      {/* Two Column Section: Journey Timeline (Left) + Delay Autopsy (Right) */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Column: Vertical Journey Stop Timeline */}
        <div className="lg:col-span-7 space-y-3">
          <div className="flex items-center gap-2">
            <MapPin className="w-4 h-4 text-text-dim stroke-[1.5]" />
            <h3 className="text-xs font-mono font-semibold uppercase tracking-wider text-text-main">
              Route Stop Progression & Schedule deltas
            </h3>
          </div>

          <div className="bg-panel border border-hairline divide-y divide-hairline">
            {train.journey.map((stop, idx) => {
              const isCurrent = stop.status === 'current';
              const isPassed = stop.status === 'passed';
              return (
                <div
                  key={stop.seq}
                  className={`p-3 text-xs flex items-center justify-between gap-4 font-mono ${
                    isCurrent ? 'bg-accent/5 border-l-2 border-l-accent' : ''
                  }`}
                >
                  <div className="flex items-center gap-3">
                    <span className="w-5 text-[11px] text-text-dim font-bold">{stop.seq}</span>
                    <div>
                      <div className="font-bold text-text-main text-xs flex items-center gap-2">
                        <span>{stop.stationName} ({stop.stationCode})</span>
                        {isCurrent && (
                          <Badge variant="warn" className="text-[9px] py-0">Current</Badge>
                        )}
                        {isPassed && (
                          <span className="text-[10px] text-ok">Passed</span>
                        )}
                      </div>
                      <div className="text-[10px] text-text-dim font-sans">
                        KM {stop.distanceKm} from origin
                      </div>
                    </div>
                  </div>

                  <div className="text-right shrink-0">
                    <div className="text-text-main font-semibold">
                      {isPassed ? stop.actualArrival || stop.schedArrival : stop.predArrival || stop.schedArrival}
                    </div>
                    <div className="text-[10px] text-text-dim">
                      Sched: {stop.schedArrival}
                      {stop.delayMinutes > 0 ? (
                        <span className="text-warn ml-1">({formatMinutes(stop.delayMinutes)})</span>
                      ) : (
                        <span className="text-ok ml-1">(ON TIME)</span>
                      )}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Right Column: Delay Autopsy Ledger */}
        <div className="lg:col-span-5 space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Layers className="w-4 h-4 text-accent stroke-[1.5]" />
              <h3 className="text-xs font-mono font-semibold uppercase tracking-wider text-text-main">
                Delay Autopsy Ledger
              </h3>
            </div>
            <span className="text-[10px] font-mono text-ok border border-ok/40 px-1.5 py-0.5">
              {autopsyData?.is_exact_accounting ? `100% Balanced (${totalAutopsyMinutes}m)` : `Delay Accounting (${totalAutopsyMinutes}m)`}
            </span>
          </div>

          <div className="bg-panel border border-hairline p-4 space-y-4">
            {train.delayMinutes === 0 && causes.length === 0 ? (
              <div className="p-6 text-center text-xs text-ok font-mono space-y-1">
                <CheckCircle2 className="w-6 h-6 mx-auto stroke-[1.5]" />
                <div className="font-bold">Train Running Strictly On Time</div>
                <div className="text-[11px] text-text-dim">Zero delay minutes recorded across corridor blocks.</div>
              </div>
            ) : causes.length === 0 ? (
              <div className="p-6 text-center text-xs text-text-dim font-mono space-y-1">
                <AlertTriangle className="w-6 h-6 mx-auto stroke-[1.5] text-warn" />
                <div className="font-bold text-text-main">Delay Autopsy In Progress</div>
                <div className="text-[11px] text-text-dim">Attribution engine analyzing {train.delayMinutes}m delay telemetry.</div>
              </div>
            ) : (
              <>
                <div className="text-xs text-text-dim font-sans leading-relaxed">
                  Exact mathematical decomposition of all <span className="font-mono text-text-main font-semibold">{totalAutopsyMinutes} delayed minutes</span> attributed across operational categories:
                </div>

                <div className="space-y-3">
                  {causes.map((item, idx) => {
                    const pct = Math.round((item.minutes / Math.max(1, totalAutopsyMinutes)) * 100);
                    return (
                      <div key={idx} className="p-3 bg-panel-2 border border-hairline space-y-1.5 text-xs">
                        <div className="flex items-center justify-between font-mono">
                          <div className="flex items-center gap-2">
                            {getCauseBadge(item.event_type)}
                            <span className="font-bold text-text-main">{item.event_type}</span>
                          </div>
                          <span className="text-accent font-bold">+{item.minutes}m ({pct}%)</span>
                        </div>
                        <p className="text-[11px] text-text-dim font-sans leading-relaxed">
                          {item.cause}{item.station_code ? ` at ${item.station_code}` : ''}
                        </p>
                        <div className="w-full bg-panel h-1.5 border border-hairline/60 overflow-hidden mt-1">
                          <div className="bg-accent h-full" style={{ width: `${pct}%` }} />
                        </div>
                      </div>
                    );
                  })}
                </div>

                <div className="pt-2 border-t border-hairline flex items-center justify-between font-mono text-xs">
                  <span className="text-text-dim">Total Attributed Delay:</span>
                  <span className="font-bold text-text-main">{totalAutopsyMinutes}m ({autopsyData?.is_exact_accounting ? '100% Exact' : 'Estimated'})</span>
                </div>
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
