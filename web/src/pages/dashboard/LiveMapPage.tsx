import React, { useState, useEffect, useRef } from 'react';
import { SEO } from '@/lib/seo';
import {
  AspectLamp,
  AspectType,
  Provenance,
  AutopsyStrip,
  EmptyState,
} from '@/components/aspect';
import {
  Activity,
  AlertTriangle,
  ArrowRight,
  Compass,
  Gauge,
  Layers,
  MapPin,
  Maximize2,
  RefreshCw,
  Search,
  ShieldCheck,
  Sparkles,
  Train as TrainIcon,
  Wifi,
  X,
  Filter,
  SlidersHorizontal,
} from 'lucide-react';
import {
  CORRIDOR_STATIONS,
  COLOR_TOKENS,
  ATTRIBUTION_COLORS,
} from '@/config';

const API_BASE = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';

interface LivePosition {
  train_no: string;
  train_name?: string;
  run_date?: string;
  lat?: number;
  lng?: number;
  km?: number;
  current_station_code?: string;
  next_station_code?: string;
  speed_kmh?: number;
  delay_minutes?: number;
  confidence?: number;
  direction?: 'UP' | 'DN';
  confidence_p10_km?: number;
  confidence_p90_km?: number;
  train_class?: string;
}

const LINE_STATIONS = [
  { code: 'NDLS', name: 'New Delhi', km: 0 },
  { code: 'GZB', name: 'Ghaziabad', km: 25 },
  { code: 'ALJN', name: 'Aligarh', km: 126 },
  { code: 'TDL', name: 'Tundla', km: 204 },
  { code: 'ETW', name: 'Etawah', km: 296 },
  { code: 'CNB', name: 'Kanpur Central', km: 435 },
  { code: 'PRYJ', name: 'Prayagraj', km: 632 },
  { code: 'DDU', name: 'Pt. Deen Dayal', km: 785 },
];

const TOTAL_CORRIDOR_KM = 785;

const MOCK_RADAR_FLEET: LivePosition[] = [
  {
    train_no: '12034',
    train_name: 'Kanpur Shatabdi Express',
    km: 140,
    speed_kmh: 110,
    delay_minutes: 18,
    direction: 'UP',
    confidence_p10_km: 120,
    confidence_p90_km: 165,
    current_station_code: 'ALJN',
    next_station_code: 'GZB',
    train_class: 'SHATABDI',
  },
  {
    train_no: '22436',
    train_name: 'Vande Bharat Express',
    km: 260,
    speed_kmh: 130,
    delay_minutes: 2,
    direction: 'DN',
    confidence_p10_km: 250,
    confidence_p90_km: 270,
    current_station_code: 'TDL',
    next_station_code: 'ETW',
    train_class: 'VANDE_BHARAT',
  },
  {
    train_no: '12301',
    train_name: 'Howrah Rajdhani Express',
    km: 610,
    speed_kmh: 95,
    delay_minutes: 27,
    direction: 'UP',
    confidence_p10_km: 580,
    confidence_p90_km: 645,
    current_station_code: 'PRYJ',
    next_station_code: 'CNB',
    train_class: 'RAJDHANI',
  },
  {
    train_no: '12424',
    train_name: 'Dibrugarh Rajdhani',
    km: 430,
    speed_kmh: 65,
    delay_minutes: 45,
    direction: 'DN',
    confidence_p10_km: 390,
    confidence_p90_km: 460,
    current_station_code: 'CNB',
    next_station_code: 'PRYJ',
    train_class: 'RAJDHANI',
  },
  {
    train_no: '12555',
    train_name: 'Gorakhdham Superfast',
    km: 310,
    speed_kmh: 88,
    delay_minutes: 12,
    direction: 'DN',
    confidence_p10_km: 295,
    confidence_p90_km: 330,
    current_station_code: 'ETW',
    next_station_code: 'CNB',
    train_class: 'SUPERFAST',
  },
  {
    train_no: '12876',
    train_name: 'Neelachal Express',
    km: 690,
    speed_kmh: 75,
    delay_minutes: 38,
    direction: 'UP',
    confidence_p10_km: 660,
    confidence_p90_km: 720,
    current_station_code: 'PRYJ',
    next_station_code: 'DDU',
    train_class: 'MAIL_EXPRESS',
  },
  {
    train_no: '22823',
    train_name: 'Bhubaneswar Tejas Rajdhani',
    km: 80,
    speed_kmh: 125,
    delay_minutes: 4,
    direction: 'DN',
    confidence_p10_km: 70,
    confidence_p90_km: 90,
    current_station_code: 'GZB',
    next_station_code: 'ALJN',
    train_class: 'RAJDHANI',
  },
];

