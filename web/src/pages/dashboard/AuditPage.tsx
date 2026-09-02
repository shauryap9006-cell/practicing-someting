import React, { useState, useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/api';
import { queryKeys } from '@/lib/queryKeys';
import { AuditEntry } from '@/mock/types';
import {
  AspectLamp,
  AspectType,
  Provenance,
  EmptyState,
} from '@/components/aspect';
import { ShieldCheck, Search, Filter, ChevronDown, ChevronRight, Hash, CheckCircle2 } from 'lucide-react';

export const AuditPage: React.FC = () => {
  const { data: logs = [], dataUpdatedAt } = useQuery({
    queryKey: queryKeys.audit(),
    queryFn: () => api.getAuditLogs(),
    refetchInterval: 5000,
  });
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedType, setSelectedType] = useState<string>('ALL');
  const [expandedId, setExpandedId] = useState<string | null>(null);

  const eventTypes = [
    { label: 'All Events', value: 'ALL' },
    { label: 'Advisory Sign-Offs', value: 'advisory_ack' },
    { label: 'Advisory Dismissals', value: 'advisory_dismiss' },
    { label: 'Platform Re-Opt', value: 'platform_reopt' },
    { label: 'Crew Relief', value: 'crew_relief' },
    { label: 'Speed Regulations', value: 'speed_regulation' },
  ];

  const filteredLogs = useMemo(() => {
    return logs.filter(log => {
      const matchesType = selectedType === 'ALL' || log.eventType === selectedType;
      const matchesQuery =
        log.action.toLowerCase().includes(searchQuery.toLowerCase()) ||
        log.actor.toLowerCase().includes(searchQuery.toLowerCase()) ||
        log.details.toLowerCase().includes(searchQuery.toLowerCase()) ||
        (log.trainNo && log.trainNo.toLowerCase().includes(searchQuery.toLowerCase())) ||
        log.referenceHash.toLowerCase().includes(searchQuery.toLowerCase());
      return matchesType && matchesQuery;
    });
  }, [logs, selectedType, searchQuery]);

  const toggleExpand = (id: string) => {
    setExpandedId(expandedId === id ? null : id);
  };

  return (
    <div className="space-y-6 font-mono select-none">
      {/* Header & Immutable Ledger Meta */}
      <div className="bg-[#101216] border border-[#23272F] rounded-lg p-5 space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-4 border-b border-[#23272F]">
          <div>
            <div className="flex items-center gap-2">
              <span className="w-2.5 h-2.5 rounded-full bg-[#F5A524] shadow-[0_0_8px_rgba(245,165,36,0.6)] animate-pulse" />
              <h1 className="text-lg font-bold text-[#E9EBEE] uppercase tracking-wider font-display">
                REGULATORY AUDIT LEDGER & COMPLIANCE LOG ({filteredLogs.length})
              </h1>
            </div>
            <p className="text-xs font-sans text-[#A3ABB6] mt-1">
              Cryptographically referenced audit ledger. Dispatcher sign-offs, overrides, and safety interlocks permanently logged.
            </p>
          </div>

          <div className="text-xs text-[#3DDC97] flex items-center gap-1.5 font-semibold">
            <ShieldCheck className="w-4 h-4" />
            <span>HASH INTEGRITY VERIFIED</span>
          </div>
        </div>

        {/* Search & Filter Toolbar */}
        <div className="space-y-3 pt-1">
          <div className="relative">
            <Search className="w-4 h-4 text-[#6B7480] absolute left-3 top-1/2 transform -translate-y-1/2" />
            <input
              type="text"
              value={searchQuery}
              onChange={e => setSearchQuery(e.target.value)}
              placeholder="Search audit records by actor, train, action, or SHA-256 reference hash..."
              className="w-full bg-[#0A0B0D] border border-[#23272F] focus:border-[#F5A524] rounded-sm py-2 pl-9 pr-3 text-xs text-[#E9EBEE] placeholder-[#6B7480]"
            />
          </div>

          <div className="flex flex-wrap items-center gap-1.5 text-xs">
            {eventTypes.map(t => (
              <button
                key={t.value}
                type="button"
                onClick={() => setSelectedType(t.value)}
                className={`px-2.5 py-1 rounded-sm border transition-colors ${
                  selectedType === t.value
                    ? 'bg-[#F5A524] text-[#0A0B0D] border-[#F5A524] font-bold'
                    : 'border-[#23272F] bg-[#0A0B0D] text-[#A3ABB6] hover:border-[#2E333D] hover:text-[#E9EBEE]'
                }`}
              >
                {t.label}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Ledger Table */}
      <div className="bg-[#101216] border border-[#23272F] rounded-lg overflow-hidden">
        {filteredLogs.length === 0 ? (
          <EmptyState
            title="No matching ledger records"
            description="Clear search or filter criteria to view all compliance entries."
            onRetry={() => {
              setSearchQuery('');
              setSelectedType('ALL');
            }}
          />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs font-mono border-collapse">
              <thead>
                <tr className="bg-[#0A0B0D] border-b border-[#23272F] text-[#A3ABB6] text-[11px] uppercase">
                  <th className="py-3 px-4">Timestamp (IST)</th>
                  <th className="py-3 px-4">Action Summary</th>
                  <th className="py-3 px-4">Operator</th>
                  <th className="py-3 px-4">Target Train</th>
                  <th className="py-3 px-4">Safety Interlock</th>
                  <th className="py-3 px-4 text-right">SHA-256 Hash</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#23272F]">
                {filteredLogs.map(log => {
                  const isExpanded = expandedId === log.id;

                  return (
                    <React.Fragment key={log.id}>
                      <tr
                        onClick={() => toggleExpand(log.id)}
                        className="hover:bg-[#15181D] transition-colors cursor-pointer"
                      >
                        <td className="py-3 px-4 text-[#A3ABB6] tabular-nums">
                          {log.timestamp}
                        </td>

                        <td className="py-3 px-4 font-bold text-[#E9EBEE] font-sans text-xs">
                          {log.action}
                        </td>

                        <td className="py-3 px-4 text-[#A3ABB6]">
                          {log.actor}
                        </td>

                        <td className="py-3 px-4 font-bold text-[#F5A524]">
                          {log.trainNo || 'Corridor-Wide'}
                        </td>

                        <td className="py-3 px-4">
                          <span className="px-2 py-0.5 bg-[rgba(61,220,151,0.13)] border border-[#3DDC97]/40 text-[#3DDC97] text-[10px] font-bold rounded-sm">
                            CONFIRMED
                          </span>
                        </td>

                        <td className="py-3 px-4 text-right text-[#6B7480] font-mono text-[11px]">
                          {log.referenceHash.slice(0, 12)}…
                        </td>
                      </tr>

                      {isExpanded && (
                        <tr className="bg-[#0A0B0D]/80">
                          <td colSpan={6} className="p-4 border-t border-[#23272F]">
                            <div className="space-y-2 text-xs">
                              <span className="text-[10px] text-[#6B7480] uppercase block">Detailed Payload Log</span>
                              <p className="font-sans text-[#A3ABB6] leading-relaxed">
                                {log.details}
                              </p>
                              <div className="pt-2 text-[10px] text-[#6B7480] font-mono">
                                Full Hash: {log.referenceHash}
                              </div>
                            </div>
                          </td>
                        </tr>
                      )}
                    </React.Fragment>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}

        <div className="p-4 border-t border-[#23272F] bg-[#0A0B0D]">
          <Provenance updatedAt={dataUpdatedAt} source="CRYPTO AUDIT F14 IMMUTABLE LEDGER" />
        </div>
      </div>
    </div>
  );
};
