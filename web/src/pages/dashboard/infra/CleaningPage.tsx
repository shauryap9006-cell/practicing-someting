import React, { useState, useEffect } from 'react';
import { api } from '@/lib/api';
import { SEO } from '@/lib/seo';
import { Sparkles, CheckCircle2, Clock, Droplets, ShieldCheck } from 'lucide-react';
import { toast } from 'sonner';

interface CleaningRecord {
  id: string;
  train_no: string;
  rake_id: string;
  arrival_time: string;
  dep_time: string;
  status: 'PENDING' | 'IN_PROGRESS' | 'DONE';
  turnaround_mins_left: number;
  watering: string;
  disinfection: string;
  supervisor: string;
}

export function CleaningPage() {
  const [logs, setLogs] = useState<CleaningRecord[]>([]);

  useEffect(() => {
    api.getCleaningLogs().then(data => setLogs(data as CleaningRecord[]));
  }, []);

  const handleMarkComplete = (id: string) => {
    setLogs(prev =>
      prev.map(l => (l.id === id ? { ...l, status: 'DONE', watering: 'COMPLETED', disinfection: 'COMPLETED' } : l))
    );
    toast.success(`Cleaning & watering for ${id} signed off by supervisor.`);
  };

  return (
    <div className="space-y-4 font-mono text-xs">
      <SEO title="Rake Cleaning & Turnaround Logs · RailTwin-X" noindex />

      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-3 border-b border-[#26282C] gap-3">
        <div>
          <h1 className="text-lg font-semibold text-[#E8E8E6] flex items-center gap-2">
            <Sparkles className="w-4 h-4 text-[#FFB224]" />
            <span>Rake Cleaning & Mechanical Turnaround Logs</span>
          </h1>
          <p className="text-[#9A9DA3]">
            Track platform coach watering, deep disinfection, and turnaround countdowns
          </p>
        </div>

        {/* Turnaround Stats Strip */}
        <div className="flex items-center gap-3">
          <div className="bg-[#15171A] border border-[#26282C] px-3 py-1.5 text-center">
            <span className="text-[10px] text-[#9A9DA3] block">RAKES HANDLED TODAY</span>
            <span className="font-bold text-sm text-[#3ECF8E]">14 Rakes</span>
          </div>
          <div className="bg-[#15171A] border border-[#26282C] px-3 py-1.5 text-center">
            <span className="text-[10px] text-[#9A9DA3] block">AVG TURNAROUND DWELL</span>
            <span className="font-bold text-sm text-[#FFB224]">24.5 Min</span>
          </div>
        </div>
      </div>

      {/* Cleaning Logs Table */}
      <div className="bg-[#15171A] border border-[#26282C] p-4">
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="border-b border-[#26282C] bg-[#1B1D21] text-[#9A9DA3] text-[11px] uppercase">
                <th className="py-2.5 px-3">Log ID</th>
                <th className="py-2.5 px-3">Train No</th>
                <th className="py-2.5 px-3">Rake ID</th>
                <th className="py-2.5 px-3">Arr / Dep (IST)</th>
                <th className="py-2.5 px-3 text-center">Turnaround Left</th>
                <th className="py-2.5 px-3">Coach Watering</th>
                <th className="py-2.5 px-3">Disinfection</th>
                <th className="py-2.5 px-3">Supervisor</th>
                <th className="py-2.5 px-3 text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#26282C]">
              {logs.map(log => {
                const isUrgent = log.turnaround_mins_left < 15 && log.status !== 'DONE';
                return (
                  <tr key={log.id} className="hover:bg-[#1B1D21]/50 text-[#E8E8E6]">
                    <td className="py-3 px-3 font-bold text-[#FFB224]">{log.id}</td>
                    <td className="py-3 px-3 font-semibold">#{log.train_no}</td>
                    <td className="py-3 px-3 text-[#9A9DA3]">{log.rake_id}</td>
                    <td className="py-3 px-3">{log.arrival_time} &rarr; {log.dep_time}</td>
                    <td className="py-3 px-3 text-center">
                      <span
                        className={`text-[10px] px-2 py-0.5 border font-bold ${
                          log.status === 'DONE'
                            ? 'border-[#3ECF8E] text-[#3ECF8E] bg-[#3ECF8E]/10'
                            : isUrgent
                            ? 'border-[#F0533A] text-[#F0533A] bg-[#F0533A]/10 animate-pulse'
                            : 'border-[#FFB224] text-[#FFB224] bg-[#FFB224]/10'
                        }`}
                      >
                        {log.status === 'DONE' ? 'COMPLETED' : `${log.turnaround_mins_left} min`}
                      </span>
                    </td>
                    <td className="py-3 px-3">
                      <span className="text-[11px] text-[#9A9DA3] flex items-center gap-1">
                        <Droplets className="w-3 h-3 text-[#3ECF8E]" />
                        <span>{log.watering}</span>
                      </span>
                    </td>
                    <td className="py-3 px-3 text-[11px] text-[#9A9DA3]">{log.disinfection}</td>
                    <td className="py-3 px-3 text-[#9A9DA3]">{log.supervisor}</td>
                    <td className="py-3 px-3 text-right">
                      {log.status !== 'DONE' && (
                        <button
                          onClick={() => handleMarkComplete(log.id)}
                          className="text-[#3ECF8E] hover:underline"
                        >
                          Sign Off &rarr;
                        </button>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
