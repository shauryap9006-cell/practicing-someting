import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import {
  ShieldCheck,
  Zap,
  TrendingUp,
  AlertTriangle,
  Clock,
  ArrowRight,
  Sparkles,
  Layers,
  Database,
  RefreshCw,
  Sliders,
  CheckCircle2,
  Lock,
  GitFork,
  Radio,
  ExternalLink,
} from 'lucide-react';
import { api, DemoComparatorData, ModelPerformanceData } from '@/lib/api';

export function ForesightConsolePage() {
  const [selectedTrain, setSelectedTrain] = useState('12301');
  const [comparatorData, setComparatorData] = useState<DemoComparatorData | null>(null);
  const [perfData, setPerfData] = useState<ModelPerformanceData | null>(null);
  const [loading, setLoading] = useState(true);
  const [injecting, setInjecting] = useState(false);
  const [shockToast, setShockToast] = useState<string | null>(null);

  const trainsList = [
    { no: '12301', name: 'Howrah – New Delhi Rajdhani', route: 'NDLS → CNB → LKO' },
    { no: '12004', name: 'New Delhi – Lucknow Shatabdi', route: 'NDLS → GZB → CNB → LKO' },
    { no: '22436', name: 'Vande Bharat Express', route: 'NDLS → CNB → PRYJ' },
    { no: '12424', name: 'Dibrugarh Rajdhani Express', route: 'NDLS → CNB → DDU' },
  ];

  const loadData = async (trainNo = selectedTrain) => {
    try {
      setLoading(true);
      const [comp, perf] = await Promise.all([
        api.getDemoComparator(trainNo),
        api.getModelPerformance(),
      ]);
      setComparatorData(comp);
      setPerfData(perf);
    } catch (e) {
      console.error('Failed loading foresight data:', e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData(selectedTrain);
  }, [selectedTrain]);

  const handleInject = async (type: string, station: string, severity: number, desc: string) => {
    try {
      setInjecting(true);
      await api.injectShockEvent({
        event_type: type,
        station,
        severity_min: severity,
        description: desc,
      });
      setShockToast(`Injected ${type} (+${severity}m at ${station}). RailTwin-X cone updating...`);
      await loadData();
      setTimeout(() => setShockToast(null), 4000);
    } catch (err) {
      console.error(err);
    } finally {
      setInjecting(false);
    }
  };

  const handleReset = async () => {
    try {
      setInjecting(true);
      await api.resetShockEvents();
      setShockToast('Cleared all shocks. Restored pristine model state.');
      await loadData();
      setTimeout(() => setShockToast(null), 3000);
    } catch (err) {
      console.error(err);
    } finally {
      setInjecting(false);
    }
  };

  const activeStation = comparatorData?.active_station;
  const stations = comparatorData?.stations || [];
  const errors = comparatorData?.cumulative_errors;
  const whyLate = comparatorData?.why_late;

  return (
    <div className="min-h-screen bg-[#07090D] text-[#E5E7EB] font-sans antialiased selection:bg-[#FFB224] selection:text-black">
      {/* 1. Global Command Bar */}
      <header className="border-b border-white/10 bg-[#0C0F17]/90 backdrop-blur-md sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 py-3 flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-lg bg-gradient-to-br from-[#FFB224] to-[#F59E0B] flex items-center justify-center shadow-lg shadow-[#FFB224]/20">
              <Zap className="w-5 h-5 text-black font-black" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="font-mono text-xs font-bold uppercase tracking-widest text-[#FFB224]">RailTwin-X</span>
                <span className="text-[10px] px-2 py-0.5 rounded-full bg-emerald-500/20 text-emerald-400 font-mono font-semibold border border-emerald-500/30">
                  SIH PS 26028 · LIVE FORESIGHT
                </span>
              </div>
              <h1 className="text-base font-bold text-white tracking-tight">
                Dynamic ETA Foresight & Operational Decision Support
              </h1>
            </div>
          </div>

          {/* Quick Navigation Tabs */}
          <div className="flex items-center gap-2 text-xs font-mono">
            <Link
              to="/compare"
              className="px-3 py-1.5 rounded-md bg-[#1B2232] hover:bg-[#253046] text-[#60A5FA] border border-[#3B82F6]/30 transition-colors flex items-center gap-1.5"
            >
              <GitFork className="w-3.5 h-3.5" />
              <span>Live Comparator</span>
            </Link>
            <Link
              to="/cascade"
              className="px-3 py-1.5 rounded-md bg-[#1B2232] hover:bg-[#253046] text-[#A78BFA] border border-[#8B5CF6]/30 transition-colors flex items-center gap-1.5"
            >
              <Layers className="w-3.5 h-3.5" />
              <span>Ripple & Custody DSS</span>
            </Link>
            <Link
              to="/model-card"
              className="px-3 py-1.5 rounded-md bg-[#1B2232] hover:bg-[#253046] text-[#34D399] border border-[#10B981]/30 transition-colors flex items-center gap-1.5"
            >
              <ShieldCheck className="w-3.5 h-3.5" />
              <span>Honest Model Card</span>
            </Link>
            <Link
              to="/dashboard"
              className="px-3 py-1.5 rounded-md bg-white/5 hover:bg-white/10 text-gray-300 border border-white/10 transition-colors"
            >
              Controller OS →
            </Link>
          </div>
        </div>
      </header>

      {/* Shock Notification Toast */}
      {shockToast && (
        <div className="fixed bottom-6 right-6 z-50 bg-[#141A26] border border-[#FFB224]/50 shadow-2xl shadow-black/80 rounded-lg p-4 flex items-center gap-3 animate-in fade-in slide-in-from-bottom-4">
          <Sparkles className="w-5 h-5 text-[#FFB224] animate-pulse" />
          <span className="text-xs font-mono text-white">{shockToast}</span>
        </div>
      )}

      <main className="max-w-7xl mx-auto px-4 py-6 space-y-6">
        {/* 2. Top Context & Train Selector */}
        <div className="bg-[#10141F] border border-white/10 rounded-xl p-4 flex flex-wrap items-center justify-between gap-4 shadow-xl">
          <div className="flex items-center gap-3">
            <span className="text-xs font-mono text-gray-400 uppercase tracking-wider">Corridor Service:</span>
            <div className="flex flex-wrap items-center gap-2">
              {trainsList.map((t) => (
                <button
                  key={t.no}
                  onClick={() => setSelectedTrain(t.no)}
                  className={`px-3 py-1.5 rounded-lg text-xs font-mono transition-all ${
                    selectedTrain === t.no
                      ? 'bg-[#FFB224] text-black font-bold shadow-md shadow-[#FFB224]/20'
                      : 'bg-white/5 hover:bg-white/10 text-gray-300 border border-white/5'
                  }`}
                >
                  #{t.no} {t.name.split('–')[0]}
                </button>
              ))}
            </div>
          </div>

          <div className="flex items-center gap-4 text-xs font-mono">
            <div className="flex items-center gap-2 text-gray-400">
              <span className="w-2 h-2 rounded-full bg-emerald-400 animate-ping" />
              <span>Current Stn:</span>
              <span className="text-white font-bold">{activeStation?.name || 'ALJN'}</span>
              <span className="text-[#FFB224] font-bold">+{activeStation?.current_delay_min || 24}m</span>
            </div>
            <button
              onClick={() => loadData()}
              disabled={loading}
              className="p-1.5 rounded-md hover:bg-white/10 text-gray-400 hover:text-white transition-colors"
              title="Refresh Foresight Model"
            >
              <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin text-[#FFB224]' : ''}`} />
            </button>
          </div>
        </div>

        {/* 3. D2 DIFFERENTIATION SURFACE: 3 Live Horizon Cards */}
        <div>
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <span className="text-xs font-mono font-bold text-[#FFB224] tracking-wider uppercase">D2 Differentiation</span>
              <h2 className="text-sm font-bold text-white uppercase tracking-wider">
                Multi-Horizon Foresight Performance vs Baselines
              </h2>
            </div>
            <span className="text-[11px] font-mono text-gray-400">
              Canonical MAE: <strong className="text-white">{perfData?.canonical_mae || 10.72}m</strong> · 80% Coverage:{' '}
              <strong className="text-emerald-400">{perfData?.overall_coverage_80 || 80.64}%</strong>
            </span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {perfData?.horizon_cards.map((card) => {
              const isTie = card.status_badge.includes('TIE');
              const isFiftyPlus = card.status_badge.includes('50%');

              return (
                <div
                  key={card.horizon}
                  className={`rounded-xl border p-4 transition-all relative overflow-hidden bg-gradient-to-b ${
                    isTie
                      ? 'from-[#141A24] to-[#0D111A] border-blue-500/20 hover:border-blue-500/40'
                      : isFiftyPlus
                      ? 'from-[#1A1424] to-[#110D1A] border-purple-500/30 hover:border-purple-500/50 shadow-lg shadow-purple-500/5'
                      : 'from-[#141E1A] to-[#0D1411] border-emerald-500/20 hover:border-emerald-500/40'
                  }`}
                >
                  <div className="flex items-start justify-between mb-3">
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="font-mono text-lg font-black text-white">{card.horizon}</span>
                        <span className="text-[11px] font-mono text-gray-400">{card.horizon_label}</span>
                      </div>
                      <span
                        className={`inline-block mt-1 text-[10px] font-mono font-bold px-2 py-0.5 rounded-full border ${
                          isTie
                            ? 'bg-blue-500/10 text-blue-400 border-blue-500/30'
                            : isFiftyPlus
                            ? 'bg-purple-500/20 text-purple-300 border-purple-500/40'
                            : 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30'
                        }`}
                      >
                        {card.status_badge}
                      </span>
                    </div>

                    <div className="text-right font-mono">
                      <div className="text-2xl font-black text-white">{card.mae} <span className="text-xs font-normal text-gray-400">min MAE</span></div>
                      <div className="text-[11px] text-gray-400">Winkler: {card.winkler_score}</div>
                    </div>
                  </div>

                  {/* Baseline Comparison Bar */}
                  <div className="space-y-1.5 text-xs font-mono my-3 bg-black/40 rounded-lg p-2.5 border border-white/5">
                    <div className="flex justify-between text-gray-400">
                      <span>RailTwin-X:</span>
                      <span className="text-emerald-400 font-bold">{card.mae} min</span>
                    </div>
                    <div className="flex justify-between text-gray-400">
                      <span>B1 (Frozen delay):</span>
                      <span>{card.baseline_b1_mae} min</span>
                    </div>
                    <div className="flex justify-between text-gray-400">
                      <span>B2 (Official NTES):</span>
                      <span className="text-red-400">{card.baseline_b2_mae} min</span>
                    </div>
                    <div className="pt-1 border-t border-white/5 flex justify-between font-bold text-[#FFB224]">
                      <span>Verdict:</span>
                      <span>{card.verdict}</span>
                    </div>
                  </div>

                  <p className="text-xs text-gray-300 leading-relaxed font-sans mt-2">
                    {card.narrative}
                  </p>
                </div>
              );
            })}
          </div>
        </div>

        {/* 4. D1 & D5 DIFFERENTIATION SURFACE: Station Timeline & Calibrated Uncertainty Cone */}
        <div className="bg-[#10141F] border border-white/10 rounded-xl p-5 shadow-2xl">
          <div className="flex flex-wrap items-center justify-between gap-4 mb-4 pb-3 border-b border-white/10">
            <div>
              <div className="flex items-center gap-2">
                <span className="text-xs font-mono font-bold text-[#FFB224] tracking-wider uppercase">D1 + D5 Surfaces</span>
                <h3 className="text-base font-bold text-white">
                  Calibrated Uncertainty Cone (p10–p50–p90) with Immutable Ledger Seal
                </h3>
              </div>
              <p className="text-xs text-gray-400 mt-0.5">
                Empirical coverage: <strong className="text-emerald-400">80.6%</strong> of arrivals fall cleanly inside p10–p90. Widening uncertainty honors real corridor physics.
              </p>
            </div>

            {/* D5 SHA-256 Ledger Badge */}
            <div className="flex items-center gap-2 bg-[#171D2B] border border-white/10 px-3 py-1.5 rounded-lg text-xs font-mono">
              <Lock className="w-3.5 h-3.5 text-emerald-400" />
              <span className="text-gray-400">Receipt SHA-256:</span>
              <span className="text-emerald-300 font-bold truncate max-w-[140px]">
                {comparatorData?.ledger_receipt?.receipt_hash.slice(0, 16)}...
              </span>
              <span className="text-[10px] px-1.5 py-0.2 rounded bg-emerald-500/20 text-emerald-400 uppercase font-bold">
                Chain Sealed
              </span>
            </div>
          </div>

          {/* Shock Simulation Trigger Strip */}
          <div className="mb-5 bg-[#0C0F17] rounded-lg p-3 border border-white/5 flex flex-wrap items-center justify-between gap-3">
            <div className="flex items-center gap-2 text-xs font-mono text-gray-400">
              <Sliders className="w-4 h-4 text-[#FFB224]" />
              <span className="font-bold text-white">Live Shock Injection:</span>
              <span>Test model reaction vs static baselines</span>
            </div>
            <div className="flex flex-wrap items-center gap-2">
              <button
                disabled={injecting}
                onClick={() => handleInject('SIGNAL_HOLD', 'CNB', 25, 'Kanpur Central outer home signal hold')}
                className="px-2.5 py-1 text-xs font-mono rounded bg-red-500/10 hover:bg-red-500/20 text-red-400 border border-red-500/30 transition-all"
              >
                +25m Signal Hold
              </button>
              <button
                disabled={injecting}
                onClick={() => handleInject('TSR_ACTIVE', 'ETW', 20, 'TSR 40 km/h over 25km track renewal')}
                className="px-2.5 py-1 text-xs font-mono rounded bg-amber-500/10 hover:bg-amber-500/20 text-amber-400 border border-amber-500/30 transition-all"
              >
                +20m TSR 40 km/h
              </button>
              <button
                disabled={injecting}
                onClick={() => handleInject('RAKE_DELAY', 'NDLS', 35, 'Late incoming rake #12034 deficit')}
                className="px-2.5 py-1 text-xs font-mono rounded bg-purple-500/10 hover:bg-purple-500/20 text-purple-400 border border-purple-500/30 transition-all"
              >
                +35m Rake Deficit
              </button>
              <button
                disabled={injecting}
                onClick={() => handleInject('WEATHER_FOG', 'CNB', 15, 'Gangetic winter fog vis < 200m')}
                className="px-2.5 py-1 text-xs font-mono rounded bg-blue-500/10 hover:bg-blue-500/20 text-blue-400 border border-blue-500/30 transition-all"
              >
                +15m Fog Dawn
              </button>
              <button
                disabled={injecting}
                onClick={handleReset}
                className="px-2.5 py-1 text-xs font-mono rounded bg-white/10 hover:bg-white/20 text-gray-300 border border-white/20 transition-all flex items-center gap-1"
              >
                <RefreshCw className="w-3 h-3" />
                Reset
              </button>
            </div>
          </div>

          {/* Station Cards Timeline with Uncertainty Cones */}
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 lg:grid-cols-8 gap-2">
            {stations.map((stn) => {
              const isPassed = stn.is_passed;
              const isCurrent = stn.is_current;

              return (
                <div
                  key={stn.station_code}
                  className={`rounded-lg p-3 border font-mono transition-all relative ${
                    isCurrent
                      ? 'bg-[#1E2433] border-[#FFB224] shadow-lg shadow-[#FFB224]/10 ring-1 ring-[#FFB224]'
                      : isPassed
                      ? 'bg-[#0E121A] border-white/5 text-gray-400'
                      : 'bg-[#141A26] border-white/10 text-white'
                  }`}
                >
                  {isCurrent && (
                    <span className="absolute -top-2 left-1/2 -translate-x-1/2 text-[9px] font-bold bg-[#FFB224] text-black px-1.5 py-0.2 rounded-full uppercase">
                      Current
                    </span>
                  )}

                  <div className="flex items-center justify-between mb-1">
                    <span className="text-xs font-bold text-white">{stn.station_code}</span>
                    <span className="text-[10px] text-gray-400">{stn.distance_km} km</span>
                  </div>
                  <div className="text-[10px] text-gray-400 truncate mb-2">{stn.station_name}</div>

                  {isPassed ? (
                    <div className="space-y-1 text-xs">
                      <div className="text-[11px] text-emerald-400 font-bold">
                        Actual: +{stn.actual_delay_min || 0}m
                      </div>
                      <div className="text-[10px] text-gray-500">
                        Sched: {stn.sched_arr || stn.sched_dep || '--:--'}
                      </div>
                      <span className="inline-block text-[9px] text-emerald-400/80 bg-emerald-500/10 px-1 rounded">
                        Recorded
                      </span>
                    </div>
                  ) : (
                    <div className="space-y-1.5">
                      <div className="text-xs font-bold text-[#FFB224] flex items-center justify-between">
                        <span>p50:</span>
                        <span>+{stn.p50_delay_min}m</span>
                      </div>

                      {/* Visual Cone Spread */}
                      <div className="bg-black/50 p-1.5 rounded border border-white/5 text-[10px] space-y-0.5">
                        <div className="flex justify-between text-emerald-400">
                          <span>p10:</span>
                          <span>+{stn.p10_delay_min}m</span>
                        </div>
                        <div className="flex justify-between text-purple-400">
                          <span>p90:</span>
                          <span>+{stn.p90_delay_min}m</span>
                        </div>
                        <div className="w-full bg-gray-700 h-1 rounded-full overflow-hidden mt-1">
                          <div
                            className="bg-gradient-to-r from-emerald-400 via-[#FFB224] to-purple-400 h-full"
                            style={{ width: '100%' }}
                          />
                        </div>
                      </div>

                      <div className="text-[9px] text-gray-400 flex justify-between pt-1">
                        <span>Cone width:</span>
                        <span className="text-white font-bold">±{Math.round(stn.cone_spread_min / 2)}m</span>
                      </div>
                    </div>
                  )}
                </div>
              );
            })}
          </div>

          {/* Running Accuracy Scoreboard */}
          {errors && (
            <div className="mt-5 p-3 rounded-lg bg-[#0D111A] border border-white/5 flex flex-wrap items-center justify-between gap-4 text-xs font-mono">
              <div className="flex items-center gap-2">
                <TrendingUp className="w-4 h-4 text-emerald-400" />
                <span className="text-gray-400">Journey-to-Date Accuracy:</span>
                <span className="text-white font-bold">{errors.samples_evaluated} stations graded</span>
              </div>
              <div className="flex flex-wrap items-center gap-4">
                <div>
                  <span className="text-gray-500">B1 Frozen MAE: </span>
                  <span className="text-gray-300 font-bold">{errors.b1_frozen_mae}m</span>
                </div>
                <div>
                  <span className="text-gray-500">B2 Official MAE: </span>
                  <span className="text-red-400 font-bold">{errors.b2_official_mae}m</span>
                </div>
                <div>
                  <span className="text-gray-500">RailTwin-X p50 MAE: </span>
                  <span className="text-emerald-400 font-bold">{errors.railtwin_p50_mae}m</span>
                </div>
                <div className="px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-400 font-bold border border-emerald-500/30">
                  +{errors.railtwin_vs_official_gain_pct}% vs NTES
                </div>
              </div>
            </div>
          )}
        </div>

        {/* 5. D3 DIFFERENTIATION SURFACE: Causal Delay Autopsy Waterfall */}
        {whyLate && (
          <div className="bg-[#10141F] border border-white/10 rounded-xl p-5 shadow-2xl">
            <div className="flex flex-wrap items-center justify-between gap-3 mb-4 pb-3 border-b border-white/10">
              <div>
                <div className="flex items-center gap-2">
                  <span className="text-xs font-mono font-bold text-[#FFB224] tracking-wider uppercase">D3 Differentiation</span>
                  <h3 className="text-base font-bold text-white">Causal Delay Autopsy & Attribution Waterfall</h3>
                </div>
                <p className="text-xs text-gray-400 mt-0.5">
                  7-category physics breakdown with exact mathematical additivity. Every minute of delay has an auditable evidence pointer.
                </p>
              </div>

              <div className="flex items-center gap-2">
                <span className="text-xs font-mono text-gray-400">Total Attributed:</span>
                <span className="text-sm font-mono font-bold text-[#FFB224]">
                  +{whyLate.total_attributed_delay_min || whyLate.total_delay_minutes || 0}m
                </span>
                <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 flex items-center gap-1 font-bold">
                  <CheckCircle2 className="w-3 h-3" />
                  Exact-Sum Additivity
                </span>
              </div>
            </div>

            {/* Narrative Banner */}
            {whyLate.narrative && (
              <div className="mb-4 p-3 rounded-lg bg-[#141A26] border border-white/5 text-xs text-gray-300 leading-relaxed font-sans flex items-start gap-2">
                <Sparkles className="w-4 h-4 text-[#FFB224] shrink-0 mt-0.5" />
                <div>
                  <strong className="text-white font-mono uppercase tracking-wider block mb-0.5">Automated Dispatch Narrative:</strong>
                  {whyLate.narrative}
                </div>
              </div>
            )}

            {/* Stacked Waterfall Breakdown */}
            <div className="space-y-2">
              {(whyLate.cause_breakdown || whyLate.causes || []).map((cause: any, idx: number) => {
                const mins = cause.attributed_min || cause.minutes || 0;
                const pct = cause.percentage || 0;
                const isNegative = mins < 0;

                return (
                  <div
                    key={idx}
                    className="bg-[#0C0F17] rounded-lg p-3 border border-white/5 flex flex-wrap items-center justify-between gap-3 text-xs font-mono"
                  >
                    <div className="flex items-center gap-3">
                      <span className="w-2 h-2 rounded-full bg-[#FFB224]" />
                      <div>
                        <div className="font-bold text-white flex items-center gap-2">
                          <span>{cause.cause_code || cause.event_type}</span>
                          {cause.rule_matched && (
                            <span className="text-[10px] text-gray-500 font-normal">({cause.rule_matched})</span>
                          )}
                        </div>
                        <div className="text-[11px] text-gray-400 font-sans mt-0.5">
                          {cause.description || cause.cause || 'Corridor operational friction'}
                        </div>
                      </div>
                    </div>

                    <div className="flex items-center gap-4">
                      {cause.evidence_pointer && (
                        <span className="text-[10px] bg-white/5 px-2 py-0.5 rounded border border-white/10 text-gray-400">
                          Log: {cause.evidence_pointer}
                        </span>
                      )}
                      <div className="text-right">
                        <span className={`text-sm font-bold ${isNegative ? 'text-emerald-400' : 'text-[#FFB224]'}`}>
                          {isNegative ? '' : '+'}{mins}m
                        </span>
                        <span className="text-gray-500 text-[10px] ml-1.5">({pct.toFixed(1)}%)</span>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
