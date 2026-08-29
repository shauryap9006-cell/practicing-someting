import React, { useState, useEffect } from 'react';
import { api } from '@/lib/api';
import { SEO } from '@/lib/seo';
import { Shield, AlertTriangle, CheckCircle, RefreshCw } from 'lucide-react';
import { toast } from 'sonner';

interface LCGate {
  id: string;
  gate_no: string;
  location: string;
  type: string;
  status: 'NORMAL' | 'FAULT' | 'STRUCK';
  last_cycle: string;
  fault_duration?: string | null;
}

export function LCMonitorPage() {
  const [gates, setGates] = useState<LCGate[]>([]);

  useEffect(() => {
    api.getLCStatus().then(data => setGates(data as LCGate[]));
  }, []);

  const handleReportFault = (gateId: string) => {
    setGates(prev =>
      prev.map(g => (g.id === gateId ? { ...g, status: 'FAULT', fault_duration: 'Just now' } : g))
    );
    toast.error(`Fault declared on ${gateId}. Caution order suggested to approach trains.`);
  };

  const handleNormalize = (gateId: string) => {
    setGates(prev =>
      prev.map(g => (g.id === gateId ? { ...g, status: 'NORMAL', fault_duration: null } : g))
    );
    toast.success(`Gate ${gateId} normalized. Interlock clear.`);
  };

  return (
    <div className="space-y-4">
      <SEO title="Level Crossing (LC) Monitor · RailTwin-X" noindex />

      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-3 border-b border-[#26282C] gap-3">
        <div>
          <h1 className="text-lg font-semibold text-[#E8E8E6] flex items-center gap-2">
            <Shield className="w-4 h-4 text-[#FFB224]" />
            <span>Level Crossing (LC) Gate Status Monitor</span>
          </h1>
          <p className="font-mono text-xs text-[#9A9DA3]">
            Manned & Interlocked Gate Telemetry across Kanpur – Prayagraj Section
          </p>
        </div>
      </div>

      {/* Gate Cards Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {gates.map(gate => {
          const isFault = gate.status === 'FAULT' || gate.status === 'STRUCK';
          return (
            <div
              key={gate.id}
              className={`p-5 border font-mono text-xs space-y-3 transition-colors ${
                isFault
                  ? 'bg-[#F0533A]/10 border-[#F0533A]'
                  : 'bg-[#15171A] border-[#26282C]'
              }`}
            >
              <div className="flex items-center justify-between">
                <span className="font-bold text-sm text-[#E8E8E6]">{gate.gate_no}</span>
                <span
                  className={`text-[10px] font-bold px-2 py-0.5 border ${
                    gate.status === 'NORMAL'
                      ? 'border-[#3ECF8E] text-[#3ECF8E] bg-[#3ECF8E]/10'
                      : 'border-[#F0533A] text-[#F0533A] bg-[#F0533A]/20'
                  }`}
                >
                  {gate.status}
                </span>
              </div>

              <div>
                <span className="text-[10px] text-[#9A9DA3] block uppercase">Location / Chainage</span>
                <span className="font-semibold text-xs text-[#E8E8E6]">{gate.location}</span>
              </div>

              <div className="grid grid-cols-2 gap-2 bg-[#0E0F11] p-2 border border-[#26282C]">
                <div>
                  <span className="text-[10px] text-[#9A9DA3] block uppercase">Type</span>
                  <span className="text-[#E8E8E6] font-semibold text-[11px]">{gate.type}</span>
                </div>
                <div>
                  <span className="text-[10px] text-[#9A9DA3] block uppercase">Last Gate Cycle</span>
                  <span className="text-[#E8E8E6] font-semibold text-[11px]">{gate.last_cycle}</span>
                </div>
              </div>

              {gate.fault_duration && (
                <div className="text-[#F0533A] font-bold text-[11px] flex items-center gap-1">
                  <AlertTriangle className="w-3.5 h-3.5" />
                  <span>Fault Duration: {gate.fault_duration}</span>
                </div>
              )}

              <div className="pt-2 border-t border-[#26282C] flex items-center justify-between">
                {isFault ? (
                  <button
                    onClick={() => handleNormalize(gate.id)}
                    className="w-full py-1.5 bg-[#3ECF8E] text-[#0E0F11] font-bold hover:bg-[#34B77C] transition-colors"
                  >
                    Acknowledge & Normalize
                  </button>
                ) : (
                  <button
                    onClick={() => handleReportFault(gate.id)}
                    className="text-[#F0533A] hover:underline text-[11px]"
                  >
                    Report Gate Fault &rarr;
                  </button>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
