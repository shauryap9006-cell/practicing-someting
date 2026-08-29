import React, { useState, useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/api';
import { queryKeys } from '@/lib/queryKeys';
import { AuditEntry } from '@/mock/types';
import { Badge } from '@/components/ui/Badge';
import { Input } from '@/components/ui/Input';
import { DataFreshnessBadge } from '@/components/common/DataFreshnessBadge';
import { ShieldCheck, Search, Filter, ChevronDown, ChevronRight, Hash } from 'lucide-react';

export const AuditPage: React.FC = () => {
  const { data: logs = [], dataUpdatedAt } = useQuery({
    queryKey: queryKeys.audit(),
    queryFn: () => api.getAuditLogs(),
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
    { label: 'Station Switches', value: 'station_switch' },
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
    <div className="space-y-4 font-sans">
      {/* Header & Immutable Ledger Meta */}
      <div className="bg-panel border border-hairline p-4 space-y-3">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div>
            <h2 className="text-base font-bold font-mono text-text-main flex items-center gap-2">
              <ShieldCheck className="w-4 h-4 text-accent stroke-[1.5]" />
              <span>REGULATORY AUDIT LOG & COMPLIANCE LEDGER</span>
            </h2>
            <p className="text-xs text-text-dim mt-0.5 font-sans">
              Cryptographically referenced audit ledger. Every human dispatcher sign-off, override, and automated safety interlock is permanently recorded.
            </p>
          </div>
          <DataFreshnessBadge dataUpdatedAt={dataUpdatedAt} />
        </div>

        {/* Filter Chips & Search Bar */}
        <div className="space-y-3 pt-2">
          {/* Search box */}
          <div className="relative">
            <Search className="w-4 h-4 text-text-dim absolute left-3 top-2.5 stroke-[1.5]" />
            <Input
              value={searchQuery}
              onChange={e => setSearchQuery(e.target.value)}
              placeholder="Search audit records by actor, train, action, or reference hash..."
              className="pl-9 text-xs font-mono"
            />
          </div>

          {/* Event Filter Chips */}
          <div className="flex flex-wrap items-center gap-1.5 text-xs font-mono">
            {eventTypes.map(t => (
              <button
                key={t.value}
                onClick={() => setSelectedType(t.value)}
                className={`px-2.5 py-1 border transition-colors ${
                  selectedType === t.value
                    ? 'bg-panel-2 border-accent text-accent font-semibold'
                    : 'border-hairline bg-panel text-text-dim hover:text-text-main'
                }`}
              >
                {t.label}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Ledger Table */}
      <div className="bg-panel border border-hairline overflow-x-auto">
        <table className="w-full text-left text-xs font-mono border-collapse" role="table">
          <thead>
            <tr className="bg-panel-2 border-b border-hairline text-text-dim text-[11px] uppercase select-none">
              <th scope="col" className="p-3 w-8"></th>
              <th scope="col" className="p-3">Timestamp (IST)</th>
              <th scope="col" className="p-3">Event Type</th>
              <th scope="col" className="p-3">Train / Zone</th>
              <th scope="col" className="p-3">Action Description</th>
              <th scope="col" className="p-3">Actor / Authorizer</th>
              <th scope="col" className="p-3 text-right">Ledger Hash</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-hairline">
            {filteredLogs.length === 0 ? (
              <tr>
                <td colSpan={7} className="p-8 text-center text-xs text-text-dim">
                  No audit entries found matching current filter.
                </td>
              </tr>
            ) : (
              filteredLogs.map(entry => {
                const isExpanded = expandedId === entry.id;
                return (
                  <React.Fragment key={entry.id}>
                    <tr
                      onClick={() => toggleExpand(entry.id)}
                      className={`hover:bg-panel-2/60 cursor-pointer transition-colors ${
                        isExpanded ? 'bg-panel-2/40' : ''
                      }`}
                    >
                      <td className="p-3 text-text-dim">
                        {isExpanded ? (
                          <ChevronDown className="w-3.5 h-3.5 stroke-[1.5]" />
                        ) : (
                          <ChevronRight className="w-3.5 h-3.5 stroke-[1.5]" />
                        )}
                      </td>
                      <td className="p-3 whitespace-nowrap font-bold text-text-main">
                        {entry.timestamp}
                      </td>
                      <td className="p-3 whitespace-nowrap">
                        <Badge
                          variant={
                            entry.eventType === 'advisory_ack'
                              ? 'ok'
                              : entry.eventType === 'advisory_dismiss'
                              ? 'warn'
                              : entry.eventType === 'crew_relief'
                              ? 'danger'
                              : 'neutral'
                          }
                        >
                          {entry.eventType.replace('_', ' ').toUpperCase()}
                        </Badge>
                      </td>
                      <td className="p-3 whitespace-nowrap">
                        <span className="font-bold text-accent mr-1.5">{entry.trainNo || 'CORRIDOR'}</span>
                        <span className="text-[10px] text-text-dim">{entry.zone}</span>
                      </td>
                      <td className="p-3 text-text-main font-sans text-xs">
                        {entry.action}
                      </td>
                      <td className="p-3 whitespace-nowrap text-text-dim text-[11px]">
                        {entry.actor}
                      </td>
                      <td className="p-3 whitespace-nowrap text-right text-[11px] text-text-dim font-mono">
                        {entry.referenceHash}
                      </td>
                    </tr>

                    {/* Expandable Detail Payload */}
                    {isExpanded && (
                      <tr className="bg-panel-2/30">
                        <td colSpan={7} className="p-4 pl-10 border-b border-hairline space-y-2">
                          <div className="text-xs font-sans text-text-main leading-relaxed">
                            <span className="font-bold font-mono text-[11px] text-text-dim mr-2">LOG DETAILS:</span>
                            {entry.details}
                          </div>
                          {entry.payload && (
                            <div className="pt-2">
                              <span className="text-[10px] font-mono text-text-dim uppercase block mb-1">
                                Structured Telemetry Payload:
                              </span>
                              <pre className="p-2.5 bg-bg border border-hairline text-[11px] font-mono text-text-main overflow-x-auto">
                                {JSON.stringify(entry.payload, null, 2)}
                              </pre>
                            </div>
                          )}
                        </td>
                      </tr>
                    )}
                  </React.Fragment>
                );
              })
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
};
