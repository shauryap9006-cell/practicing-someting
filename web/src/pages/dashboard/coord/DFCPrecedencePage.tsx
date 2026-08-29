import React, { useState, useEffect } from 'react';
import { api } from '@/lib/api';
import { SEO } from '@/lib/seo';
import { Train, ArrowUpDown, CheckCircle, ShieldAlert, Clock } from 'lucide-react';
import { toast } from 'sonner';

interface DFCConflictItem {
  id: string;
  crossing_point: string;
  freight_train: string;
  passenger_train: string;
  proposed_action: string;
  delay_impact_min: number;
  status: string;
}

export function DFCPrecedencePage() {
  const [items, setItems] = useState<DFCConflictItem[]>([]);

  useEffect(() => {
    api.getDFCPrecedence().then(data => setItems(data as DFCConflictItem[]));
  }, []);

  const handleApplyPrecedence = (id: string) => {
    setItems(prev =>
      prev.map(item => (item.id === id ? { ...item, status: 'EXECUTED_ADVISORY' } : item))
    );
    toast.success(`Precedence decision for ${id} broadcast to Section Controller.`);
  };

  return (
    <div className="space-y-4 font-mono text-xs">
      <SEO title="DFC Freight Precedence Controller · RailTwin-X" noindex />

      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-3 border-b border-[#26282C] gap-3">
        <div>
          <h1 className="text-lg font-semibold text-[#E8E8E6] flex items-center gap-2">
            <Train className="w-4 h-4 text-[#FFB224]" />
            <span>Dedicated Freight Corridor (DFC) Precedence Controller</span>
          </h1>
          <p className="text-[#9A9DA3]">
            Dynamic loop regulation resolving freight vs premium passenger rake conflicts at diamond crossings
          </p>
        </div>
      </div>

      {/* Conflicts List */}
      <div className="space-y-4">
        {items.map(item => (
          <div key={item.id} className="bg-[#15171A] border border-[#26282C] p-5 space-y-4">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-3 border-b border-[#26282C] gap-2">
              <div className="flex items-center gap-2">
                <span className="font-bold text-[#FFB224] text-sm">{item.id}</span>
                <span className="text-[#E8E8E6] font-semibold">{item.crossing_point}</span>
              </div>

              <span
                className={`text-[10px] px-2 py-0.5 border font-bold ${
                  item.status === 'ACTIVE'
                    ? 'border-[#FFB224] text-[#FFB224] bg-[#FFB224]/10'
                    : 'border-[#3ECF8E] text-[#3ECF8E] bg-[#3ECF8E]/10'
                }`}
              >
                {item.status}
              </span>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 bg-[#0E0F11] p-4 border border-[#26282C]">
              <div>
                <span className="text-[10px] text-[#9A9DA3] block uppercase">Approaching Freight Rake</span>
                <span className="font-bold text-xs text-[#E8E8E6] mt-0.5 block">{item.freight_train}</span>
                <span className="text-[10px] text-[#6B6E74]">Eastern DFC Siding Approach</span>
              </div>

              <div>
                <span className="text-[10px] text-[#9A9DA3] block uppercase">Trunk Passenger Train</span>
                <span className="font-bold text-xs text-[#FFB224] mt-0.5 block">{item.passenger_train}</span>
                <span className="text-[10px] text-[#6B6E74]">UP Main Line (130 km/h)</span>
              </div>

              <div>
                <span className="text-[10px] text-[#9A9DA3] block uppercase">Proposed Resolution</span>
                <span className="font-bold text-xs text-[#3ECF8E] mt-0.5 block">{item.proposed_action}</span>
                <span className="text-[10px] text-[#3ECF8E]">Network Delay Impact: {item.delay_impact_min} min</span>
              </div>
            </div>

            <div className="flex items-center justify-between pt-1">
              <span className="text-[11px] text-[#9A9DA3]">Advisory Mode · Human Controller Sign-Off Required</span>
              {item.status === 'ACTIVE' && (
                <button
                  onClick={() => handleApplyPrecedence(item.id)}
                  className="px-4 py-2 bg-[#FFB224] hover:bg-[#E59F1C] text-[#0E0F11] font-bold text-xs transition-colors"
                >
                  Authorize Precedence Order &rarr;
                </button>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
