import React, { useState, useEffect } from 'react';
import { api } from '@/lib/api';
import { SEO } from '@/lib/seo';
import { Radio, CheckCircle, AlertTriangle, ArrowRight, ShieldCheck } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { toast } from 'sonner';

interface HandoffRecord {
  id: string;
  train_no: string;
  boundary: string;
  sched_handoff: string;
  pred_handoff: string;
  state: 'ACCEPTED' | 'PENDING' | 'FLAGGED';
  delta: string;
  speed_kmph: number;
}

export function CorridorHandoffPage() {
  const navigate = useNavigate();
  const [handoffs, setHandoffs] = useState<HandoffRecord[]>([]);

  useEffect(() => {
    api.getCorridorHandoffs().then(data => setHandoffs(data as HandoffRecord[]));
  }, []);

  const handleAcknowledge = async (id: string) => {
    try {
      await api.acknowledgeHandoff(id);
      setHandoffs(prev =>
        prev.map(h => (h.id === id ? { ...h, state: 'ACCEPTED' } : h))
      );
      toast.success(`Handoff ${id} accepted between control divisions.`);
    } catch {
      toast.error('Failed to acknowledge handoff.');
    }
  };

  return (
    <div className="space-y-4 font-mono text-xs">
      <SEO title="Corridor Division Handoff Matrix · RailTwin-X" noindex />

      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-3 border-b border-[#26282C] gap-3">
        <div>
          <h1 className="text-lg font-semibold text-[#E8E8E6] flex items-center gap-2">
            <Radio className="w-4 h-4 text-[#FFB224]" />
            <span>Corridor Multi-Station Handoff Matrix</span>
          </h1>
          <p className="text-[#9A9DA3]">
            Cross-divisional block boundary coordination (Agra &rarr; Prayagraj &rarr; Pt. Deen Dayal Upadhyaya)
          </p>
        </div>

        {/* Handoff Punctuality KPI Strip */}
        <div className="flex items-center gap-3">
          <div className="bg-[#15171A] border border-[#26282C] px-3 py-1.5 text-center">
            <span className="text-[10px] text-[#9A9DA3] block">ON-TIME HANDOFF RATE</span>
            <span className="font-bold text-sm text-[#3ECF8E]">92.4%</span>
          </div>
          <div className="bg-[#15171A] border border-[#26282C] px-3 py-1.5 text-center">
            <span className="text-[10px] text-[#9A9DA3] block">ACTIVE BOUNDARY EXCHANGES</span>
            <span className="font-bold text-sm text-[#FFB224]">4 Active</span>
          </div>
        </div>
      </div>

      {/* Handoff Matrix Table */}
      <div className="bg-[#15171A] border border-[#26282C] p-4">
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="border-b border-[#26282C] bg-[#1B1D21] text-[#9A9DA3] text-[11px] uppercase">
                <th className="py-2.5 px-3">Handoff ID</th>
                <th className="py-2.5 px-3">Train Number</th>
                <th className="py-2.5 px-3">Division Boundary</th>
                <th className="py-2.5 px-3">Scheduled</th>
                <th className="py-2.5 px-3">Predicted (ETA)</th>
                <th className="py-2.5 px-3 text-center">Delta</th>
                <th className="py-2.5 px-3">Line Speed</th>
                <th className="py-2.5 px-3 text-center">Handoff State</th>
                <th className="py-2.5 px-3 text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#26282C]">
              {handoffs.map(h => (
                <tr key={h.id} className="hover:bg-[#1B1D21]/50 text-[#E8E8E6]">
                  <td className="py-3 px-3 font-bold text-[#FFB224]">{h.id}</td>
                  <td className="py-3 px-3 font-bold text-[#E8E8E6]">#{h.train_no}</td>
                  <td className="py-3 px-3">{h.boundary}</td>
                  <td className="py-3 px-3 text-[#9A9DA3]">{h.sched_handoff}</td>
                  <td className="py-3 px-3 font-semibold">{h.pred_handoff}</td>
                  <td className="py-3 px-3 text-center">
                    <span className={`font-bold ${h.delta.startsWith('+') ? 'text-[#FFB224]' : 'text-[#3ECF8E]'}`}>
                      {h.delta}
                    </span>
                  </td>
                  <td className="py-3 px-3 text-[#9A9DA3]">{h.speed_kmph} km/h</td>
                  <td className="py-3 px-3 text-center">
                    <span
                      className={`text-[10px] px-2 py-0.5 border font-bold ${
                        h.state === 'ACCEPTED'
                          ? 'border-[#3ECF8E] text-[#3ECF8E] bg-[#3ECF8E]/10'
                          : h.state === 'PENDING'
                          ? 'border-[#FFB224] text-[#FFB224] bg-[#FFB224]/10'
                          : 'border-[#F0533A] text-[#F0533A] bg-[#F0533A]/10'
                      }`}
                    >
                      {h.state}
                    </span>
                  </td>
                  <td className="py-3 px-3 text-right space-x-2">
                    <button
                      onClick={() => navigate(`/dashboard/trains/${h.train_no}`)}
                      className="text-[#9A9DA3] hover:text-[#E8E8E6] text-[11px]"
                    >
                      Train Detail &rarr;
                    </button>
                    {h.state !== 'ACCEPTED' && (
                      <button
                        onClick={() => handleAcknowledge(h.id)}
                        className="text-[#3ECF8E] hover:underline text-[11px]"
                      >
                        Accept Handoff
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
