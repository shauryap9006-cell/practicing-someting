import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../lib/api';
import type { PopularTrain } from '../lib/types';
import { SectionShell, StatCard, LoadingState, ErrorState } from '../primitives';

export const TrainSearchPage: React.FC = () => {
  const navigate = useNavigate();
  const [trains, setTrains] = useState<PopularTrain[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedType, setSelectedType] = useState<string>('ALL');

  const fetchFleet = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.passenger.popular();
      setTrains(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to query corridor train fleet.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchFleet();
  }, []);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const clean = searchQuery.trim();
    if (clean) {
      navigate(`/t/${clean}`);
    }
  };

  const trainTypes = ['ALL', 'RAJDHANI', 'SHATABDI', 'SUPERFAST'];

  const filteredTrains = trains.filter((t) => {
    const matchesQuery =
      t.train_no.includes(searchQuery.trim()) ||
      t.name.toLowerCase().includes(searchQuery.toLowerCase().trim()) ||
      (t.route_short && t.route_short.toLowerCase().includes(searchQuery.toLowerCase().trim()));

    if (!matchesQuery) return false;
    if (selectedType === 'ALL') return true;
    return t.type?.toUpperCase().includes(selectedType) || t.name.toUpperCase().includes(selectedType);
  });

  return (
    <div className="max-w-6xl mx-auto w-full p-4 sm:p-6 lg:p-8 flex flex-col gap-6">
      {/* Masthead Header */}
      <div className="flex flex-col gap-1 border-b border-line/60 pb-5">
        <div className="flex items-center gap-2">
          <span className="w-2.5 h-2.5 rounded-[2px] bg-ink" />
          <span className="font-mono text-micro uppercase tracking-wider text-muted font-medium">
            Dynamic Working Timetable · PS 26028
          </span>
        </div>
        <h1 className="font-serif text-3xl sm:text-4xl font-bold tracking-tight text-ink">
          Corridor Fleet & Train Tracker
        </h1>
        <p className="font-sans text-sm text-ink/75 max-w-2xl">
          Live probabilistic ETA forecasting and root-cause delay attribution across
          the New Delhi — Howrah Main Trunk Corridor. Select an active service or enter a train number.
        </p>
      </div>

      {/* Network Overview Stats */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <StatCard
          label="Corridor Fleet"
          value={trains.length > 0 ? `${trains.length} Services` : '--'}
          subtext="Main line active fleet"
        />
        <StatCard
          label="Dynamic Engine"
          value="P10 — P90"
          subtext="Interval forecasting"
          deltaType="positive"
        />
        <StatCard
          label="Attribution"
          value="100% Additive"
          subtext="Zero unexplained drift"
        />
        <StatCard
          label="Cryptographic Proof"
          value="SHA-256"
          subtext="Append-only ledger"
        />
      </div>

      {/* Prominent Search Bar */}
      <form onSubmit={handleSearchSubmit} className="flex flex-col sm:flex-row gap-2">
        <div className="relative flex-1">
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Enter train number or name (e.g. 12301, 12003, Rajdhani)..."
            className="w-full h-12 px-4 bg-surface border border-line rounded-[4px] font-mono text-sm sm:text-base text-ink placeholder:text-muted focus:outline-none focus:border-ink transition-colors"
          />
          <div className="absolute right-3 top-3.5 hidden sm:flex items-center gap-1 font-mono text-[10px] text-muted border border-line/60 rounded px-1.5 py-0.5 bg-raised">
            <span>PRESS ENTER ↵</span>
          </div>
        </div>
        <button
          type="submit"
          className="h-12 px-6 bg-ink text-surface font-mono text-xs uppercase tracking-wider rounded-[4px] hover:bg-ink/90 transition-colors font-medium cursor-pointer"
        >
          Track Service →
        </button>
      </form>

      {/* Type Filter Pills */}
      <div className="flex items-center gap-2 overflow-x-auto pb-1">
        <span className="font-mono text-[11px] uppercase tracking-wider text-muted font-medium mr-1">
          Filter:
        </span>
        {trainTypes.map((type) => (
          <button
            key={type}
            type="button"
            onClick={() => setSelectedType(type)}
            className={`font-mono text-xs px-3 py-1.5 rounded-[3px] border transition-colors cursor-pointer ${
              selectedType === type
                ? 'bg-ink text-surface border-ink font-semibold'
                : 'bg-surface text-ink border-line hover:bg-raised'
            }`}
          >
            {type === 'ALL' ? 'ALL SERVICES' : type}
          </button>
        ))}
      </div>

      {/* Fleet Table / Listing */}
      {loading ? (
        <LoadingState rows={5} message="Loading corridor fleet telemetry..." />
      ) : error ? (
        <ErrorState
          title="Fleet Telemetry Sync Error"
          message={error}
          onRetry={fetchFleet}
        />
      ) : filteredTrains.length === 0 ? (
        <SectionShell className="p-8 text-center">
          <p className="font-mono text-xs text-muted">
            No active trains found matching query &ldquo;{searchQuery}&rdquo;.
          </p>
          <div className="pt-3">
            <button
              type="button"
              onClick={() => navigate(`/t/${searchQuery.trim()}`)}
              className="font-mono text-xs text-ink underline"
            >
              Force inspect train #{searchQuery.trim()} →
            </button>
          </div>
        </SectionShell>
      ) : (
        <SectionShell
          microLabel="Active Corridor Fleet"
          title="Scheduled & Active Services"
          action={
            <span className="font-mono text-xs text-muted">
              {filteredTrains.length} {filteredTrains.length === 1 ? 'train' : 'trains'} listed
            </span>
          }
        >
          <div className="divide-y divide-line/60 -mx-4 -my-4">
            {filteredTrains.map((train) => {
              const delay = train.delay_min ?? 0;
              const isLate = delay > 5;
              const isEarly = delay < 0;

              return (
                <div
                  key={train.train_no}
                  onClick={() => navigate(`/t/${train.train_no}`)}
                  className="p-4 sm:p-5 flex flex-col sm:flex-row sm:items-center justify-between gap-3 hover:bg-raised/40 transition-colors cursor-pointer"
                >
                  <div className="flex items-start sm:items-center gap-3">
                    <span className="font-mono text-base font-bold text-ink px-2.5 py-1 bg-surface border border-line rounded-[3px] tabular-nums shrink-0">
                      #{train.train_no}
                    </span>
                    <div className="flex flex-col gap-0.5">
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="font-serif text-base font-semibold text-ink leading-tight">
                          {train.name}
                        </span>
                        {train.type && (
                          <span className="font-mono text-[9px] uppercase px-1.5 py-0.5 bg-raised border border-line rounded-[2px] text-muted font-medium">
                            {train.type}
                          </span>
                        )}
                      </div>
                      {train.route_short && (
                        <span className="font-mono text-xs text-muted">
                          {train.route_short}
                        </span>
                      )}
                    </div>
                  </div>

                  <div className="flex items-center justify-between sm:justify-end gap-4 pl-12 sm:pl-0">
                    {train.next_departure && (
                      <div className="flex flex-col items-end text-right hidden sm:flex">
                        <span className="font-mono text-[10px] uppercase text-muted">
                          Next Departure
                        </span>
                        <span className="font-mono text-xs text-ink tabular-nums">
                          {train.next_departure}
                        </span>
                      </div>
                    )}

                    <div className="flex items-center gap-2">
                      <span
                        className={`font-mono text-xs px-2.5 py-1 rounded-[3px] border font-medium tabular-nums ${
                          isLate
                            ? 'bg-restrict/10 border-restrict/30 text-restrict'
                            : isEarly
                            ? 'bg-clear/10 border-clear/30 text-clear'
                            : 'bg-clear/10 border-clear/30 text-clear'
                        }`}
                      >
                        {isLate ? `+${delay}m Late` : isEarly ? `${delay}m Early` : 'Right Time'}
                      </span>
                      <span className="font-mono text-xs text-muted">→</span>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </SectionShell>
      )}
    </div>
  );
};
