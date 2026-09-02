import React, { useState, useMemo } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/api';
import { queryKeys } from '@/lib/queryKeys';
import { Train } from '@/mock/types';
import {
  AspectLamp,
  AspectType,
  Provenance,
  EmptyState,
} from '@/components/aspect';
import { Search, ArrowUpDown, ChevronRight, TrainTrack, Filter } from 'lucide-react';

export const TrainsPage: React.FC = () => {
  const navigate = useNavigate();
  const { data: trains = [], dataUpdatedAt } = useQuery({
    queryKey: queryKeys.board('CNB'),
    queryFn: () => api.getTrains(),
    refetchInterval: 5000,
  });

  const [searchQuery, setSearchQuery] = useState('');
  const [typeFilter, setTypeFilter] = useState<string>('ALL');
  const [sortField, setSortField] = useState<'number' | 'delayMinutes' | 'predictedArrival'>('predictedArrival');
  const [sortAsc, setSortAsc] = useState(true);

  const getAspect = (delayMin: number): AspectType => {
    if (delayMin <= 5) return 'clear';
    if (delayMin <= 25) return 'caution';
    return 'restrict';
  };

  const filteredTrains = useMemo(() => {
    return trains
      .filter(train => {
        const matchesQuery =
          train.number.toLowerCase().includes(searchQuery.toLowerCase()) ||
          train.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
          train.origin.toLowerCase().includes(searchQuery.toLowerCase()) ||
          train.destination.toLowerCase().includes(searchQuery.toLowerCase());

        const matchesType = typeFilter === 'ALL' || train.type === typeFilter;
        return matchesQuery && matchesType;
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
  }, [trains, searchQuery, typeFilter, sortField, sortAsc]);

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
    <div className="space-y-6 font-mono select-none">
      {/* Header & Filter Controls Card */}
      <div className="bg-[#101216] border border-[#23272F] rounded-lg p-5 space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-4 border-b border-[#23272F]">
          <div>
            <div className="flex items-center gap-2">
              <span className="w-2.5 h-2.5 rounded-full bg-[#F5A524] shadow-[0_0_8px_rgba(245,165,36,0.6)] animate-pulse" />
              <h1 className="text-lg font-bold text-[#E9EBEE] uppercase tracking-wider font-display">
                CORRIDOR TRAINS DIRECTORY ({filteredTrains.length} ACTIVE)
              </h1>
            </div>
            <p className="text-xs font-sans text-[#A3ABB6] mt-1">
              Live tracking, calibrated arrival confidence windows, and delay root cause autopsy.
            </p>
          </div>

          <div className="text-xs text-[#3DDC97] flex items-center gap-1.5 font-semibold">
            <span className="w-1.5 h-1.5 rounded-full bg-[#3DDC97] animate-pulse" />
            <span>TELEMETRY STREAMING</span>
          </div>
        </div>

        {/* Filter bar */}
        <div className="grid grid-cols-1 sm:grid-cols-12 gap-3">
          {/* Search box */}
          <div className="sm:col-span-8 relative">
            <Search className="w-4 h-4 text-[#6B7480] absolute left-3 top-1/2 transform -translate-y-1/2" />
            <input
              type="text"
              value={searchQuery}
              onChange={e => setSearchQuery(e.target.value)}
              placeholder="Search by train number (#12034), name, origin, or destination..."
              className="w-full bg-[#0A0B0D] border border-[#23272F] focus:border-[#F5A524] rounded-sm py-2 pl-9 pr-3 text-xs text-[#E9EBEE] placeholder-[#6B7480]"
            />
          </div>

          {/* Type filter */}
          <div className="sm:col-span-4">
            <select
              value={typeFilter}
              onChange={e => setTypeFilter(e.target.value)}
              className="w-full bg-[#0A0B0D] border border-[#23272F] focus:border-[#F5A524] rounded-sm py-2 px-3 text-xs text-[#E9EBEE]"
            >
              {trainTypes.map(t => (
                <option key={t} value={t} className="bg-[#101216] text-[#E9EBEE]">
                  {t === 'ALL' ? 'All Train Types' : t}
                </option>
              ))}
            </select>
          </div>
        </div>
      </div>

      {/* Main Trains Tabular Instrument Table */}
      <div className="bg-[#101216] border border-[#23272F] rounded-lg overflow-hidden">
        {filteredTrains.length === 0 ? (
          <EmptyState
            title="No matching corridor trains"
            description="Clear search or filter criteria to view all active corridor trains."
            onRetry={() => {
              setSearchQuery('');
              setTypeFilter('ALL');
            }}
          />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left font-mono text-xs border-collapse">
              <thead>
                <tr className="border-b border-[#23272F] bg-[#0A0B0D] text-[#A3ABB6] text-[11px] uppercase">
                  <th
                    className="py-3.5 px-4 cursor-pointer hover:text-[#E9EBEE] select-none"
                    onClick={() => toggleSort('number')}
                  >
                    <div className="flex items-center gap-1.5">
                      <span>Train No</span>
                      <ArrowUpDown className="w-3 h-3 text-[#6B7480]" />
                    </div>
                  </th>
                  <th className="py-3.5 px-4">Train Name & Route</th>
                  <th className="py-3.5 px-4">Type</th>
                  <th className="py-3.5 px-4 text-center">PF</th>
                  <th
                    className="py-3.5 px-4 cursor-pointer hover:text-[#E9EBEE] select-none"
                    onClick={() => toggleSort('predictedArrival')}
                  >
                    <div className="flex items-center gap-1.5">
                      <span>Expected Arrival</span>
                      <ArrowUpDown className="w-3 h-3 text-[#6B7480]" />
                    </div>
                  </th>
                  <th className="py-3.5 px-4">Confidence Window</th>
                  <th
                    className="py-3.5 px-4 text-right cursor-pointer hover:text-[#E9EBEE] select-none"
                    onClick={() => toggleSort('delayMinutes')}
                  >
                    <div className="flex items-center justify-end gap-1.5">
                      <span>Signal Aspect</span>
                      <ArrowUpDown className="w-3 h-3 text-[#6B7480]" />
                    </div>
                  </th>
                  <th className="py-3.5 px-4 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#23272F]">
                {filteredTrains.map((train, idx) => {
                  const aspect = getAspect(train.delayMinutes);
                  const delayLabel = train.delayMinutes <= 0 ? 'ON TIME' : `+${train.delayMinutes}M`;

                  return (
                    <tr
                      key={train.number}
                      className="hover:bg-[#15181D] transition-colors group cursor-pointer"
                      onClick={() => navigate(`/dashboard/trains/${train.number}`)}
                    >
                      {/* Train Number */}
                      <td className="py-3 px-4 font-bold text-[#E9EBEE] text-xs">
                        {train.number}
                      </td>

                      {/* Name & Route */}
                      <td className="py-3 px-4">
                        <div className="font-bold text-[#E9EBEE] font-sans text-xs group-hover:text-[#F5A524] transition-colors">
                          {train.name}
                        </div>
                        <div className="text-[10px] text-[#6B7480] mt-0.5">
                          {train.origin} → {train.destination}
                        </div>
                      </td>

                      {/* Type */}
                      <td className="py-3 px-4 text-[#A3ABB6] text-[11px]">
                        {train.type}
                      </td>

                      {/* Platform */}
                      <td className="py-3 px-4 text-center">
                        <span className="px-2 py-0.5 bg-[#0A0B0D] border border-[#23272F] rounded-xs font-bold text-[#E9EBEE]">
                          {train.platform || (idx % 5 + 1)}
                        </span>
                      </td>

                      {/* Predicted Arrival */}
                      <td className="py-3 px-4 font-bold text-[#E9EBEE] tabular-nums">
                        {train.predictedArrival || '18:22'}
                      </td>

                      {/* Confidence Window (Signal Blue Tint) */}
                      <td className="py-3 px-4">
                        <span className="px-2 py-0.5 bg-[rgba(108,159,255,0.13)] border border-[#6C9FFF]/40 text-[#6C9FFF] rounded-xs text-[11px]">
                          {train.etaBand?.p10 || '18:15'} – {train.etaBand?.p90 || '19:05'}
                        </span>
                      </td>

                      {/* Signal Aspect Lamp */}
                      <td className="py-3 px-4 text-right">
                        <AspectLamp aspect={aspect} label={delayLabel} size="sm" />
                      </td>

                      {/* Action */}
                      <td className="py-3 px-4 text-right">
                        <span className="inline-flex items-center gap-1 text-[11px] text-[#A3ABB6] group-hover:text-[#F5A524] transition-colors font-semibold">
                          <span>Autopsy</span>
                          <ChevronRight className="w-3.5 h-3.5" />
                        </span>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}

        <div className="p-4 border-t border-[#23272F] bg-[#0A0B0D]">
          <Provenance updatedAt={dataUpdatedAt} source="CORRIDOR REAL-TIME TELEMETRY STREAM" />
        </div>
      </div>
    </div>
  );
};
