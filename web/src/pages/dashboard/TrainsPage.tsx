import React, { useState, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/api';
import { queryKeys } from '@/lib/queryKeys';
import { Train, TrainType } from '@/mock/types';
import { Badge } from '@/components/ui/Badge';
import { Input } from '@/components/ui/Input';
import { Button } from '@/components/ui/Button';
import { DataFreshnessBadge } from '@/components/common/DataFreshnessBadge';
import { formatMinutes } from '@/lib/utils';
import { Search, Filter, ArrowUpDown, ChevronRight, TrainTrack } from 'lucide-react';

export const TrainsPage: React.FC = () => {
  const navigate = useNavigate();
  const { data: trains = [], dataUpdatedAt } = useQuery({
    queryKey: queryKeys.board('NDLS'),
    queryFn: () => api.getTrains(),
  });
  const [searchQuery, setSearchQuery] = useState('');
  const [typeFilter, setTypeFilter] = useState<string>('ALL');
  const [statusFilter, setStatusFilter] = useState<string>('ALL');
  const [sortField, setSortField] = useState<'number' | 'delayMinutes' | 'predictedArrival'>('predictedArrival');
  const [sortAsc, setSortAsc] = useState(true);

  const filteredTrains = useMemo(() => {
    return trains
      .filter(train => {
        const matchesQuery =
          train.number.toLowerCase().includes(searchQuery.toLowerCase()) ||
          train.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
          train.origin.toLowerCase().includes(searchQuery.toLowerCase()) ||
          train.destination.toLowerCase().includes(searchQuery.toLowerCase());

        const matchesType = typeFilter === 'ALL' || train.type === typeFilter;
        const matchesStatus = statusFilter === 'ALL' || train.status === statusFilter;

        return matchesQuery && matchesType && matchesStatus;
      })
      .sort((a, b) => {
        if (sortField === 'number') {
          return sortAsc ? a.number.localeCompare(b.number) : b.number.localeCompare(a.number);
        }
        if (sortField === 'delayMinutes') {
          return sortAsc ? a.delayMinutes - b.delayMinutes : b.delayMinutes - a.delayMinutes;
        }
        if (sortField === 'predictedArrival') {
          return sortAsc
            ? a.predictedArrival.localeCompare(b.predictedArrival)
            : b.predictedArrival.localeCompare(a.predictedArrival);
        }
        return 0;
      });
  }, [trains, searchQuery, typeFilter, statusFilter, sortField, sortAsc]);

  const toggleSort = (field: 'number' | 'delayMinutes' | 'predictedArrival') => {
    if (sortField === field) {
      setSortAsc(!sortAsc);
    } else {
      setSortField(field);
      setSortAsc(true);
    }
  };

  const trainTypes = ['ALL', 'Rajdhani Express', 'Shatabdi Express', 'Vande Bharat', 'Superfast', 'Mail / Express', 'DFC Freight'];

  return (
    <div className="space-y-4 font-sans">
      {/* Header & Filter Controls */}
      <div className="bg-panel border border-hairline p-4 space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
          <div>
            <h2 className="text-base font-bold font-mono text-text-main flex items-center gap-2">
              <TrainTrack className="w-4 h-4 text-accent stroke-[1.5]" />
              <span>CORRIDOR TRAINS DIRECTORY ({filteredTrains.length} ACTIVE)</span>
            </h2>
            <p className="text-xs text-text-dim mt-0.5">
              Live tracking, calibrated ETA bands ($p_{10}, p_{50}, p_{90}$), and delay breakdown across all corridor trains.
            </p>
          </div>
          <DataFreshnessBadge dataUpdatedAt={dataUpdatedAt} />
        </div>

        {/* Filter bar */}
        <div className="grid grid-cols-1 sm:grid-cols-12 gap-3">
          {/* Search box */}
          <div className="sm:col-span-6 relative">
            <Search className="w-4 h-4 text-text-dim absolute left-3 top-2.5 stroke-[1.5]" />
            <Input
              value={searchQuery}
              onChange={e => setSearchQuery(e.target.value)}
              placeholder="Search by train number, name, origin, or destination..."
              className="pl-9 text-xs"
            />
          </div>

          {/* Type filter */}
          <div className="sm:col-span-3">
            <select
              value={typeFilter}
              onChange={e => setTypeFilter(e.target.value)}
              className="w-full h-8 px-2 bg-panel-2 border border-hairline text-text-main text-xs font-mono rounded-none focus-visible:outline-none focus-visible:border-accent"
            >
              {trainTypes.map(t => (
                <option key={t} value={t}>
                  {t === 'ALL' ? 'All Train Types' : t}
                </option>
              ))}
            </select>
          </div>

          {/* Status filter */}
          <div className="sm:col-span-3">
            <select
              value={statusFilter}
              onChange={e => setStatusFilter(e.target.value)}
              className="w-full h-8 px-2 bg-panel-2 border border-hairline text-text-main text-xs font-mono rounded-none focus-visible:outline-none focus-visible:border-accent"
            >
              <option value="ALL">All Delay Statuses</option>
              <option value="on_time">On Time (&lt;5m)</option>
              <option value="delayed">Delayed (5–20m)</option>
              <option value="critical">Critical (&gt;20m)</option>
            </select>
          </div>
        </div>
      </div>

      {/* Virtualized Table Container */}
      <div className="bg-panel border border-hairline overflow-x-auto">
        <table className="w-full text-left text-xs font-mono border-collapse" role="table">
          <thead>
            <tr className="bg-panel-2 border-b border-hairline text-text-dim text-[11px] uppercase select-none">
              <th
                scope="col"
                className="p-3 cursor-pointer hover:text-text-main"
                onClick={() => toggleSort('number')}
              >
                <div className="flex items-center gap-1">
                  <span>Train</span>
                  <ArrowUpDown className="w-3 h-3 stroke-[1.5]" />
                </div>
              </th>
              <th scope="col" className="p-3">Type</th>
              <th scope="col" className="p-3">Route & Current Position</th>
              <th scope="col" className="p-3">Sched</th>
              <th
                scope="col"
                className="p-3 cursor-pointer hover:text-text-main"
                onClick={() => toggleSort('predictedArrival')}
              >
                <div className="flex items-center gap-1">
                  <span>Predicted Band (p10 / p50 / p90)</span>
                  <ArrowUpDown className="w-3 h-3 stroke-[1.5]" />
                </div>
              </th>
              <th
                scope="col"
                className="p-3 cursor-pointer hover:text-text-main"
                onClick={() => toggleSort('delayMinutes')}
              >
                <div className="flex items-center gap-1">
                  <span>Delay</span>
                  <ArrowUpDown className="w-3 h-3 stroke-[1.5]" />
                </div>
              </th>
              <th scope="col" className="p-3">Regime</th>
              <th scope="col" className="p-3">PF</th>
              <th scope="col" className="p-3 text-right">Action</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-hairline">
            {filteredTrains.length === 0 ? (
              <tr>
                <td colSpan={9} className="p-8 text-center text-xs text-text-dim">
                  No trains found matching current filters.
                </td>
              </tr>
            ) : (
              filteredTrains.map(train => {
                const reg = train.regimeWeights || { clearTrack: 0.8, congestion: 0.15, winterFog: 0.05 };
                const topRegime =
                  reg.winterFog >= 0.4
                    ? { label: 'FOG', variant: 'neutral' as const }
                    : reg.congestion >= 0.4
                    ? { label: 'CONGESTION', variant: 'warn' as const }
                    : { label: 'CLEAR', variant: 'ok' as const };

                return (
                  <tr
                    key={train.number}
                    onClick={() => navigate(`/dashboard/trains/${train.number}`)}
                    className="hover:bg-panel-2/60 cursor-pointer transition-colors group"
                  >
                    <td className="p-3 whitespace-nowrap">
                      <div className="font-bold text-accent group-hover:underline">
                        {train.number}
                      </div>
                      <div className="font-sans text-[11px] text-text-dim truncate max-w-[180px]">
                        {train.name}
                      </div>
                    </td>
                    <td className="p-3 whitespace-nowrap text-text-dim text-[11px]">
                      {train.type}
                    </td>
                    <td className="p-3 whitespace-nowrap">
                      <div className="text-text-main text-[11px]">{train.origin} → {train.destination}</div>
                      <div className="text-[10px] text-text-dim font-sans">{train.routePosition}</div>
                    </td>
                    <td className="p-3 whitespace-nowrap text-text-dim">
                      {train.scheduledArrival}
                    </td>
                    <td className="p-3 whitespace-nowrap">
                      <div className="flex items-center gap-1.5 text-xs">
                        <span className="text-text-dim text-[11px]">{train.etaBand?.p10 ?? train.scheduledArrival}</span>
                        <span className="font-bold text-text-main">{train.etaBand?.p50 ?? train.predictedArrival ?? train.scheduledArrival}</span>
                        <span className="text-text-dim text-[11px]">{train.etaBand?.p90 ?? train.scheduledArrival}</span>
                      </div>
                    </td>
                    <td className="p-3 whitespace-nowrap">
                      {train.delayMinutes === 0 ? (
                        <Badge variant="ok">ON TIME</Badge>
                      ) : train.delayMinutes > 20 ? (
                        <Badge variant="danger">{formatMinutes(train.delayMinutes)}</Badge>
                      ) : (
                        <Badge variant="warn">{formatMinutes(train.delayMinutes)}</Badge>
                      )}
                    </td>
                    <td className="p-3 whitespace-nowrap">
                      <Badge variant={topRegime.variant} className="text-[9px] py-0">
                        {topRegime.label}
                      </Badge>
                    </td>
                    <td className="p-3 whitespace-nowrap font-bold text-text-main">
                      PF{train.platform}
                    </td>
                    <td className="p-3 whitespace-nowrap text-right">
                      <span className="text-[11px] text-text-dim group-hover:text-accent flex items-center justify-end gap-1 font-mono">
                        <span>Detail</span>
                        <ChevronRight className="w-3.5 h-3.5 stroke-[1.5]" />
                      </span>
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
};
