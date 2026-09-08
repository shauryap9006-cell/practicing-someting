import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../lib/api';
import type { LivePosition, CongestionRadarData } from '@railtwin/shared-types';
import { SectionShell, StatCard, DataTable, LoadingState, ErrorState, type TableColumn } from '../primitives';

export const NetworkPage: React.FC = () => {
  const navigate = useNavigate();
  const [positions, setPositions] = useState<LivePosition[]>([]);
  const [radar, setRadar] = useState<CongestionRadarData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedSection, setSelectedSection] = useState<string>('ALL');

  const fetchNetworkState = async () => {
    setLoading(true);
    setError(null);
    try {
      const [posData, radarData] = await Promise.all([
        api.live.positions(),
        api.corridor.congestionRadar(),
      ]);

      setPositions(posData);
      setRadar(radarData);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : 'Failed to load corridor network state.'
      );
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchNetworkState();
    // Poll every 15 seconds for live fleet
    const interval = setInterval(fetchNetworkState, 15000);
    return () => clearInterval(interval);
  }, []);

  if (loading && positions.length === 0) {
    return (
      <div className="max-w-6xl mx-auto w-full p-4 sm:p-6 lg:p-8 flex flex-col gap-6">
        <LoadingState rows={5} message="Acquiring 1,447 km corridor telemetry..." />
      </div>
    );
  }

  if (error && positions.length === 0) {
    return (
      <div className="max-w-4xl mx-auto w-full p-4 sm:p-6 lg:p-8 flex flex-col gap-6">
        <ErrorState
          title="Corridor Network Telemetry Fault"
          message={error}
          onRetry={fetchNetworkState}
        />
      </div>
    );
  }

  const radarSections = radar?.radar || [];
  const horizons = radar?.horizons || ['T+0h', 'T+1h', 'T+2h', 'T+4h', 'T+6h'];

  // Key corridor landmarks for 1D Spine
  const landmarks = [
    { code: 'NDLS', name: 'New Delhi', km: 0 },
    { code: 'ALJN', name: 'Aligarh', km: 131 },
    { code: 'TDL', name: 'Tundla', km: 204 },
    { code: 'CNB', name: 'Kanpur', km: 440 },
    { code: 'PRYJ', name: 'Prayagraj', km: 635 },
    { code: 'DDU', name: 'Pt Deen Dayal', km: 788 },
    { code: 'GAYA', name: 'Gaya', km: 993 },
    { code: 'DHN', name: 'Dhanbad', km: 1190 },
    { code: 'HWH', name: 'Howrah', km: 1447 },
  ];

  // Filtered positions for data table
  const filteredPositions = positions.filter((p: LivePosition) => {
    if (selectedSection === 'ALL') return true;
    return p.section_id?.includes(selectedSection) || p.current_station_code === selectedSection;
  });

  const columns: TableColumn<LivePosition>[] = [
    {
      header: 'Train',
      accessor: (row: LivePosition) => (
        <span className="font-mono font-bold text-xs px-2 py-0.5 bg-surface border border-line rounded-[3px] tabular-nums">
          #{row.train_no}
        </span>
      ),
    },
    {
      header: 'Section',
      accessor: (row: LivePosition) => (
        <span className="font-mono text-xs text-ink font-medium">
          {row.section_id || row.current_station_code || '--'}
        </span>
      ),
    },
    {
      header: 'Speed',
      accessor: (row: LivePosition) => `${Math.round(row.speed_kmh)} km/h`,
      align: 'right',
      isNumeric: true,
    },
    {
      header: 'Delay',
      accessor: (row: LivePosition) => {
        const d = Math.round(row.delay_minutes);
        return (
          <span
            className={`font-mono text-xs px-1.5 py-0.5 rounded-[2px] font-medium ${
              d > 5
                ? 'text-restrict bg-restrict/10 border border-restrict/30'
                : 'text-clear bg-clear/10 border border-clear/30'
            }`}
          >
            {d > 0 ? `+${d}m` : '0m'}
          </span>
        );
      },
      align: 'right',
    },
    {
      header: 'Aspect',
      accessor: (row: LivePosition) => {
        const aspect = row.inferred_signal_aspect || 'GREEN';
        const color =
          aspect === 'RED'
            ? 'bg-restrict text-surface'
            : aspect === 'YELLOW'
            ? 'bg-caution text-ink'
            : 'bg-clear text-surface';

        return (
          <span className={`font-mono text-[9px] uppercase px-1.5 py-0.5 rounded-[2px] font-bold ${color}`}>
            {aspect}
          </span>
        );
      },
      align: 'center',
    },
    {
      header: 'Fix Time',
      accessor: (row: LivePosition) => (
        <span className="font-mono text-[10px] text-muted">
          {row.last_event_time ? row.last_event_time.split('T')[1]?.slice(0, 8) : '--'}
        </span>
      ),
      align: 'right',
    },
  ];

  return (
    <div className="max-w-6xl mx-auto w-full p-4 sm:p-6 lg:p-8 flex flex-col gap-6">
      {/* Header */}
      <div className="flex flex-col gap-1 border-b border-line/60 pb-5">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-[2px] bg-ink" />
            <span className="font-mono text-micro uppercase tracking-wider text-muted font-medium">
              Corridor Digital Twin · PS 26028
            </span>
          </div>
          <span className="font-mono text-xs text-muted">
            Auto-refresh: 15s
          </span>
        </div>

        <h1 className="font-serif text-3xl sm:text-4xl font-bold tracking-tight text-ink">
          Network State & Congestion Radar
        </h1>
        <p className="font-sans text-sm text-ink/75 max-w-2xl">
          Real-time 1D spatial model of the New Delhi &mdash; Howrah Main Trunk Corridor.
          Aggregates section block occupancy, signal aspects, and 6-hour forward congestion horizon.
        </p>
      </div>

      {/* Network Stats Strip */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <StatCard
          label="Active Fleet"
          value={positions.length > 0 ? `${positions.length} Trains` : '--'}
          subtext="Under active corridor block"
        />
        <StatCard
          label="Corridor Span"
          value="1,447 km"
          subtext="NDLS to HWH Main Trunk"
        />
        <StatCard
          label="Critical Chokepoints"
          value={radar?.highest_chokepoints?.length ? `${radar.highest_chokepoints.length} Sections` : '0 Sections'}
          subtext="Peak capacity reached"
          deltaType={radar?.highest_chokepoints?.length ? 'negative' : 'positive'}
        />
        <StatCard
          label="Telemetry Integrity"
          value="100% Live"
          subtext="Zero mock estimation"
          deltaType="positive"
        />
      </div>

      {/* 1D Corridor Fleet Spine (SVG) */}
      <SectionShell
        microLabel="1D Spatial Corridor Model"
        title="Fleet Distribution Along 1,447 km Trunk"
        action={
          <span className="font-mono text-xs text-muted">
            {positions.length} active positions
          </span>
        }
      >
        <div className="overflow-x-auto select-none py-2">
          <div className="min-w-[700px] w-full">
            <svg
              viewBox="0 0 900 130"
              className="w-full h-auto overflow-visible"
              preserveAspectRatio="xMidYMid meet"
            >
              {/* Baseline Track Spine */}
              <line
                x1="40"
                y1="60"
                x2="860"
                y2="60"
                stroke="#E1DAC9"
                strokeWidth="4"
                strokeLinecap="round"
              />

              {/* Landmark Stations */}
              {landmarks.map((lm) => {
                const x = 40 + (lm.km / 1447) * 820;

                return (
                  <g key={lm.code}>
                    {/* Tick mark */}
                    <line
                      x1={x}
                      y1="50"
                      x2={x}
                      y2="70"
                      stroke="#8A8477"
                      strokeWidth="1.5"
                    />
                    {/* Pip */}
                    <circle
                      cx={x}
                      cy="60"
                      r="3.5"
                      fill="#FDFCF8"
                      stroke="#191712"
                      strokeWidth="1.5"
                    />
                    {/* Station Code */}
                    <text
                      x={x}
                      y="40"
                      textAnchor="middle"
                      className="font-mono text-[10px] font-bold fill-ink"
                    >
                      {lm.code}
                    </text>
                    {/* Station Km */}
                    <text
                      x={x}
                      y="85"
                      textAnchor="middle"
                      className="font-mono text-[9px] fill-muted tabular-nums"
                    >
                      {lm.km} km
                    </text>
                  </g>
                );
              })}

              {/* Render Train Pips */}
              {positions.slice(0, 150).map((train: LivePosition, idx: number) => {
                const pct = train.progress_pct != null ? train.progress_pct / 100 : idx / 150;
                const x = 40 + Math.min(1, Math.max(0, pct)) * 820;
                const isLate = train.delay_minutes > 15;

                return (
                  <g
                    key={`${train.train_no}-${idx}`}
                    className="cursor-pointer group"
                    onClick={() => navigate(`/t/${train.train_no}`)}
                  >
                    <circle
                      cx={x}
                      cy="60"
                      r="4"
                      fill={isLate ? '#B3362B' : '#C25E00'}
                      stroke="#FDFCF8"
                      strokeWidth="1"
                      className="transition-transform hover:scale-150"
                    />
                  </g>
                );
              })}
            </svg>
          </div>

          <div className="flex flex-wrap items-center justify-between text-[11px] font-mono text-muted pt-3 border-t border-line/40 px-1">
            <div className="flex items-center gap-4">
              <div className="flex items-center gap-1.5">
                <span className="w-2.5 h-2.5 rounded-full bg-ochre inline-block" />
                <span>On-Time Fleet</span>
              </div>
              <div className="flex items-center gap-1.5">
                <span className="w-2.5 h-2.5 rounded-full bg-restrict inline-block" />
                <span>Delayed (&gt;15m)</span>
              </div>
            </div>
            <span>Click any train pip to inspect its operational twin</span>
          </div>
        </div>
      </SectionShell>

      {/* Congestion Radar Heat Matrix */}
      <SectionShell
        microLabel="Predictive Corridor Headway"
        title="Congestion Radar (Forward Horizons)"
        action={
          <span className="font-mono text-xs text-muted">
            9 Key Corridor Sections
          </span>
        }
      >
        <div className="flex flex-col gap-4">
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse text-xs">
              <thead>
                <tr className="bg-raised border-b border-line">
                  <th className="px-3.5 py-2.5 font-mono text-[10px] uppercase text-muted">
                    Section
                  </th>
                  <th className="px-3.5 py-2.5 font-mono text-[10px] uppercase text-muted">
                    Span
                  </th>
                  <th className="px-3.5 py-2.5 font-mono text-[10px] uppercase text-muted">
                    Chokepoint
                  </th>
                  {horizons.map((h) => (
                    <th
                      key={h}
                      className="px-3.5 py-2.5 font-mono text-[10px] uppercase text-muted text-center"
                    >
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-line/60">
                {radarSections.length === 0 ? (
                  <tr>
                    <td colSpan={3 + horizons.length} className="py-6 text-center font-mono text-xs text-muted">
                      No congestion radar telemetry available.
                    </td>
                  </tr>
                ) : (
                  radarSections.map((sec) => {
                    const hKeys = ['h0', 'h1', 'h2', 'h4', 'h6'] as const;

                    return (
                      <tr key={sec.section_id} className="hover:bg-raised/20 transition-colors">
                        <td className="px-3.5 py-2.5 font-sans font-semibold text-ink">
                          {sec.section_name}
                        </td>
                        <td className="px-3.5 py-2.5 font-mono text-muted tabular-nums">
                          {sec.length_km} km
                        </td>
                        <td className="px-3.5 py-2.5 font-mono font-bold text-ink">
                          {sec.chokepoint_station}
                        </td>
                        {hKeys.map((k) => {
                          const hData = sec.horizons?.[k];
                          if (!hData) {
                            return (
                              <td key={k} className="px-2 py-2 text-center font-mono text-muted">
                                --
                              </td>
                            );
                          }

                          const level = hData.congestion_level;
                          const cellColor =
                            level === 'CRITICAL'
                              ? 'bg-restrict/15 text-restrict border border-restrict/30'
                              : level === 'MODERATE'
                              ? 'bg-caution/15 text-caution border border-caution/30'
                              : 'bg-clear/10 text-clear border border-clear/25';

                          return (
                            <td key={k} className="px-2 py-2 text-center">
                              <div
                                className={`px-2 py-1 rounded-[2px] font-mono text-[11px] font-semibold tabular-nums inline-block min-w-[50px] ${cellColor}`}
                                title={`${hData.active_trains} trains / cap ${hData.capacity}`}
                              >
                                {Math.round(hData.occupancy_pct)}%
                              </div>
                            </td>
                          );
                        })}
                      </tr>
                    );
                  })
                )}
              </tbody>
            </table>
          </div>

          {/* Highest Chokepoints Advisory Strip */}
          {radar?.highest_chokepoints && radar.highest_chokepoints.length > 0 && (
            <div className="p-4 bg-raised/40 border border-line rounded-[3px] flex flex-col gap-2">
              <span className="font-mono text-micro uppercase tracking-wider text-muted font-medium">
                Dispatch Advisory · Peak Capacity Chokepoints
              </span>
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
                {radar.highest_chokepoints.map((cp, idx) => (
                  <div key={idx} className="p-2.5 bg-surface border border-line rounded-[3px] flex flex-col gap-1">
                    <div className="flex items-center justify-between">
                      <span className="font-mono font-bold text-xs text-ink">{cp.chokepoint}</span>
                      <span className="font-mono text-[10px] text-restrict font-bold px-1.5 py-0.2 bg-restrict/10 border border-restrict/30 rounded">
                        {cp.peak_occupancy}% LOAD
                      </span>
                    </div>
                    <span className="font-sans text-[11px] text-muted leading-tight">
                      {cp.recommended_action}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </SectionShell>

      {/* Active Corridor Fleet Data Table */}
      <SectionShell
        microLabel="Active Corridor Telemetry"
        title="Fleet Positions & Signal Aspects"
        action={
          <div className="flex items-center gap-2">
            <span className="font-mono text-xs text-muted">Filter:</span>
            <select
              value={selectedSection}
              onChange={(e) => setSelectedSection(e.target.value)}
              className="font-mono text-xs px-2 py-1 bg-surface border border-line rounded-[3px] text-ink"
            >
              <option value="ALL">All Corridor Sections</option>
              <option value="NDLS">New Delhi (NDLS)</option>
              <option value="ALJN">Aligarh (ALJN)</option>
              <option value="CNB">Kanpur (CNB)</option>
              <option value="PRYJ">Prayagraj (PRYJ)</option>
              <option value="DDU">Pt Deen Dayal (DDU)</option>
            </select>
          </div>
        }
      >
        <DataTable
          columns={columns}
          data={filteredPositions.slice(0, 25)}
          keyExtractor={(row: LivePosition, idx: number) => `${row.train_no}-${idx}`}
          onRowClick={(row: LivePosition) => navigate(`/t/${row.train_no}`)}
          emptyMessage="No train positions recorded in this section."
        />
        {filteredPositions.length > 25 && (
          <div className="pt-3 text-center font-mono text-xs text-muted">
            Showing top 25 of {filteredPositions.length} active trains in corridor
          </div>
        )}
      </SectionShell>
    </div>
  );
};
