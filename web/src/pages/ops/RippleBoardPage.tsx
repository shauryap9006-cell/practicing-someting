import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import {
  Layers,
  ArrowLeft,
  ShieldAlert,
  Clock,
  TrendingUp,
  AlertOctagon,
  CheckCircle2,
  Users,
  Repeat,
  RefreshCw,
  ExternalLink,
} from 'lucide-react';
import { api, CascadeRippleData } from '@/lib/api';

export function RippleBoardPage() {
  const [stationCode, setStationCode] = useState('CNB');
  const [data, setData] = useState<CascadeRippleData | null>(null);
  const [loading, setLoading] = useState(true);

  const loadData = async (stn = stationCode) => {
    try {
      setLoading(true);
      const res = await api.getCascadeRipple(stn);
      setData(res);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData(stationCode);
  }, [stationCode]);

  const summary = data?.summary;
  const rakeLinks = data?.rake_turnarounds || [];
  const holdAdvisories = data?.top_hold_advisories || [];

  return (
    <div className="min-h-screen bg-[#07090D] text-[#E5E7EB] font-sans antialiased selection:bg-[#FFB224] selection:text-black">
      {/* Header with Jurisdictional Badge */}
      <header className="border-b border-white/10 bg-[#0C0F17]/90 backdrop-blur-md sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 py-3 flex flex-wrap items-center justify-between gap-4">
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
                <span className="font-mono text-xs font-bold uppercase tracking-widest text-[#A78BFA]">
                  D4 DIFFERENTIATION
                </span>
                <span className="text-[10px] px-2 py-0.5 rounded-full bg-purple-500/20 text-purple-300 font-mono font-semibold border border-purple-500/30">
                  NETWORK RIPPLE & CONNECTION CUSTODY
                </span>
              </div>
              <h1 className="text-base font-bold text-white tracking-tight">
                Section Controller Decision Support System (DSS)
              </h1>
            </div>
          </div>

          {/* Section Controller Advisory Framing */}
          <div className="flex items-center gap-2 bg-amber-500/10 border border-amber-500/30 px-3 py-1.5 rounded-lg text-xs font-mono">
            <ShieldAlert className="w-4 h-4 text-[#FFB224]" />
            <span className="text-[#FFB224] font-bold">ADVISORY ONLY:</span>
            <span className="text-gray-300 hidden md:inline">Authority remains strictly with Section Controller / DOM</span>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 py-6 space-y-6">
        {/* Metric Summary Scoreboard */}
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-4">
          <div className="bg-[#10141F] border border-white/10 rounded-xl p-4 font-mono">
            <span className="text-gray-400 text-xs uppercase tracking-wider block mb-1">Rake Links Monitored</span>
            <div className="text-2xl font-black text-white">{summary?.total_rake_links_monitored || 14}</div>
            <span className="text-[11px] text-gray-500 mt-1 block">Corridor turnaround pairs</span>
          </div>

          <div className="bg-[#10141F] border border-red-500/30 rounded-xl p-4 font-mono bg-gradient-to-br from-red-500/5 to-transparent">
            <span className="text-red-400 text-xs uppercase tracking-wider block mb-1 font-bold">At-Risk Turnarounds</span>
            <div className="text-2xl font-black text-red-400">{summary?.at_risk_turnarounds || 0}</div>
            <span className="text-[11px] text-red-400/80 mt-1 block">Buffer deficit below 90m threshold</span>
          </div>

          <div className="bg-[#10141F] border border-white/10 rounded-xl p-4 font-mono">
            <span className="text-gray-400 text-xs uppercase tracking-wider block mb-1">Hold Advisories Active</span>
            <div className="text-2xl font-black text-[#A78BFA]">{summary?.active_hold_advisories || 0}</div>
            <span className="text-[11px] text-gray-500 mt-1 block">Interchange junctions assessed</span>
          </div>

          <div className="bg-[#10141F] border border-emerald-500/30 rounded-xl p-4 font-mono bg-gradient-to-br from-emerald-500/5 to-transparent">
            <span className="text-emerald-400 text-xs uppercase tracking-wider block mb-1 font-bold">Net Pax-Hours Saved</span>
            <div className="text-2xl font-black text-emerald-400">+{summary?.total_net_pax_hours_saved || 0} <span className="text-xs font-normal">hrs</span></div>
            <span className="text-[11px] text-emerald-400/80 mt-1 block">Tradeoff benefit across passengers</span>
          </div>
        </div>

        {/* Section 1: Connection Custody Advisories */}
        <div className="bg-[#10141F] border border-white/10 rounded-xl p-5 shadow-xl">
          <div className="flex flex-wrap items-center justify-between gap-4 mb-4 pb-3 border-b border-white/10">
            <div>
              <div className="flex items-center gap-2">
                <Users className="w-4 h-4 text-[#A78BFA]" />
                <h2 className="text-sm font-bold text-white uppercase tracking-wider font-mono">
                  Connection Custody Trade-off Advisories (Kanpur Central Junction)
                </h2>
              </div>
              <p className="text-xs text-gray-400 mt-0.5">
                Quantile-driven hold decisions: holding a connecting train by 6–15 min saves 35+ passengers from a 5-hour stranded headway, yielding massive positive passenger-hours.
              </p>
            </div>

            <div className="text-xs font-mono text-gray-400">
              Station: <strong className="text-white">CNB (Kanpur Central)</strong>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {holdAdvisories.map((c: any, idx: number) => {
              const adv = c.hold_advisory;
              const f = c.feeder_train;
              const conn = c.connecting_train;

              return (
                <div
                  key={idx}
                  className="rounded-xl border border-purple-500/30 bg-gradient-to-b from-[#181324] to-[#0E0C17] p-4 font-mono relative overflow-hidden shadow-lg shadow-purple-500/5"
                >
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-purple-500/20 text-purple-300 border border-purple-500/40">
                      {adv?.action || 'HOLD RECOMMENDATION'}
                    </span>
                    <span className="text-xs font-bold text-emerald-400">
                      +{adv?.net_passenger_hours_saved} pax-hrs saved
                    </span>
                  </div>

                  <div className="space-y-2 text-xs my-3 bg-black/40 rounded-lg p-2.5 border border-white/5">
                    <div>
                      <span className="text-gray-500 text-[10px] block">Incoming Feeder Train:</span>
                      <span className="text-white font-bold">#{f.train_no}</span>{' '}
                      <span className="text-gray-400 text-[11px] truncate block">{f.name}</span>
                      <span className="text-[10px] text-amber-400">Arrival window: {f.p10_arr} – {f.p90_arr}</span>
                    </div>

                    <div className="pt-2 border-t border-white/5">
                      <span className="text-gray-500 text-[10px] block">Connecting Outgoing Train:</span>
                      <span className="text-white font-bold">#{conn.train_no}</span>{' '}
                      <span className="text-gray-400 text-[11px] truncate block">{conn.name}</span>
                      <span className="text-[10px] text-gray-400">Sched Dep: {conn.sched_dep} → Revised: {adv?.revised_departure}</span>
                    </div>
                  </div>

                  <div className="text-[11px] text-gray-300 font-sans leading-relaxed">
                    {adv?.reason}
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Section 2: Downstream Rake Links & Turnaround Deficit */}
        <div className="bg-[#10141F] border border-white/10 rounded-xl overflow-hidden shadow-xl">
          <div className="px-5 py-4 border-b border-white/10 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Repeat className="w-4 h-4 text-[#FFB224]" />
              <h2 className="text-sm font-bold text-white uppercase tracking-wider font-mono">
                Rake Turnaround Links & Cascade Deficit Radar
              </h2>
            </div>
            <span className="text-xs font-mono text-gray-400">
              Minimum buffer threshold: <strong className="text-white">90 mins</strong>
            </span>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-xs font-mono text-left">
              <thead className="bg-[#0A0D14] text-gray-400 border-b border-white/10">
                <tr>
                  <th className="py-3 px-4">Incoming Train</th>
                  <th className="py-3 px-4">Outgoing Train</th>
                  <th className="py-3 px-4">Turnaround Station</th>
                  <th className="py-3 px-4">Scheduled Buffer</th>
                  <th className="py-3 px-4">Incoming Delay</th>
                  <th className="py-3 px-4">Remaining Buffer</th>
                  <th className="py-3 px-4">Projected Outgoing Delay</th>
                  <th className="py-3 px-4">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/5">
                {rakeLinks.map((r: any, idx: number) => {
                  const isCrit = r.status === 'CRITICAL_DEFICIT';
                  const isRisk = r.status === 'AT_RISK';

                  return (
                    <tr
                      key={idx}
                      className={`hover:bg-white/5 transition-colors ${
                        isCrit ? 'bg-red-500/5' : isRisk ? 'bg-amber-500/5' : ''
                      }`}
                    >
                      <td className="py-3 px-4">
                        <span className="font-bold text-white">#{r.incoming_train}</span>
                        <div className="text-[10px] text-gray-400 truncate max-w-[140px]">{r.incoming_name}</div>
                      </td>
                      <td className="py-3 px-4">
                        <span className="font-bold text-white">#{r.outgoing_train}</span>
                        <div className="text-[10px] text-gray-400 truncate max-w-[140px]">{r.outgoing_name}</div>
                      </td>
                      <td className="py-3 px-4 text-[#FFB224] font-bold">{r.turnaround_station}</td>
                      <td className="py-3 px-4 text-gray-300">{r.scheduled_turnaround_min}m</td>
                      <td className="py-3 px-4 text-amber-400">+{r.incoming_delay_min}m</td>
                      <td className="py-3 px-4 font-bold text-white">{r.remaining_buffer_min}m</td>
                      <td className="py-3 px-4 font-bold text-red-400">
                        {r.projected_outgoing_delay_min > 0 ? `+${r.projected_outgoing_delay_min}m` : '0m'}
                      </td>
                      <td className="py-3 px-4">
                        <span
                          className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase border ${
                            isCrit
                              ? 'bg-red-500/20 text-red-400 border-red-500/30'
                              : isRisk
                              ? 'bg-amber-500/20 text-amber-400 border-amber-500/30'
                              : 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20'
                          }`}
                        >
                          {r.status}
                        </span>
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
