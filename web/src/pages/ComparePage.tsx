import React, { useState, useEffect, useCallback } from 'react';
import { api } from '../lib/api';
import type { ComparatorData } from '../lib/types';
import { SectionShell, StatCard, LoadingState, ErrorState, ReceiptChip } from '../primitives';

export const ComparePage: React.FC = () => {
  const [selectedTrain, setSelectedTrain] = useState<string>('12301');
  const [comparator, setComparator] = useState<ComparatorData | null>(null);
  const [loading, setLoading] = useState(true);
  const [injecting, setInjecting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const trains = [
    { no: '12301', name: 'Howrah Rajdhani' },
    { no: '12004', name: 'Lucknow Shatabdi' },
    { no: '12424', name: 'DBRT Rajdhani' },
    { no: '12560', name: 'Shiv Ganga Express' },
  ];

  const shocks = [
    {
      type: 'SIGNAL_FAILURE',
      label: 'Signal Failure (+25m)',
      station: 'GZB',
      severity: 25,
      desc: 'Automatic signalling interlocking dropped at Ghaziabad Jn',
    },
    {
      type: 'TSR_SPEED_RESTRICTION',
      label: 'Speed Restriction (+14m)',
      station: 'ETW',
      severity: 14,
      desc: '30 km/h emergency caution order on Down main track',
    },
    {
      type: 'WEATHER_FOG',
      label: 'Corridor Fog (+35m)',
      station: 'ALJN',
      severity: 35,
      desc: 'Visibility < 100m between Aligarh and Tundla sections',
    },
    {
      type: 'RAKE_TURNAROUND',
      label: 'Yard Dwell (+40m)',
      station: 'LKO',
      severity: 40,
      desc: 'Carriage & Wagon mechanical clearance delay at coaching yard',
    },
  ];

  const fetchComparator = useCallback(async (trainNo: string) => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.demo.comparator(trainNo);
      setComparator(data);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : `Failed to load comparator data for train #${trainNo}.`
      );
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchComparator(selectedTrain);
  }, [selectedTrain, fetchComparator]);

  const handleInjectShock = async (shock: typeof shocks[0]) => {
    setInjecting(true);
    try {
      await api.demo.injectEvent({
        event_type: shock.type,
        severity_min: shock.severity,
        station: shock.station,
        description: shock.desc,
      });
      // Refetch immediately
      await fetchComparator(selectedTrain);
    } catch (err) {
      alert('Failed to inject shock: ' + (err instanceof Error ? err.message : 'Unknown error'));
    } finally {
      setInjecting(false);
    }
  };

  const handleResetShocks = async () => {
    setInjecting(true);
    try {
      await api.demo.resetEvents();
      await fetchComparator(selectedTrain);
    } catch (err) {
      alert('Failed to reset shocks: ' + (err instanceof Error ? err.message : 'Unknown error'));
    } finally {
      setInjecting(false);
    }
  };

  const activeShocks = comparator?.active_shocks || [];
  const errors = comparator?.cumulative_errors;
  const stations = comparator?.stations || [];

  return (
    <div className="max-w-6xl mx-auto w-full p-4 sm:p-6 lg:p-8 flex flex-col gap-6">
      {/* Header */}
      <div className="flex flex-col gap-1 border-b border-line/60 pb-5">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-[2px] bg-ink" />
            <span className="font-mono text-micro uppercase tracking-wider text-muted font-medium">
              The Shock Lab · PS 26028
            </span>
          </div>
          {comparator?.ledger_receipt && (
            <ReceiptChip
              hash={comparator.ledger_receipt.receipt_hash}
              status="SEALED"
            />
          )}
        </div>

        <h1 className="font-serif text-3xl sm:text-4xl font-bold tracking-tight text-ink">
          The Shock Lab & Model Comparator
        </h1>
        <p className="font-sans text-sm text-ink/75 max-w-2xl">
          Real-time head-to-head evaluation: RailTwin-X dynamic confidence interval vs
          Official NTES frozen baseline under simulated operational disturbances.
        </p>
      </div>

      {/* Train Selector Pills */}
      <div className="flex flex-wrap items-center gap-2">
        <span className="font-mono text-[11px] uppercase tracking-wider text-muted font-medium mr-1">
          Select Service:
        </span>
        {trains.map((t) => (
          <button
            key={t.no}
            type="button"
            onClick={() => setSelectedTrain(t.no)}
            className={`font-mono text-xs px-3 py-1.5 rounded-[3px] border transition-colors cursor-pointer flex items-center gap-2 ${
              selectedTrain === t.no
                ? 'bg-ink text-surface border-ink font-semibold'
                : 'bg-surface text-ink border-line hover:bg-raised'
            }`}
          >
            <span>#{t.no}</span>
            <span className="text-[11px] opacity-80">{t.name}</span>
          </button>
        ))}
      </div>

      {/* Shock Injection Control Deck */}
      <SectionShell
        microLabel="Live Disturbance Simulation"
        title="Inject Corridor Operational Shock"
        action={
          activeShocks.length > 0 ? (
            <button
              type="button"
              onClick={handleResetShocks}
              disabled={injecting}
              className="font-mono text-xs px-2.5 py-1 rounded-[3px] bg-raised border border-line text-ink hover:bg-surface transition-colors cursor-pointer font-medium"
            >
              RESET ALL SHOCKS ↺
            </button>
          ) : null
        }
      >
        <div className="flex flex-col gap-4">
          <p className="font-sans text-xs text-muted">
            Click any operational disturbance to inject a real incident into the corridor engine.
            Observe how the official static timetable remains frozen while RailTwin-X widens its confidence cone.
          </p>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-2.5">
            {shocks.map((shock) => {
              const isActive = activeShocks.some((as) => as.event_type === shock.type);

              return (
                <button
                  key={shock.type}
                  type="button"
                  onClick={() => handleInjectShock(shock)}
                  disabled={injecting}
                  className={`p-3 rounded-[3px] border text-left transition-all cursor-pointer flex flex-col justify-between gap-2 ${
                    isActive
                      ? 'bg-restrict/10 border-restrict text-restrict shadow-sm'
                      : 'bg-surface border-line hover:border-ink/60 hover:bg-raised/30 text-ink'
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <span className="font-mono font-bold text-xs">
                      {shock.label}
                    </span>
                    <span className="font-mono text-[10px] uppercase px-1 py-0.2 bg-raised border border-line rounded text-muted">
                      @{shock.station}
                    </span>
                  </div>
                  <span className="font-sans text-[11px] text-muted leading-tight">
                    {shock.desc}
                  </span>
                  <div className="pt-1 border-t border-line/40 flex items-center justify-between font-mono text-[10px]">
                    <span className={isActive ? 'text-restrict font-bold' : 'text-muted'}>
                      {isActive ? '● ACTIVE SHOCK' : '+ INJECT'}
                    </span>
                    <span className="text-muted">+{shock.severity}m</span>
                  </div>
                </button>
              );
            })}
          </div>

          {/* Active Shocks Bar */}
          {activeShocks.length > 0 && (
            <div className="p-3 bg-restrict/5 border border-restrict/30 rounded-[3px] flex flex-wrap items-center justify-between gap-2">
              <div className="flex items-center gap-2">
                <span className="w-2 h-2 rounded-[2px] bg-restrict animate-pulse" />
                <span className="font-mono text-xs font-bold text-restrict">
                  {activeShocks.length} Active Operational Disturbance{activeShocks.length > 1 ? 's' : ''} Injected
                </span>
              </div>
              <div className="flex flex-wrap items-center gap-1.5 font-mono text-xs">
                {activeShocks.map((as, i) => (
                  <span
                    key={i}
                    className="px-2 py-0.5 bg-surface border border-restrict/30 rounded text-restrict text-[11px]"
                  >
                    {as.event_type} @ {as.station} (+{as.severity_min}m)
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      </SectionShell>

      {/* Loading or Content */}
      {loading ? (
        <LoadingState rows={4} message="Computing benchmark comparator telemetry..." />
      ) : error ? (
        <ErrorState
          title="Comparator Evaluation Error"
          message={error}
          onRetry={() => fetchComparator(selectedTrain)}
        />
      ) : (
        <>
          {/* Split Verdict Scoreboard Banner */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Left: Official NTES Baseline */}
            <div className="p-5 bg-surface border border-line rounded-[4px] flex flex-col justify-between gap-4">
              <div className="flex items-center justify-between border-b border-line/60 pb-2.5">
                <div className="flex items-center gap-2">
                  <span className="w-2 h-2 rounded-[2px] bg-muted" />
                  <span className="font-mono text-micro uppercase tracking-wider text-muted font-medium">
                    Baseline · Official NTES
                  </span>
                </div>
                <span className="font-mono text-[11px] px-2 py-0.5 bg-raised border border-line rounded text-muted">
                  Static Frozen
                </span>
              </div>

              <div className="flex flex-col gap-1">
                <span className="font-mono text-3xl font-bold text-ink tabular-nums">
                  {errors ? `${errors.b2_official_mae.toFixed(2)} min` : '--'}
                </span>
                <span className="font-sans text-xs text-muted">
                  Mean Absolute Error (MAE) across evaluated stops
                </span>
              </div>

              <div className="p-3 bg-raised/40 border border-line/60 rounded-[3px] text-xs font-sans text-muted">
                Assumes nominal section running times until train physically breaches a signal block. Zero forward shock anticipation.
              </div>
            </div>

            {/* Right: RailTwin-X Dynamic Cone */}
            <div className="p-5 bg-surface border-2 border-ink rounded-[4px] flex flex-col justify-between gap-4">
              <div className="flex items-center justify-between border-b border-line/60 pb-2.5">
                <div className="flex items-center gap-2">
                  <span className="w-2 h-2 rounded-[2px] bg-clear" />
                  <span className="font-mono text-micro uppercase tracking-wider text-ink font-bold">
                    RailTwin-X Dynamic Twin
                  </span>
                </div>
                <span className="font-mono text-[11px] px-2 py-0.5 bg-clear/10 border border-clear/30 rounded text-clear font-semibold">
                  Probabilistic P10–P90
                </span>
              </div>

              <div className="flex flex-col gap-1">
                <div className="flex items-baseline gap-3">
                  <span className="font-mono text-3xl font-bold text-ink tabular-nums">
                    {errors ? `${errors.railtwin_p50_mae.toFixed(2)} min` : '--'}
                  </span>
                  {errors && (
                    <span className="font-mono text-sm font-bold text-clear px-2 py-0.5 bg-clear/10 rounded">
                      +{errors.railtwin_vs_official_gain_pct}% GAIN
                    </span>
                  )}
                </div>
                <span className="font-sans text-xs text-muted">
                  Mean Absolute Error (MAE) with corridor entropy conditioning
                </span>
              </div>

              <div className="p-3 bg-raised/40 border border-line/60 rounded-[3px] text-xs font-sans text-ink/85">
                Adapts downstream confidence cone in &lt;400ms following operational disturbances. Cryptographically sealed into SHA-256 audit ledger.
              </div>
            </div>
          </div>

          {/* Cumulative Scoreboard Cards */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <StatCard
              label="Official NTES MAE"
              value={errors ? `${errors.b2_official_mae.toFixed(1)}m` : '--'}
              subtext="Static benchmark error"
              deltaType="negative"
            />
            <StatCard
              label="RailTwin-X MAE"
              value={errors ? `${errors.railtwin_p50_mae.toFixed(1)}m` : '--'}
              subtext="P50 ensemble error"
              deltaType="positive"
            />
            <StatCard
              label="Predictive Gain"
              value={errors ? `+${errors.railtwin_vs_official_gain_pct}%` : '--'}
              subtext="Error reduction vs NTES"
              deltaType="positive"
            />
            <StatCard
              label="Stations Verified"
              value={errors ? `${errors.samples_evaluated} Stops` : '--'}
              subtext="Tested downstream"
            />
          </div>

          {/* Station Benchmark Breakdown Table */}
          <SectionShell
            microLabel="Downstream Checkpoints"
            title="Station-by-Station Arrival Forecast Comparison"
            action={
              <span className="font-mono text-xs text-muted">
                {stations.length} corridor stations
              </span>
            }
          >
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse text-xs">
                <thead>
                  <tr className="bg-raised border-b border-line">
                    <th className="px-3.5 py-2.5 font-mono text-[10px] uppercase text-muted">
                      Station
                    </th>
                    <th className="px-3.5 py-2.5 font-mono text-[10px] uppercase text-muted text-right">
                      Distance
                    </th>
                    <th className="px-3.5 py-2.5 font-mono text-[10px] uppercase text-muted text-center">
                      State
                    </th>
                    <th className="px-3.5 py-2.5 font-mono text-[10px] uppercase text-muted text-right">
                      Official Delay
                    </th>
                    <th className="px-3.5 py-2.5 font-mono text-[10px] uppercase text-ink text-right font-bold">
                      RailTwin P50
                    </th>
                    <th className="px-3.5 py-2.5 font-mono text-[10px] uppercase text-muted text-right">
                      Confidence Cone
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-line/60">
                  {stations.length === 0 ? (
                    <tr>
                      <td colSpan={6} className="py-6 text-center font-mono text-xs text-muted">
                        No station records found.
                      </td>
                    </tr>
                  ) : (
                    stations.map((stn) => {
                      const officialDelay = Math.round(stn.b2_official_delay_min);
                      const p50 = Math.round(stn.p50_delay_min);
                      const p10 = Math.round(stn.p10_delay_min);
                      const p90 = Math.round(stn.p90_delay_min);

                      return (
                        <tr
                          key={stn.station_code}
                          className={`hover:bg-raised/20 transition-colors ${
                            stn.is_current ? 'bg-raised/30' : ''
                          }`}
                        >
                          <td className="px-3.5 py-2.5">
                            <div className="flex items-center gap-2">
                              <span className="font-mono font-bold text-ink">
                                {stn.station_code}
                              </span>
                              <span className="font-sans text-muted">
                                {stn.station_name}
                              </span>
                            </div>
                          </td>
                          <td className="px-3.5 py-2.5 font-mono text-muted text-right tabular-nums">
                            {stn.distance_km} km
                          </td>
                          <td className="px-3.5 py-2.5 text-center">
                            <span
                              className={`font-mono text-[10px] uppercase px-1.5 py-0.2 rounded border ${
                                stn.is_passed
                                  ? 'bg-raised border-line text-muted'
                                  : stn.is_current
                                  ? 'bg-ochre/15 border-ochre/30 text-ochre font-bold'
                                  : 'bg-surface border-line text-ink'
                              }`}
                            >
                              {stn.is_passed ? 'PASSED' : stn.is_current ? 'CURRENT' : 'UPCOMING'}
                            </span>
                          </td>
                          <td className="px-3.5 py-2.5 font-mono text-right tabular-nums text-muted">
                            +{officialDelay}m
                          </td>
                          <td className="px-3.5 py-2.5 font-mono text-right tabular-nums font-bold text-ink">
                            +{p50}m
                          </td>
                          <td className="px-3.5 py-2.5 font-mono text-right tabular-nums text-muted">
                            [{p10}m &mdash; {p90}m]
                          </td>
                        </tr>
                      );
                    })
                  )}
                </tbody>
              </table>
            </div>
          </SectionShell>
        </>
      )}
    </div>
  );
};
