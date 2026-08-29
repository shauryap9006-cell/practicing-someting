import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/lib/api';
import { queryKeys } from '@/lib/queryKeys';
import { CrewMember } from '@/mock/types';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { DataFreshnessBadge } from '@/components/common/DataFreshnessBadge';
import { Users, Phone, AlertTriangle, ShieldCheck, CheckCircle2, UserCheck } from 'lucide-react';
import { toast } from 'sonner';

export const CrewPage: React.FC = () => {
  const queryClient = useQueryClient();
  const { data: crew = [], dataUpdatedAt } = useQuery({
    queryKey: queryKeys.crew(),
    queryFn: () => api.getCrew(),
  });
  const [requestingId, setRequestingId] = useState<string | null>(null);

  const reliefMutation = useMutation({
    mutationFn: (id: string) => api.requestCrewRelief(id),
    onSuccess: (_, id) => {
      queryClient.invalidateQueries({ queryKey: queryKeys.crew() });
      const member = crew.find(c => c.id === id);
      toast.success(`Relief Crew Dispatched for ${member?.name || 'Crew Member'}`, {
        description: `Standby crew assigned at ${member?.reliefStation || 'CNB'} for train ${member?.trainNo || ''}.`,
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

  const criticalCount = crew.filter(c => c.status === 'critical').length;
  const advisoryCount = crew.filter(c => c.status === 'advisory').length;

  return (
    <div className="space-y-4 font-sans">
      {/* Header & Stats Strip */}
      <div className="bg-panel border border-hairline p-4 space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div>
            <h2 className="text-base font-bold font-mono text-text-main flex items-center gap-2">
              <Users className="w-4 h-4 text-accent stroke-[1.5]" />
              <span>LOCO PILOT & CREW DUTY ROSTER WATCH</span>
            </h2>
            <p className="text-xs text-text-dim mt-0.5 font-sans">
              Statutory 10-hour duty limit early warning system. Automatically calculates remaining section running times to prevent mid-section breaches.
            </p>
          </div>

          <div className="flex items-center gap-3">
            <DataFreshnessBadge dataUpdatedAt={dataUpdatedAt} />
            <div className="flex items-center gap-2 font-mono text-xs">
              <div className="px-2.5 py-1 bg-danger/10 border border-danger text-danger">
                {criticalCount} Critical (&lt;2h)
              </div>
              <div className="px-2.5 py-1 bg-warn/10 border border-warn text-warn">
                {advisoryCount} Advisory (2–4h)
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Roster Table */}
      <div className="bg-panel border border-hairline overflow-x-auto">
        <table className="w-full text-left text-xs font-mono border-collapse" role="table">
          <thead>
            <tr className="bg-panel-2 border-b border-hairline text-text-dim text-[11px] uppercase">
              <th scope="col" className="p-3">Crew Member / ID</th>
              <th scope="col" className="p-3">Assigned Train</th>
              <th scope="col" className="p-3">Sign-On</th>
              <th scope="col" className="p-3">Elapsed Duty</th>
              <th scope="col" className="p-3">Projected Total</th>
              <th scope="col" className="p-3">Hours Left</th>
              <th scope="col" className="p-3">Relief Station</th>
              <th scope="col" className="p-3 text-right">Relief Action</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-hairline">
            {crew.map(member => {
              const dutyPercent = Math.min(100, (member.dutyHoursSoFar / member.maxAllowedHours) * 100);
              return (
                <tr key={member.id} className="hover:bg-panel-2/60 transition-colors">
                  {/* Name & ID */}
                  <td className="p-3 whitespace-nowrap">
                    <div className="font-bold text-text-main font-sans">{member.name}</div>
                    <div className="text-[10px] text-text-dim">{member.id} · {member.designation}</div>
                  </td>

                  {/* Train */}
                  <td className="p-3 whitespace-nowrap">
                    <div className="font-bold text-accent">{member.trainNo}</div>
                    <div className="text-[10px] text-text-dim font-sans">{member.trainName}</div>
                  </td>

                  {/* Sign-on */}
                  <td className="p-3 whitespace-nowrap text-text-dim">
                    <div>{member.signOnTime} IST</div>
                    <div className="text-[10px]">{member.signOnStation}</div>
                  </td>

                  {/* Duty Bar & Elapsed */}
                  <td className="p-3 whitespace-nowrap">
                    <div className="font-bold text-text-main">{member.dutyHoursSoFar}h / {member.maxAllowedHours}h</div>
                    <div className="w-24 bg-panel-2 h-1.5 border border-hairline/60 overflow-hidden mt-1">
                      <div
                        className={`h-full ${
                          member.status === 'critical'
                            ? 'bg-danger'
                            : member.status === 'advisory'
                            ? 'bg-warn'
                            : 'bg-ok'
                        }`}
                        style={{ width: `${dutyPercent}%` }}
                      />
                    </div>
                  </td>

                  {/* Projected total */}
                  <td className="p-3 whitespace-nowrap">
                    <span className={member.projectedTotalHours > member.maxAllowedHours ? 'text-danger font-bold' : 'text-text-main'}>
                      {member.projectedTotalHours}h
                    </span>
                    {member.projectedTotalHours > member.maxAllowedHours && (
                      <div className="text-[9px] text-danger uppercase font-bold">Limit Breach</div>
                    )}
                  </td>

                  {/* Hours Left Badge */}
                  <td className="p-3 whitespace-nowrap">
                    {member.status === 'critical' ? (
                      <Badge variant="danger">{member.remainingHours}h remaining</Badge>
                    ) : member.status === 'advisory' ? (
                      <Badge variant="warn">{member.remainingHours}h remaining</Badge>
                    ) : (
                      <Badge variant="ok">{member.remainingHours}h nominal</Badge>
                    )}
                  </td>

                  {/* Relief station */}
                  <td className="p-3 whitespace-nowrap font-bold text-text-main">
                    {member.reliefStation}
                  </td>

                  {/* Relief Action */}
                  <td className="p-3 whitespace-nowrap text-right">
                    {member.reliefRequested ? (
                      <span className="inline-flex items-center gap-1 text-[11px] text-ok font-mono font-semibold">
                        <CheckCircle2 className="w-3.5 h-3.5 stroke-[2]" />
                        <span>Relief Arranged</span>
                      </span>
                    ) : member.status !== 'ok' ? (
                      <Button
                        variant={member.status === 'critical' ? 'danger' : 'secondary'}
                        size="sm"
                        isLoading={requestingId === member.id}
                        onClick={() => handleRequestRelief(member)}
                        className="text-[11px] font-mono h-7 px-2.5"
                      >
                        <UserCheck className="w-3.5 h-3.5 mr-1 stroke-[1.5]" />
                        <span>Dispatch Relief</span>
                      </Button>
                    ) : (
                      <span className="text-text-dim text-[11px]">Nominal</span>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
};
