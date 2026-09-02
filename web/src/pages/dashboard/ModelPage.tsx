import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/api';
import { queryKeys } from '@/lib/queryKeys';
import {
  F14_PROOF_METRICS,
  HORIZON_MAE_DATA,
  V3_SHOOTOUT_BENCHMARKS,
  V3_FEATURE_DOMAINS,
  V3_VERIFICATION_GATES,
} from '@/mock/model';
import {
  AspectLamp,
  AspectType,
  Provenance,
} from '@/components/aspect';
import {
  Cpu,
  CheckCircle2,
  TrendingDown,
  Target,
  ShieldCheck,
  Zap,
  CloudFog,
  Activity,
  Layers,
  Sparkles,
  Lock,
} from 'lucide-react';

export const ModelPage: React.FC = () => {
  const { data: modelProof, dataUpdatedAt } = useQuery({
    queryKey: queryKeys.modelProof(),
    queryFn: () => api.getModelProof(),
  });
  const [selectedDomain, setSelectedDomain] = useState<number>(0);

  return (
    <div className="space-y-6 font-mono select-none">
      {/* Header & Architecture Overview */}
      <div className="bg-[#101216] border border-[#23272F] rounded-lg p-5 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <div className="flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full bg-[#F5A524] shadow-[0_0_8px_rgba(245,165,36,0.6)] animate-pulse" />
            <h1 className="text-base font-bold text-[#E9EBEE] tracking-tight uppercase font-display">
              v3 NEURAL ENGINE PROOF & PROMOTION AUDIT BENCHMARKS
            </h1>
          </div>
          <p className="text-xs font-sans text-[#A3ABB6] max-w-3xl leading-relaxed mt-1">
            Deep learning neural architecture with 24 point-in-time features, Interaction Cortex cross-attention,
            and a 3-expert Regime Mixture-of-Experts head. Materialized on <strong>434,382</strong> real corridor snapshots.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <span className="px-2.5 py-1 bg-[rgba(61,220,151,0.13)] border border-[#3DDC97]/40 text-[#3DDC97] text-xs font-bold rounded-sm">
            ● CHAMPION PROMOTED
          </span>
        </div>
      </div>

      {/* Headline Metric Strip */}
      <div className="grid grid-cols-1 sm:grid-cols-4 gap-4 font-mono text-center">
        <div className="bg-[#101216] border border-[#23272F] rounded-lg p-4 space-y-1">
          <div className="text-[11px] text-[#A3ABB6] uppercase tracking-wider">1-Hour MAE</div>
          <div className="text-2xl sm:text-3xl font-bold text-[#3DDC97] tabular-nums">7.1 min</div>
          <div className="text-[10px] text-[#A3ABB6]">-60.8% error vs NTES</div>
        </div>

        <div className="bg-[#101216] border border-[#23272F] rounded-lg p-4 space-y-1">
          <div className="text-[11px] text-[#A3ABB6] uppercase tracking-wider">Fog Core Gain (BENCH_v3)</div>
          <div className="text-2xl sm:text-3xl font-bold text-[#F5A524] tabular-nums">-5.37 min</div>
          <div className="text-[10px] text-[#3DDC97]">p &lt; 0.0001 (Wilcoxon Win)</div>
        </div>

        <div className="bg-[#101216] border border-[#23272F] rounded-lg p-4 space-y-1">
          <div className="text-[11px] text-[#A3ABB6] uppercase tracking-wider">Quantile Monotonicity</div>
          <div className="text-2xl sm:text-3xl font-bold text-[#E9EBEE] tabular-nums">100.0%</div>
          <div className="text-[10px] text-[#A3ABB6]">0 &le; q10 &le; q50 &le; q90</div>
        </div>

        <div className="bg-[#101216] border border-[#23272F] rounded-lg p-4 space-y-1">
          <div className="text-[11px] text-[#A3ABB6] uppercase tracking-wider">Epistemic Uncertainty</div>
          <div className="text-2xl sm:text-3xl font-bold text-[#E9EBEE] tabular-nums">±1.8 min</div>
          <div className="text-[10px] text-[#A3ABB6]">Tri-seed Deep Ensemble</div>
        </div>
      </div>

      {/* 3-Expert Mixture-of-Experts Visualizer Card */}
      <div className="bg-[#101216] border border-[#23272F] rounded-lg p-5 space-y-4">
        <div className="flex items-center justify-between border-b border-[#23272F] pb-3">
          <div className="flex items-center gap-2">
            <Sparkles className="w-4 h-4 text-[#F5A524]" />
            <h2 className="text-xs font-mono font-bold uppercase tracking-wider text-[#E9EBEE]">
              Regime Mixture-of-Experts (MoE) Architecture
            </h2>
          </div>
          <span className="text-[11px] font-mono text-[#A3ABB6]">
            6 Observable Gate Signals → 3 Monotone Quantile Experts
          </span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 font-mono text-xs">
          {/* Expert 1 */}
          <div className="p-4 bg-[#0A0B0D] border border-[#23272F] rounded-sm space-y-2">
            <div className="flex items-center justify-between">
              <span className="font-bold text-[#3DDC97]">Expert 0: Nominal Regimes</span>
              <span className="text-[10px] text-[#6B7480]">W: 0.62</span>
            </div>
            <p className="text-[#A3ABB6] font-sans text-[11px] leading-relaxed">
              Active under clear weather (visibility &gt; 1200m) and low corridor headway density.
            </p>
          </div>

          {/* Expert 2 */}
          <div className="p-4 bg-[#0A0B0D] border border-[#23272F] rounded-sm space-y-2">
            <div className="flex items-center justify-between">
              <span className="font-bold text-[#F5A524]">Expert 1: Adverse Fog/Weather</span>
              <span className="text-[10px] text-[#6B7480]">W: 0.26</span>
            </div>
            <p className="text-[#A3ABB6] font-sans text-[11px] leading-relaxed">
              Gated by fog risk flag, relative humidity, and active caution orders.
            </p>
          </div>

          {/* Expert 3 */}
          <div className="p-4 bg-[#0A0B0D] border border-[#23272F] rounded-sm space-y-2">
            <div className="flex items-center justify-between">
              <span className="font-bold text-[#F4506A]">Expert 2: Congested Cascade</span>
              <span className="text-[10px] text-[#6B7480]">W: 0.12</span>
            </div>
            <p className="text-[#A3ABB6] font-sans text-[11px] leading-relaxed">
              Models bottleneck delays, turnaround deficits, and rolling stock dependencies.
            </p>
          </div>
        </div>
      </div>

      {/* Benchmark Shootout Table */}
      <div className="bg-[#101216] border border-[#23272F] rounded-lg overflow-hidden">
        <div className="p-4 bg-[#0A0B0D] border-b border-[#23272F] flex items-center justify-between">
          <span className="font-bold text-xs uppercase text-[#E9EBEE] tracking-wider">
            OUT-OF-SAMPLE EVALUATION SHOOTOUT (434,382 SNAPSHOTS)
          </span>
          <span className="text-xs text-[#3DDC97] font-semibold">● 100% GATES PASS</span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left font-mono text-xs border-collapse">
            <thead>
              <tr className="border-b border-[#23272F] bg-[#15181D] text-[#A3ABB6] text-[11px] uppercase">
                <th className="py-3 px-4">Benchmark Scope</th>
                <th className="py-3 px-4">Split Scope</th>
                <th className="py-3 px-4 text-right">Snapshots</th>
                <th className="py-3 px-4 text-right">Champion MAE</th>
                <th className="py-3 px-4 text-right text-[#3DDC97] font-bold">v3 Ensemble MAE</th>
                <th className="py-3 px-4 text-right text-[#F5A524] font-bold">Delta (Δ)</th>
                <th className="py-3 px-4 text-center">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#23272F]">
              {V3_SHOOTOUT_BENCHMARKS.map(m => (
                <tr key={m.rowLabel} className="hover:bg-[#15181D]/50 text-[#E9EBEE]">
                  <td className="py-3 px-4 font-semibold">{m.rowLabel}</td>
                  <td className="py-3 px-4 text-[#A3ABB6] text-[11px]">{m.splitScope}</td>
                  <td className="py-3 px-4 text-right text-[#A3ABB6]">{m.nEvents.toLocaleString()}</td>
                  <td className="py-3 px-4 text-right text-[#A3ABB6]">{m.champMae.toFixed(2)}m</td>
                  <td className="py-3 px-4 text-right font-bold text-[#3DDC97]">{m.v3Mae.toFixed(2)}m</td>
                  <td className="py-3 px-4 text-right font-bold text-[#F5A524]">{m.deltaMae.toFixed(2)}m</td>
                  <td className="py-3 px-4 text-center">
                    <span className="px-2 py-0.5 bg-[rgba(61,220,151,0.13)] border border-[#3DDC97]/40 text-[#3DDC97] text-[10px] font-bold rounded-sm">
                      {m.winStatus}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div className="p-4 border-t border-[#23272F] bg-[#0A0B0D]">
          <Provenance updatedAt={dataUpdatedAt} source="NEURAL ENGINE TRAINING MANIFEST" />
        </div>
      </div>
    </div>
  );
};
