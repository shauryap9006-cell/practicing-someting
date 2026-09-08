import React, { useState, useMemo, useRef, useEffect } from 'react';
import type { LivePosition, NetworkState, StationMeta } from '@railtwin/shared-types';
import { NATIONAL_CORRIDORS } from '../lib/corridors';

export interface CorridorDef {
  id: string;
  name: string;
  code: string;
  zone: string;
  stationCodes: string[];
}

export const MAJOR_CORRIDORS: CorridorDef[] = NATIONAL_CORRIDORS.map((c) => ({
  id: c.id,
  name: c.name,
  code: `${c.stations[0].code}-${c.stations[c.stations.length - 1].code} (${c.totalKm}km)`,
  zone: c.shortName,
  stationCodes: c.stations.map((s) => s.code),
}));

interface SearchBarProps {
  positions: LivePosition[];
  network: NetworkState | null;
  stations: StationMeta[];
  onSelectTrain: (trainNo: string) => void;
  onSelectStation: (stationCode: string) => void;
  onSelectCorridor: (corridorId: string) => void;
}

export const SearchBar: React.FC<SearchBarProps> = ({
  positions,
  network,
  stations,
  onSelectTrain,
  onSelectStation,
  onSelectCorridor,
}) => {
  const [query, setQuery] = useState('');
  const [isOpen, setIsOpen] = useState(false);
  const [activeTab, setActiveTab] = useState<'ALL' | 'TRAINS' | 'STATIONS' | 'CORRIDORS'>('ALL');
  const [selectedIndex, setSelectedIndex] = useState<number>(0);
  const dropdownRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  // Map of train numbers to detailed info
  const trainDetailMap = useMemo(() => {
    const map = new Map<string, { name: string; class: string; delay: number }>();
    if (network?.trains) {
      for (const t of network.trains) {
        map.set(t.train_no, {
          name: t.train_name,
          class: t.train_class,
          delay: t.current_delay_min,
        });
      }
    }
    return map;
  }, [network]);

  // Filtered lists based on query
  const searchResults = useMemo(() => {
    const q = query.trim().toUpperCase();
    if (!q) {
      // Default suggested items
      return {
        trains: (positions.slice(0, 5) || []).map((p) => {
          const detail = trainDetailMap.get(p.train_no);
          return {
            type: 'TRAIN' as const,
            id: p.train_no,
            title: `#${p.train_no}`,
            subtitle: detail?.name || `Speed: ${Math.round(p.speed_kmh)} km/h`,
            meta: p.current_station_code ? `@ ${p.current_station_code}` : p.next_station_code ? `-> ${p.next_station_code}` : 'En Route',
            delay: p.delay_minutes,
          };
        }),
        stations: stations.slice(0, 6).map((s) => ({
          type: 'STATION' as const,
          id: s.code,
          title: s.code,
          subtitle: s.name,
          meta: `${s.platforms || 2} PF`,
        })),
        corridors: MAJOR_CORRIDORS.slice(0, 4).map((c) => ({
          type: 'CORRIDOR' as const,
          id: c.id,
          title: c.name,
          subtitle: c.zone,
          meta: c.code,
        })),
      };
    }

    // Search Trains
    const matchedTrains = positions
      .filter((p) => {
        const detail = trainDetailMap.get(p.train_no);
        const nameMatch = detail?.name ? detail.name.toUpperCase().includes(q) : false;
        const noMatch = p.train_no.toUpperCase().includes(q);
        return noMatch || nameMatch;
      })
      .slice(0, 10)
      .map((p) => {
        const detail = trainDetailMap.get(p.train_no);
        return {
          type: 'TRAIN' as const,
          id: p.train_no,
          title: `#${p.train_no}`,
          subtitle: detail?.name || `Speed: ${Math.round(p.speed_kmh)} km/h`,
          meta: p.current_station_code ? `@ ${p.current_station_code}` : p.next_station_code ? `-> ${p.next_station_code}` : 'En Route',
          delay: p.delay_minutes,
        };
      });

    // Search Stations
    const matchedStations = stations
      .filter((s) => s.code.toUpperCase().includes(q) || s.name.toUpperCase().includes(q))
      .slice(0, 8)
      .map((s) => ({
        type: 'STATION' as const,
        id: s.code,
        title: s.code,
        subtitle: s.name,
        meta: `${s.platforms || 2} PF`,
      }));

    // Search Corridors
    const matchedCorridors = MAJOR_CORRIDORS.filter(
      (c) => c.name.toUpperCase().includes(q) || c.id.toUpperCase().includes(q) || c.zone.toUpperCase().includes(q)
    ).map((c) => ({
      type: 'CORRIDOR' as const,
      id: c.id,
      title: c.name,
      subtitle: c.zone,
      meta: c.code,
    }));

    return {
      trains: matchedTrains,
      stations: matchedStations,
      corridors: matchedCorridors,
    };
  }, [query, positions, stations, trainDetailMap]);

  // Flatten based on activeTab
  const flatResults = useMemo(() => {
    if (activeTab === 'TRAINS') return searchResults.trains;
    if (activeTab === 'STATIONS') return searchResults.stations;
    if (activeTab === 'CORRIDORS') return searchResults.corridors;
    return [...searchResults.trains, ...searchResults.stations, ...searchResults.corridors];
  }, [activeTab, searchResults]);

  // Click outside to close
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleSelect = (item: { type: 'TRAIN' | 'STATION' | 'CORRIDOR'; id: string }) => {
    if (item.type === 'TRAIN') {
      onSelectTrain(item.id);
    } else if (item.type === 'STATION') {
      onSelectStation(item.id);
    } else if (item.type === 'CORRIDOR') {
      onSelectCorridor(item.id);
    }
    setIsOpen(false);
    setQuery('');
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setSelectedIndex((prev) => (prev + 1) % Math.max(1, flatResults.length));
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setSelectedIndex((prev) => (prev - 1 + flatResults.length) % Math.max(1, flatResults.length));
    } else if (e.key === 'Enter') {
      e.preventDefault();
      const item = flatResults[selectedIndex];
      if (item) handleSelect(item);
    } else if (e.key === 'Escape') {
      setIsOpen(false);
    }
  };

  return (
    <div className="header-search-container" ref={dropdownRef}>
      <div className="header-search-input-wrap">
        {/* Minimal Search SVG Icon */}
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="var(--text-dim)" strokeWidth="2">
          <circle cx="11" cy="11" r="8" />
          <line x1="21" y1="21" x2="16.65" y2="16.65" />
        </svg>

        <input
          ref={inputRef}
          type="text"
          className="header-search-input"
          placeholder="Search train (12004), station (NDLS), corridor..."
          value={query}
          onChange={(e) => {
            setQuery(e.target.value);
            setIsOpen(true);
            setSelectedIndex(0);
          }}
          onFocus={() => setIsOpen(true)}
          onKeyDown={handleKeyDown}
        />

        {query && (
          <button className="search-clear-btn" onClick={() => setQuery('')} title="Clear search">
            x
          </button>
        )}
      </div>

      {/* Instant Filter Dropdown */}
      {isOpen && (
        <div className="search-results-dropdown">
          {/* Filter Tabs */}
          <div className="search-tabs-row">
            {(['ALL', 'TRAINS', 'STATIONS', 'CORRIDORS'] as const).map((tab) => (
              <button
                key={tab}
                className={`search-tab-pill ${activeTab === tab ? 'active' : ''}`}
                onClick={() => {
                  setActiveTab(tab);
                  setSelectedIndex(0);
                }}
              >
                {tab}
              </button>
            ))}
          </div>

          {/* Render Results */}
          {flatResults.length === 0 ? (
            <div style={{ padding: '16px', textAlign: 'center', color: 'var(--text-dim)', fontSize: '11px', fontFamily: 'var(--font-mono)' }}>
              NO MATCHES FOR "{query.toUpperCase()}"
            </div>
          ) : (
            <div>
              {/* Trains Group */}
              {(activeTab === 'ALL' || activeTab === 'TRAINS') && searchResults.trains.length > 0 && (
                <div className="search-category-group">
                  <div className="search-group-title">TRAINS ({searchResults.trains.length})</div>
                  {searchResults.trains.map((t, idx) => {
                    const isSelected = flatResults[selectedIndex]?.id === t.id && flatResults[selectedIndex]?.type === 'TRAIN';
                    return (
                      <div
                        key={`t-${t.id}-${idx}`}
                        className={`search-result-row ${isSelected ? 'selected' : ''}`}
                        onClick={() => handleSelect(t)}
                      >
                        <div className="search-result-primary">
                          <span className="search-badge-type">TRAIN</span>
                          <span className="search-code">{t.title}</span>
                          <span className="search-name">{t.subtitle}</span>
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                          {t.delay !== undefined && (
                            <span
                              style={{
                                color: t.delay <= 5 ? 'var(--signal-green)' : t.delay <= 20 ? 'var(--signal-amber)' : 'var(--signal-red)',
                                fontSize: '10px',
                                fontWeight: 700,
                              }}
                            >
                              {t.delay > 0 ? `+${t.delay}m` : '0m'}
                            </span>
                          )}
                          <span className="search-meta-tag">{t.meta}</span>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}

              {/* Stations Group */}
              {(activeTab === 'ALL' || activeTab === 'STATIONS') && searchResults.stations.length > 0 && (
                <div className="search-category-group">
                  <div className="search-group-title">STATIONS ({searchResults.stations.length})</div>
                  {searchResults.stations.map((s, idx) => {
                    const isSelected = flatResults[selectedIndex]?.id === s.id && flatResults[selectedIndex]?.type === 'STATION';
                    return (
                      <div
                        key={`s-${s.id}-${idx}`}
                        className={`search-result-row ${isSelected ? 'selected' : ''}`}
                        onClick={() => handleSelect(s)}
                      >
                        <div className="search-result-primary">
                          <span className="search-badge-type" style={{ color: 'var(--ochre)' }}>
                            STN
                          </span>
                          <span className="search-code">{s.title}</span>
                          <span className="search-name">{s.subtitle}</span>
                        </div>
                        <span className="search-meta-tag">{s.meta}</span>
                      </div>
                    );
                  })}
                </div>
              )}

              {/* Corridors Group */}
              {(activeTab === 'ALL' || activeTab === 'CORRIDORS') && searchResults.corridors.length > 0 && (
                <div className="search-category-group">
                  <div className="search-group-title">CORRIDORS ({searchResults.corridors.length})</div>
                  {searchResults.corridors.map((c, idx) => {
                    const isSelected = flatResults[selectedIndex]?.id === c.id && flatResults[selectedIndex]?.type === 'CORRIDOR';
                    return (
                      <div
                        key={`c-${c.id}-${idx}`}
                        className={`search-result-row ${isSelected ? 'selected' : ''}`}
                        onClick={() => handleSelect(c)}
                      >
                        <div className="search-result-primary">
                          <span className="search-badge-type" style={{ color: 'var(--signal-amber)' }}>
                            ROUTE
                          </span>
                          <span className="search-code">{c.title}</span>
                        </div>
                        <span className="search-meta-tag">{c.meta}</span>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
};
export default SearchBar;
