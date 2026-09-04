import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import {
  GitFork,
  Zap,
  ArrowLeft,
  ShieldCheck,
  TrendingDown,
  TrendingUp,
  Sliders,
  RefreshCw,
  Sparkles,
  Lock,
  Layers,
  Info,
} from 'lucide-react';
import { api, DemoComparatorData } from '@/lib/api';

export function ComparatorPage() {
  const [selectedTrain, setSelectedTrain] = useState('12301');
  const [data, setData] = useState<DemoComparatorData | null>(null);
  const [loading, setLoading] = useState(true);
  const [injecting, setInjecting] = useState(false);
  const [activeTab, setActiveTab] = useState<'comparison' | 'proof'>('comparison');

  const loadData = async (trainNo = selectedTrain) => {
    try {
      setLoading(true);
      const res = await api.getDemoComparator(trainNo);
      setData(res);
    } catch (e) {
      console.error(e);
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
      await loadData();
    } catch (e) {
      console.error(e);
    } finally {
      setInjecting(false);
    }
  };

  const handleReset = async () => {
    try {
      setInjecting(true);
      await api.resetShockEvents();
      await loadData();
    } catch (e) {
      console.error(e);
    } finally {
      setInjecting(false);
    }
  };

  const stations = data?.stations || [];
  const errors = data?.cumulative_errors;
  const shocks = data?.active_shocks || [];

  return (
    <div className="min-h-screen bg-[#07090D] text-[#E5E7EB] font-sans antialiased selection:bg-[#FFB224] selection:text-black">
      {/* Top Header */}
      <header className="border-b border-white/10 bg-[#0C0F17]/90 backdrop-blur-md sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 py-3 flex items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <Link
              to="/"
              className="p-1.5 rounded-lg bg-white/5 hover:bg-white/10 text-gray-300 transition-colors"
              title="Back to Foresight Console"
            >
              <ArrowLeft className="w-4 h-4" />
            </Link>
            <div>
              <div className="flex items-center gap-2">
                <span className="font-mono text-xs font-bold uppercase tracking-widest text-[#FFB224]">
                  SIGNATURE DEMO
                </span>
                <span className="text-[10px] px-2 py-0.5 rounded-full bg-blue-500/20 text-blue-400 font-mono font-semibold border border-blue-500/30">
                  LIVE COMPARATOR
                </span>
              </div>
              <h1 className="text-base font-bold text-white tracking-tight">
                Static Baselines (B1/B2) vs RailTwin-X Calibrated Quantile Cone
              </h1>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <div className="text-xs font-mono text-gray-400">
              Train: <strong className="text-white font-bold">#{data?.train_no || selectedTrain}</strong> ·{' '}
              <span className="text-[#FFB224] font-bold">+{data?.active_station.current_delay_min || 24}m</span>
            </div>
            <button
              onClick={() => loadData()}
              disabled={loading}
              className="p-1.5 rounded-md hover:bg-white/10 text-gray-400 hover:text-white transition-colors"
            >
              <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin text-[#FFB224]' : ''}`} />
            </button>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 py-6 space-y-6">
        {/* Shock Injection Control Center */}
        <div className="bg-[#10141F] border border-white/10 rounded-xl p-4 shadow-xl">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div className="flex items-center gap-2.5">
              <div className="w-7 h-7 rounded-md bg-[#FFB224]/10 text-[#FFB224] flex items-center justify-center">
                <Sliders className="w-4 h-4" />
              </div>
              <div>
                <h2 className="text-xs font-bold text-white font-mono uppercase tracking-wider">
                  Operational Shock Injection Lab
                </h2>
                <p className="text-[11px] text-gray-400">
                  Inject unexpected corridor shocks to observe instant ML cone re-calibration while static baselines remain paralyzed.
                </p>
              </div>
            </div>

            <div className="flex flex-wrap items-center gap-2">
              <button
                disabled={injecting}
                onClick={() => handleInject('SIGNAL_HOLD', 'CNB', 25, 'Kanpur Central outer home signal hold')}
                className="px-3 py-1.5 text-xs font-mono rounded-lg bg-red-500/10 hover:bg-red-500/20 text-red-400 border border-red-500/30 transition-all font-bold"
              >
                ⚡ +25m Signal Hold
              </button>
              <button
                disabled={injecting}
                onClick={() => handleInject('TSR_ACTIVE', 'ETW', 20, 'TSR 40 km/h speed restriction')}
                className="px-3 py-1.5 text-xs font-mono rounded-lg bg-amber-500/10 hover:bg-amber-500/20 text-amber-400 border border-amber-500/30 transition-all font-bold"
              >
                🚧 +20m TSR 40 km/h
              </button>
              <button
                disabled={injecting}
                onClick={() => handleInject('RAKE_DELAY', 'NDLS', 35, 'Late incoming rake #12034 turnaround deficit')}
                className="px-3 py-1.5 text-xs font-mono rounded-lg bg-purple-500/10 hover:bg-purple-500/20 text-purple-400 border border-purple-500/30 transition-all font-bold"
              >
                🔄 +35m Rake Deficit
              </button>
              <button
                disabled={injecting}
                onClick={() => handleInject('WEATHER_FOG', 'CNB', 15, 'Gangetic winter fog vis < 200m')}
                className="px-3 py-1.5 text-xs font-mono rounded-lg bg-blue-500/10 hover:bg-blue-500/20 text-blue-400 border border-blue-500/30 transition-all font-bold"
              >
                🌫️ +15m Fog Dawn
              </button>
              <button
                disabled={injecting}
                onClick={handleReset}
                className="px-3 py-1.5 text-xs font-mono rounded-lg bg-white/10 hover:bg-white/20 text-gray-300 border border-white/20 transition-all font-bold flex items-center gap-1.5"
              >
                <RefreshCw className="w-3.5 h-3.5" />
                Reset Shocks
              </button>
            </div>
          </div>

          {shocks.length > 0 && (
            <div className="mt-3 pt-3 border-t border-white/5 flex flex-wrap items-center gap-2 text-xs font-mono">
              <span className="text-[#FFB224] font-bold">Active Shocks ({shocks.length}):</span>
              {shocks.map((s: any, idx: number) => (
                <span
                  key={idx}
                  className="px-2 py-0.5 rounded bg-red-500/20 text-red-300 border border-red-500/30 text-[11px]"
                >
                  {s.event_type} at {s.station} (+{s.severity_min}m)
                </span>
              ))}
            </div>
          )}
        </div>

        {/* Real-Time Scoreboard Banner */}
        {errors && (
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-4">
            <div className="bg-[#10141F] border border-white/10 rounded-xl p-4 font-mono">
              <span className="text-gray-400 text-xs uppercase tracking-wider block mb-1">Baseline 1 (Frozen)</span>
              <div className="text-2xl font-black text-gray-300">{errors.b1_frozen_mae} <span className="text-xs font-normal text-gray-400">min MAE</span></div>
              <span className="text-[11px] text-gray-500 mt-1 block">Assumes constant delay (stuck in past)</span>
            </div>

            <div className="bg-[#10141F] border border-white/10 rounded-xl p-4 font-mono">
              <span className="text-gray-400 text-xs uppercase tracking-wider block mb-1">Baseline 2 (Official NTES)</span>
              <div className="text-2xl font-black text-red-400">{errors.b2_official_mae} <span className="text-xs font-normal text-gray-400">min MAE</span></div>
              <span className="text-[11px] text-red-400/80 mt-1 block">Unbuffered run-rate (under-predicts)</span>
            </div>

            <div className="bg-[#10141F] border border-emerald-500/30 rounded-xl p-4 font-mono bg-gradient-to-br from-emerald-500/5 to-transparent">
              <span className="text-emerald-400 text-xs uppercase tracking-wider block mb-1 font-bold">RailTwin-X p50 ML</span>
              <div className="text-2xl font-black text-emerald-400">{errors.railtwin_p50_mae} <span className="text-xs font-normal text-gray-400">min MAE</span></div>
              <span className="text-[11px] text-emerald-400/80 mt-1 block">Calibrated corridor ML cone</span>
            </div>

            <div className="bg-[#10141F] border border-[#FFB224]/30 rounded-xl p-4 font-mono bg-gradient-to-br from-[#FFB224]/5 to-transparent">
              <span className="text-[#FFB224] text-xs uppercase tracking-wider block mb-1 font-bold">Accuracy Advantage</span>
              <div className="text-2xl font-black text-[#FFB224]">+{errors.railtwin_vs_official_gain_pct}%</div>
              <span className="text-[11px] text-[#FFB224]/80 mt-1 block">Superiority vs official NTES run-rate</span>
            </div>
          </div>
        )}

        {/* Side-by-Side Station Table Comparison */}
        <div className="bg-[#10141F] border border-white/10 rounded-xl overflow-hidden shadow-2xl">
          <div className="px-5 py-4 border-b border-white/10 flex flex-wrap items-center justify-between gap-4">
            <div>
              <h2 className="text-sm font-bold text-white font-mono uppercase tracking-wider">
                Station-by-Station Journey Comparison Table
              </h2>
              <p className="text-xs text-gray-400 mt-0.5">
                Exposing the exact gap between frozen baselines and dynamic corridor foresight.
              </p>
            </div>

            <div className="flex items-center gap-2 text-xs font-mono">
              <span className="flex items-center gap-1 text-gray-400">
                <span className="w-2 h-2 rounded-full bg-gray-500" /> B1 Frozen
              </span>
              <span className="flex items-center gap-1 text-red-400">
                <span className="w-2 h-2 rounded-full bg-red-400" /> B2 Official
              </span>
              <span className="flex items-center gap-1 text-emerald-400 font-bold">
                <span className="w-2 h-2 rounded-full bg-emerald-400" /> RailTwin-X Cone
              </span>
            </div>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-xs font-mono text-left">
              <thead className="bg-[#0A0D14] text-gray-400 border-b border-white/10">
                <tr>
                  <th className="py-3 px-4">Seq</th>
                  <th className="py-3 px-4">Station</th>
                  <th className="py-3 px-4">Distance</th>
                  <th className="py-3 px-4">Schedule</th>
                  <th className="py-3 px-4">Status / Horizon</th>
                  <th className="py-3 px-4 text-gray-300">B1 Frozen Line</th>
                  <th className="py-3 px-4 text-red-400">B2 Official NTES</th>
                  <th className="py-3 px-4 text-emerald-400 font-bold">RailTwin-X p50</th>
                  <th className="py-3 px-4 text-purple-400">Cone [p10–p90]</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/5">
                {stations.map((s) => {
                  const isCurrent = s.is_current;
                  const isPassed = s.is_passed;

                  return (
                    <tr
                      key={s.station_code}
                      className={`hover:bg-white/5 transition-colors ${
                        isCurrent ? 'bg-[#1C2333]/70 font-bold' : isPassed ? 'text-gray-400' : 'text-white'
                      }`}
                    >
                      <td className="py-3 px-4 text-gray-500">{s.seq}</td>
                      <td className="py-3 px-4">
                        <div className="font-bold text-white">{s.station_code}</div>
                        <div className="text-[10px] text-gray-400 truncate max-w-[120px]">{s.station_name}</div>
                      </td>
                      <td className="py-3 px-4 text-gray-400">{s.distance_km} km</td>
                      <td className="py-3 px-4 text-gray-400">{s.sched_arr || s.sched_dep || '--:--'}</td>
                      <td className="py-3 px-4">
                        {isCurrent ? (
                          <span className="px-2 py-0.5 rounded bg-[#FFB224] text-black font-bold uppercase text-[10px]">
                            CURRENT
                          </span>
                        ) : isPassed ? (
                          <span className="px-2 py-0.5 rounded bg-white/10 text-gray-400 uppercase text-[10px]">
                            PASSED
                          </span>
                        ) : (
                          <span className="px-2 py-0.5 rounded bg-blue-500/20 text-blue-400 border border-blue-500/30 uppercase text-[10px]">
                            {s.horizon_tag} HORIZON
                          </span>
                        )}
                      </td>
                      <td className="py-3 px-4 text-gray-300">
                        {isPassed ? `+${s.actual_delay_min || 0}m` : `+${s.b1_frozen_delay_min}m`}
                      </td>
                      <td className="py-3 px-4 text-red-400">
                        {isPassed ? `+${s.actual_delay_min || 0}m` : `+${s.b2_official_delay_min}m`}
                      </td>
                      <td className="py-3 px-4 text-emerald-400 font-bold text-sm">
                        {isPassed ? `+${s.actual_delay_min || 0}m (Act)` : `+${s.p50_delay_min}m`}
                      </td>
                      <td className="py-3 px-4 text-purple-300">
                        {isPassed ? (
                          <span className="text-gray-500">Graded</span>
                        ) : (
                          <span>
                            [{s.p10_delay_min}m – {s.p90_delay_min}m] <span className="text-gray-500 text-[10px]">(±{Math.round(s.cone_spread_min / 2)}m)</span>
                          </span>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      </main>
    </div>
  );
}
