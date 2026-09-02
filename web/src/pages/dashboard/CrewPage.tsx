import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/lib/api';
import { queryKeys } from '@/lib/queryKeys';
import { CrewMember } from '@/mock/types';
import {
  AspectLamp,
  AspectType,
  Provenance,
  EmptyState,
} from '@/components/aspect';
import { Users, Phone, AlertTriangle, ShieldCheck, CheckCircle2, UserCheck, Sparkles } from 'lucide-react';
import { toast } from 'sonner';

export const CrewPage: React.FC = () => {
  const queryClient = useQueryClient();
  const { data: crew = [], dataUpdatedAt } = useQuery({
    queryKey: queryKeys.crew(),
    queryFn: () => api.getCrew(),
    refetchInterval: 5000,
  });
  const [requestingId, setRequestingId] = useState<string | null>(null);

  const reliefMutation = useMutation({
    mutationFn: (id: string) => api.requestCrewRelief(id),
    onSuccess: (_, id) => {
      queryClient.invalidateQueries({ queryKey: queryKeys.crew() });
      const member = crew.find(c => c.id === id);
      toast.success(`Relief Crew Dispatched for ${member?.name || 'Crew Member'}`, {
        description: `Standby relief crew assigned at ${member?.reliefStation || 'CNB'} for train ${member?.trainNo || ''}.`,
      });
    },
    onError: (err: any) => {
      toast.error('Relief Request Failed', { description: err?.message || 'Error dispatching crew' });
    },
  });

  const handleRequestRelief = async (member: CrewMember) => {
    setRequestingId(member.id);
    try {
      await reliefMutation.mutateAsync(member.id);
    } finally {
      setRequestingId(null);
    }
  };

  const getAspect = (status: string): AspectType => {
    if (status === 'critical') return 'restrict';
    if (status === 'advisory' || status === 'warn') return 'caution';
    return 'clear';
  };

  const criticalCount = crew.filter(c => c.status === 'critical').length;
  const advisoryCount = crew.filter(c => c.status === 'advisory').length;

  return (
    <div className="space-y-6 font-mono select-none">
      {/* Header & Stats Strip */}
      <div className="bg-[#101216] border border-[#23272F] rounded-lg p-5 space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-4 border-b border-[#23272F]">
          <div>
            <div className="flex items-center gap-2">
              <span className="w-2.5 h-2.5 rounded-full bg-[#F5A524] shadow-[0_0_8px_rgba(245,165,36,0.6)] animate-pulse" />
              <h1 className="text-lg font-bold text-[#E9EBEE] uppercase tracking-wider font-display">
                CREW DUTY ROSTER & STATUTORY 10H HOER WATCH
              </h1>
            </div>
            <p className="text-xs font-sans text-[#A3ABB6] mt-1">
              Statutory 10-hour duty limit early warning system. Prevents mid-section crew expiry by calculating section runtimes.
            </p>
          </div>

          <div className="flex items-center gap-2">
            <span className="px-2.5 py-1 bg-[rgba(244,80,106,0.13)] border border-[#F4506A]/40 text-[#F4506A] text-xs font-bold rounded-sm">
              {criticalCount} Critical (&lt;2h)
            </span>
            <span className="px-2.5 py-1 bg-[rgba(245,165,36,0.13)] border border-[#F5A524]/40 text-[#F5A524] text-xs font-bold rounded-sm">
              {advisoryCount} Advisory (2–4h)
            </span>
          </div>
        </div>
      </div>

      {/* Roster Table */}
      <div className="bg-[#101216] border border-[#23272F] rounded-lg overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs font-mono border-collapse">
            <thead>
              <tr className="bg-[#0A0B0D] border-b border-[#23272F] text-[#A3ABB6] text-[11px] uppercase">
                <th className="py-3.5 px-4">Crew Member / ID</th>
                <th className="py-3.5 px-4">Assigned Train</th>
                <th className="py-3.5 px-4">Sign-On</th>
                <th className="py-3.5 px-4">Elapsed Duty</th>
                <th className="py-3.5 px-4">Duty Progress</th>
                <th className="py-3.5 px-4">Hours Left</th>
                <th className="py-3.5 px-4">Relief Station</th>
                <th className="py-3.5 px-4 text-right">Relief Dispatch</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#23272F]">
              {crew.map(member => {
                const dutyPercent = Math.min(100, (member.dutyHoursSoFar / member.maxAllowedHours) * 100);
                const aspect = getAspect(member.status);

                return (
                  <tr key={member.id} className="hover:bg-[#15181D] transition-colors">
                    {/* Name & ID */}
                    <td className="py-3 px-4">
                      <div className="font-bold text-[#E9EBEE] font-sans">{member.name}</div>
                      <div className="text-[10px] text-[#6B7480]">{member.id} · {member.designation}</div>
                    </td>

                    {/* Assigned Train */}
                    <td className="py-3 px-4 font-bold text-[#F5A524]">
                      {member.trainNo}
                    </td>

                    {/* Sign-On */}
                    <td className="py-3 px-4 text-[#A3ABB6]">
                      {member.signOnTime} IST
                    </td>

                    {/* Elapsed Duty */}
                    <td className="py-3 px-4 font-bold text-[#E9EBEE] tabular-nums">
                      {member.dutyHoursSoFar.toFixed(1)}h / {member.maxAllowedHours}h
                    </td>

                    {/* Progress Bar */}
                    <td className="py-3 px-4 min-w-[140px]">
                      <div className="w-full bg-[#0A0B0D] h-2 rounded-xs border border-[#23272F] overflow-hidden">
                        <div
                          className={`h-full rounded-xs transition-all ${
                            aspect === 'restrict'
                              ? 'bg-[#F4506A]'
                              : aspect === 'caution'
                              ? 'bg-[#F5A524]'
                              : 'bg-[#3DDC97]'
                          }`}
                          style={{ width: `${dutyPercent}%` }}
                        />
                      </div>
                    </td>

                    {/* Hours Left + Aspect Lamp */}
                    <td className="py-3 px-4">
                      <AspectLamp
                        aspect={aspect}
                        label={`${(member.maxAllowedHours - member.dutyHoursSoFar).toFixed(1)}h LEFT`}
                        size="xs"
                      />
                    </td>

                    {/* Relief Station */}
                    <td className="py-3 px-4 text-[#A3ABB6]">
                      {member.reliefStation || 'CNB'}
                    </td>

                    {/* Action */}
                    <td className="py-3 px-4 text-right">
                      {member.status !== 'ok' ? (
                        <button
                          type="button"
                          disabled={requestingId === member.id}
                          onClick={() => handleRequestRelief(member)}
                          className="px-3 py-1 bg-[#F5A524] hover:bg-[#F5A524]/90 text-[#0A0B0D] font-bold text-xs rounded-sm transition-colors shadow-sm"
                        >
                          {requestingId === member.id ? 'Dispatching...' : 'Plan Relief'}
                        </button>
                      ) : (
                        <span className="text-[#3DDC97] text-[11px] font-semibold flex items-center justify-end gap-1">
                          <CheckCircle2 className="w-3.5 h-3.5" />
                          <span>Nominal</span>
                        </span>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>

        <div className="p-4 border-t border-[#23272F] bg-[#0A0B0D]">
          <Provenance updatedAt={dataUpdatedAt} source="RAILWAY HOER CREW ROSTER SYSTEM" />
        </div>
      </div>
    </div>
  );
};