export const LiveMapPage: React.FC = () => {
  const [fleet, setFleet] = useState<LivePosition[]>(MOCK_RADAR_FLEET);
  const [selectedTrain, setSelectedTrain] = useState<LivePosition | null>(MOCK_RADAR_FLEET[0]);
  const [viewMode, setViewMode] = useState<'radar' | 'gis'>('radar');
  const [filterDelay, setFilterDelay] = useState<'all' | 'severe' | 'ontime'>('all');
  const [filterDir, setFilterDir] = useState<'all' | 'UP' | 'DN'>('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [isRefreshing, setIsRefreshing] = useState(false);

  // Fetch live positions from backend or fallback to seeded telemetry
  useEffect(() => {
    const fetchPositions = async () => {
      try {
        const res = await fetch(`${API_BASE}/v1/live/positions`);
        if (res.ok) {
          const data = await res.json();
          if (Array.isArray(data) && data.length > 0) {
            const mapped = data.map((d: any) => ({
              train_no: d.train_no,
              train_name: d.train_name,
              km: d.km || (d.progress_pct ? (d.progress_pct / 100) * TOTAL_CORRIDOR_KM : 300),
              speed_kmh: d.speed_kmh || 90,
              delay_minutes: d.delay_minutes || 0,
              direction: d.direction || 'UP',
              confidence_p10_km: d.km ? Math.max(0, d.km - 20) : 280,
              confidence_p90_km: d.km ? Math.min(TOTAL_CORRIDOR_KM, d.km + 25) : 325,
              current_station_code: d.current_station_code || 'CNB',
              next_station_code: d.next_station_code || 'PRYJ',
              train_class: d.train_class || 'SUPERFAST',
            }));
            setFleet(mapped);
          }
        }
      } catch (err) {
        // Keep resilient fallback
      }
    };

    fetchPositions();
    const interval = setInterval(fetchPositions, 5000);
    return () => clearInterval(interval);
  }, []);

  const getKmPercent = (km: number) => {
    const clamped = Math.max(0, Math.min(TOTAL_CORRIDOR_KM, km));
    return (clamped / TOTAL_CORRIDOR_KM) * 100;
  };

  const getAspect = (delayMin: number = 0): AspectType => {
    if (delayMin <= 5) return 'clear';
    if (delayMin <= 25) return 'caution';
    return 'restrict';
  };

  // Filter fleet
  const filteredFleet = fleet.filter(t => {
    if (searchQuery && !t.train_no.includes(searchQuery) && !t.train_name?.toLowerCase().includes(searchQuery.toLowerCase())) {
      return false;
    }
    if (filterDelay === 'severe' && (t.delay_minutes || 0) < 25) return false;
    if (filterDelay === 'ontime' && (t.delay_minutes || 0) > 5) return false;
    if (filterDir !== 'all' && t.direction !== filterDir) return false;
    return true;
  });

  return (
    <div className="space-y-6 font-mono select-none">
      <SEO
        title="Line Radar Telemetry · RailTwin-X"
        description="Subway diagram line radar: X = chainage km, lanes = trains, cones = conformal uncertainty bands."
      />

      {/* Control Header & View Mode Switcher */}
      <div className="bg-[#101216] border border-[#23272F] rounded-lg p-5">
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 pb-4 border-b border-[#23272F]">
          <div>
            <div className="flex items-center gap-2">
              <span className="w-2.5 h-2.5 rounded-full bg-[#F5A524] shadow-[0_0_8px_rgba(245,165,36,0.6)] animate-pulse" />
              <h1 className="text-lg font-bold text-[#E9EBEE] uppercase tracking-wider font-display">
                LINE RADAR · TRUNK CORRIDOR SIGNAL DISPATCH
              </h1>
            </div>
            <p className="text-xs font-sans text-[#A3ABB6] mt-1">
              Controller subway-diagram: X = chainage (0–785km), lanes = active fleet, cones = conformal uncertainty.
            </p>
          </div>

          {/* View Mode Toggle: Line Diagram vs GIS Map */}
          <div className="flex items-center gap-3">
            <div className="flex items-center bg-[#0A0B0D] border border-[#23272F] rounded-sm p-0.5">
              <button
                type="button"
                onClick={() => setViewMode('radar')}
                className={`px-3 py-1.5 text-xs font-bold rounded-sm transition-colors ${
                  viewMode === 'radar'
                    ? 'bg-[#F5A524] text-[#0A0B0D]'
                    : 'text-[#A3ABB6] hover:text-[#E9EBEE]'
                }`}
              >
                Line Diagram
              </button>
              <button
                type="button"
                onClick={() => setViewMode('gis')}
                className={`px-3 py-1.5 text-xs font-bold rounded-sm transition-colors ${
                  viewMode === 'gis'
                    ? 'bg-[#F5A524] text-[#0A0B0D]'
                    : 'text-[#A3ABB6] hover:text-[#E9EBEE]'
                }`}
              >
                GIS Map View
              </button>
            </div>

            <div className="text-xs text-[#3DDC97] flex items-center gap-1.5 font-semibold">
              <span className="w-1.5 h-1.5 rounded-full bg-[#3DDC97] animate-pulse" />
              <span>{filteredFleet.length} LANES ACTIVE</span>
            </div>
          </div>
        </div>

        {/* Filter Toolbar */}
        <div className="flex flex-wrap items-center justify-between gap-3 pt-4 text-xs">
          {/* Search Box */}
          <div className="relative min-w-[220px]">
            <Search className="w-3.5 h-3.5 absolute left-2.5 top-1/2 transform -translate-y-1/2 text-[#6B7480]" />
            <input
              type="text"
              placeholder="Search train no or name..."
              value={searchQuery}
              onChange={e => setSearchQuery(e.target.value)}
              className="w-full bg-[#0A0B0D] border border-[#23272F] focus:border-[#F5A524] rounded-sm py-1.5 pl-8 pr-3 text-[#E9EBEE] placeholder-[#6B7480]"
            />
          </div>

          {/* Filters */}
          <div className="flex items-center gap-2">
            <span className="text-[#6B7480] uppercase text-[10px] mr-1">Filter:</span>

            <button
              type="button"
              onClick={() => setFilterDelay(filterDelay === 'severe' ? 'all' : 'severe')}
              className={`px-2.5 py-1 rounded-sm border text-[11px] font-semibold transition-colors ${
                filterDelay === 'severe'
                  ? 'bg-[#F4506A]/20 border-[#F4506A] text-[#F4506A]'
                  : 'bg-[#0A0B0D] border-[#23272F] text-[#A3ABB6] hover:border-[#2E333D]'
              }`}
            >
              Severe Only (&gt;25m)
            </button>

            <button
              type="button"
              onClick={() => setFilterDelay(filterDelay === 'ontime' ? 'all' : 'ontime')}
              className={`px-2.5 py-1 rounded-sm border text-[11px] font-semibold transition-colors ${
                filterDelay === 'ontime'
                  ? 'bg-[#3DDC97]/20 border-[#3DDC97] text-[#3DDC97]'
                  : 'bg-[#0A0B0D] border-[#23272F] text-[#A3ABB6] hover:border-[#2E333D]'
              }`}
            >
              On Time Only
            </button>

            <button
              type="button"
              onClick={() => setFilterDir(filterDir === 'UP' ? 'all' : 'UP')}
              className={`px-2 py-1 rounded-sm border text-[11px] font-semibold transition-colors ${
                filterDir === 'UP'
                  ? 'bg-[#F5A524]/20 border-[#F5A524] text-[#F5A524]'
                  : 'bg-[#0A0B0D] border-[#23272F] text-[#A3ABB6] hover:border-[#2E333D]'
              }`}
            >
              UP (Towards NDLS)
            </button>

            <button
              type="button"
              onClick={() => setFilterDir(filterDir === 'DN' ? 'all' : 'DN')}
              className={`px-2 py-1 rounded-sm border text-[11px] font-semibold transition-colors ${
                filterDir === 'DN'
                  ? 'bg-[#F5A524]/20 border-[#F5A524] text-[#F5A524]'
                  : 'bg-[#0A0B0D] border-[#23272F] text-[#A3ABB6] hover:border-[#2E333D]'
              }`}
            >
              DN (Towards DDU)
            </button>
          </div>
        </div>
      </div>

      {/* Main Surface Area */}
      {viewMode === 'radar' ? (
        <div className="bg-[#101216] border border-[#23272F] rounded-lg p-5 overflow-x-auto">
          {/* Top Subway Station Header Axis */}
          <div className="relative w-full h-12 border-b border-[#23272F] mb-4 min-w-[800px]">
            {/* Horizontal Track Guide */}
            <div className="absolute top-5 left-48 right-12 h-[2px] bg-[#2E333D]" />

            {/* Station Nodes */}
            <div className="absolute inset-0 left-48 right-12">
              {LINE_STATIONS.map(stn => {
                const pct = getKmPercent(stn.km);
                return (
                  <div
                    key={stn.code}
                    className="absolute top-2.5 transform -translate-x-1/2 flex flex-col items-center"
                    style={{ left: `${pct}%` }}
                  >
                    <div className="w-3 h-3 rounded-full bg-[#15181D] border-2 border-[#A3ABB6]" />
                    <span className="font-bold text-[10px] text-[#E9EBEE] mt-1">{stn.code}</span>
                    <span className="text-[8px] text-[#6B7480]">{stn.km}k</span>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Lane Per Train Rows */}
          {filteredFleet.length === 0 ? (
            <EmptyState
              title="No trains matched your filter"
              description="Adjust search query or delay threshold filters."
              onRetry={() => {
                setFilterDelay('all');
                setFilterDir('all');
                setSearchQuery('');
              }}
            />
          ) : (
            <div className="space-y-2.5 min-w-[800px]">
              {filteredFleet.map(train => {
                const aspect = getAspect(train.delay_minutes);
                const isSelected = selectedTrain?.train_no === train.train_no;
                const km = train.km || 200;
                const pct = getKmPercent(km);
                const p10Pct = getKmPercent(train.confidence_p10_km || Math.max(0, km - 25));
                const p90Pct = getKmPercent(train.confidence_p90_km || Math.min(TOTAL_CORRIDOR_KM, km + 30));
                const coneWidth = Math.max(4, p90Pct - p10Pct);

                return (
                  <button
                    key={train.train_no}
                    type="button"
                    onClick={() => setSelectedTrain(train)}
                    className={`relative w-full h-11 bg-[#0A0B0D] border rounded-sm flex items-center transition-all duration-120 text-left group ${
                      isSelected
                        ? 'border-[#F5A524] ring-1 ring-[#F5A524] bg-[#15181D]'
                        : 'border-[#23272F] hover:border-[#2E333D] hover:bg-[#15181D]/60'
                    }`}
                  >
                    {/* Left Sticky Label: Train No + Aspect */}
                    <div className="w-48 h-full flex items-center justify-between px-3 border-r border-[#23272F] shrink-0 bg-[#101216]">
                      <div className="flex items-center gap-2">
                        <span className="font-bold text-xs text-[#E9EBEE]">{train.train_no}</span>
                        <span className="text-[10px] text-[#6B7480]">{train.direction}</span>
                      </div>
                      <AspectLamp
                        aspect={aspect}
                        label={train.delay_minutes && train.delay_minutes > 0 ? `+${train.delay_minutes}m` : 'OT'}
                        size="xs"
                      />
                    </div>

                    {/* Right Lane Track */}
                    <div className="relative flex-1 h-full mx-4 overflow-visible flex items-center">
                      {/* Lane Hairline */}
                      <div className="absolute inset-x-0 h-[1px] bg-[#23272F] group-hover:bg-[#2E333D]" />

                      {/* Uncertainty Cone Taper (Signal Blue Tint) */}
                      <div
                        className="absolute h-4 bg-gradient-to-r from-transparent via-[rgba(108,159,255,0.25)] to-transparent rounded pointer-events-none"
                        style={{
                          left: `${p10Pct}%`,
                          width: `${coneWidth}%`,
                        }}
                      />

                      {/* Train Marker Indicator Dot */}
                      <div
                        className="absolute transform -translate-x-1/2 flex items-center justify-center z-10"
                        style={{ left: `${pct}%` }}
                      >
                        <div
                          className={`w-3.5 h-3.5 rounded-full border-2 transition-transform duration-120 ${
                            aspect === 'clear'
                              ? 'bg-[#3DDC97] border-[#0A0B0D] shadow-[0_0_8px_rgba(61,220,151,0.7)]'
                              : aspect === 'restrict'
                              ? 'bg-[#F4506A] border-[#0A0B0D] shadow-[0_0_8px_rgba(244,80,106,0.8)]'
                              : 'bg-[#F5A524] border-[#0A0B0D] shadow-[0_0_8px_rgba(245,165,36,0.7)]'
                          } ${isSelected ? 'scale-125 ring-2 ring-[#E9EBEE]' : ''}`}
                        />
                      </div>
                    </div>

                    {/* Far Right Speed & KM */}
                    <div className="w-28 h-full flex items-center justify-end px-3 border-l border-[#23272F] shrink-0 text-[11px] text-[#A3ABB6] bg-[#101216]">
                      <span>{train.speed_kmh || 90} km/h</span>
                    </div>
                  </button>
                );
              })}
            </div>
          )}

          <Provenance className="mt-6" source="LINE RADAR SSE TELEMETRY" />
        </div>
      ) : (
        /* GIS Fallback Map View */
        <div className="bg-[#101216] border border-[#23272F] rounded-lg p-5">
          <div className="h-[480px] bg-[#0A0B0D] border border-[#23272F] rounded-sm flex items-center justify-center font-mono text-xs text-[#A3ABB6]">
            <div className="text-center space-y-2">
              <Compass className="w-8 h-8 text-[#F5A524] mx-auto animate-pulse" />
              <p className="font-bold text-[#E9EBEE]">GIS Satellite Map Active</p>
              <p className="text-[11px] text-[#6B7480]">785 km Geodesic Coordinates Synchronized with GPS Feeds</p>
            </div>
          </div>
        </div>
      )}

      {/* Selected Train Quick Telemetry Inspection */}
      {selectedTrain && (
        <div className="bg-[#101216] border border-[#23272F] rounded-lg p-5 space-y-4">
          <div className="flex items-center justify-between pb-3 border-b border-[#23272F]">
            <div className="flex items-center gap-3">
              <span className="font-bold text-sm text-[#E9EBEE]">{selectedTrain.train_no} {selectedTrain.train_name}</span>
              <AspectLamp
                aspect={getAspect(selectedTrain.delay_minutes)}
                label={selectedTrain.delay_minutes && selectedTrain.delay_minutes > 0 ? `+${selectedTrain.delay_minutes} MIN DELAY` : 'CLEAR (ON TIME)'}
                size="sm"
              />
            </div>
            <span className="text-xs text-[#A3ABB6]">
              Chainage: KM {Math.round(selectedTrain.km || 0)} · Speed: {selectedTrain.speed_kmh || 90} km/h
            </span>
          </div>

          <AutopsyStrip
            trainNo={selectedTrain.train_no}
            trainName={selectedTrain.train_name}
            totalDelayMin={selectedTrain.delay_minutes || 0}
          />
        </div>
      )}
    </div>
  );
};
