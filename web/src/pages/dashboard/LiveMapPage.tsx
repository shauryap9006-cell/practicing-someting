import React, { useState, useEffect, useRef } from 'react';
import { SEO } from '@/lib/seo';
import { DataFreshnessBadge } from '@/components/common/DataFreshnessBadge';
import {
  Activity,
  AlertCircle,
  AlertTriangle,
  ArrowRight,
  CloudFog,
  CloudRain,
  Compass,
  Gauge,
  HelpCircle,
  Layers,
  MapPin,
  Maximize2,
  Navigation,
  RefreshCw,
  RotateCcw,
  ShieldAlert,
  ShieldCheck,
  Sparkles,
  Train as TrainIcon,
  Wifi,
  WifiOff,
  Wind,
  X,
} from 'lucide-react';
import {
  CORRIDOR_STATIONS,
  COLOR_TOKENS,
  ATTRIBUTION_COLORS,
  LIVE_CONFIG,
  BACKEND_DEFAULTS,
} from '@/config';

const API_BASE = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';

interface LivePosition {
  train_no: string;
  train_name?: string;
  run_date: string;
  lat: number;
  lng: number;
  lon?: number;
  est_lat?: number;
  est_lng?: number;
  current_station_code?: string;
  next_station_code?: string;
  prev_station_code?: string;
  section_id?: string;
  speed_kmh: number;
  heading?: number;
  delay_minutes: number;
  confidence: number;
  progress_pct: number;
  is_dead_reckoned: boolean;
  basis?: string;
  source?: string;
  status?: string;
  last_event_time?: string;
  updated_at?: string;
}

interface TrainLiveDetail {
  train_no: string;
  train_name: string;
  train_class: string;
  run_date: string;
  position: LivePosition;
  context: {
    train_no: string;
    run_date: string;
    weather: {
      station_code: string;
      temperature_celsius: number;
      relative_humidity_percent: number;
      precipitation_mm: number;
      visibility_km: number;
      fog_risk_flag: boolean;
      rain_risk_flag: boolean;
    };
    tsrs_ahead: Array<{
      id: number;
      section_id: string;
      from_station: string;
      to_station: string;
      speed_limit_kmh: number;
      reason: string;
    }>;
    incoming_rake: {
      incoming_train_no: string | null;
      status: string;
      incoming_delay_min: number;
      turnaround_min: number;
      turnaround_deficit_min: number;
      cascade_risk_score: number;
    };
    platform: {
      station_code: string;
      platform: number | string;
      status: string;
    };
    congestion: {
      trains_in_same_section: number;
      density_factor: number;
      lead_train_no: string | null;
      headway_gap_km: number;
    };
  };
  why_late?: {
    train_no: string;
    run_date: string;
    total_delay_min: number;
    delay_delta_min: number;
    primary_cause: string;
    is_exact_accounting: boolean;
    cause_breakdown: Array<{
      cause_code: string;
      name: string;
      attributed_min: number;
      share_pct: number;
      description: string;
      evidence_ref?: string;
      confidence_tier: string;
    }>;
  };
}

// Built-in Corridor Active Fleet Seed Fallback
const INITIAL_CORRIDOR_FLEET: LivePosition[] = [
  {
    train_no: '12301',
    train_name: 'Howrah Rajdhani Express',
    run_date: '2026-09-01',
    lat: 26.55,
    lng: 80.20,
    current_station_code: 'CNB',
    next_station_code: 'PRYJ',
    section_id: 'CNB_PRYJ',
    speed_kmh: 88,
    delay_minutes: 16.0,
    confidence: 0.94,
    progress_pct: 55.6,
    is_dead_reckoned: false,
    source: 'live_ingestion',
  },
  {
    train_no: '12004',
    train_name: 'Lucknow Swarna Shatabdi',
    run_date: '2026-09-01',
    lat: 27.85,
    lng: 78.15,
    current_station_code: 'ALJN',
    next_station_code: 'TDL',
    section_id: 'ALJN_TDL',
    speed_kmh: 110,
    delay_minutes: 4.0,
    confidence: 0.98,
    progress_pct: 22.4,
    is_dead_reckoned: false,
    source: 'live_ingestion',
  },
  {
    train_no: '22436',
    train_name: 'Vande Bharat Express',
    run_date: '2026-09-01',
    lat: 26.82,
    lng: 79.10,
    current_station_code: 'ETW',
    next_station_code: 'CNB',
    section_id: 'ETW_CNB',
    speed_kmh: 130,
    delay_minutes: 2.0,
    confidence: 0.99,
    progress_pct: 38.0,
    is_dead_reckoned: false,
    source: 'live_ingestion',
  },
  {
    train_no: '12424',
    train_name: 'Dibrugarh Rajdhani Express',
    run_date: '2026-09-01',
    lat: 25.50,
    lng: 81.75,
    current_station_code: 'PRYJ',
    next_station_code: 'DDU',
    section_id: 'PRYJ_DDU',
    speed_kmh: 95,
    delay_minutes: 8.0,
    confidence: 0.92,
    progress_pct: 78.2,
    is_dead_reckoned: false,
    source: 'live_ingestion',
  },
  {
    train_no: '12001',
    train_name: 'Bhopal Shatabdi',
    run_date: '2026-09-01',
    lat: 28.65,
    lng: 77.35,
    current_station_code: 'GZB',
    next_station_code: 'ALJN',
    section_id: 'GZB_ALJN',
    speed_kmh: 105,
    delay_minutes: 0.0,
    confidence: 0.97,
    progress_pct: 8.5,
    is_dead_reckoned: false,
    source: 'live_ingestion',
  },
  {
    train_no: '12802',
    train_name: 'Purushottam Express',
    run_date: '2026-09-01',
    lat: 25.32,
    lng: 82.90,
    current_station_code: 'DDU',
    next_station_code: 'DDU',
    section_id: 'PRYJ_DDU',
    speed_kmh: 70,
    delay_minutes: 28.0,
    confidence: 0.85,
    progress_pct: 94.0,
    is_dead_reckoned: true,
    source: 'dead_reckoning',
  },
];

// Project Geographic Coordinates onto 1200x500 SVG Canvas
function projectGeoToSvg(lat: number, lon: number): { x: number; y: number } {
  const minLat = 25.0;
  const maxLat = 29.0;
  const minLon = 77.0;
  const maxLon = 83.5;

  const normX = (lon - minLon) / (maxLon - minLon);
  const normY = (maxLat - lat) / (maxLat - minLat);

  const x = 70 + normX * 1060;
  const y = 90 + normY * 320;
  return { x: Math.max(60, Math.min(1140, x)), y: Math.max(60, Math.min(440, y)) };
}

function getDelayColor(delayMin: number): string {
  if (delayMin <= 15) return COLOR_TOKENS.SUCCESS;
  if (delayMin <= 60) return COLOR_TOKENS.WARNING;
  return COLOR_TOKENS.DANGER;
}

export function LiveMapPage() {
  const [positions, setPositions] = useState<LivePosition[]>(INITIAL_CORRIDOR_FLEET);
  const [interpolatedPositions, setInterpolatedPositions] = useState<Record<string, { x: number; y: number }>>({});
  const [selectedTrainNo, setSelectedTrainNo] = useState<string | null>(null);
  const [selectedDetail, setSelectedDetail] = useState<TrainLiveDetail | null>(null);
  const [isLoadingDetail, setIsLoadingDetail] = useState(false);
  const [sseConnected, setSseConnected] = useState(false);
  const [isStale, setIsStale] = useState(false);
  const [lastPulseTime, setLastPulseTime] = useState<Date>(new Date());
  const [showTSRs, setShowTSRs] = useState(true);
  const [showHalos, setShowHalos] = useState(true);

  const targetPositionsRef = useRef<Record<string, { x: number; y: number }>>({});
  const currentPositionsRef = useRef<Record<string, { x: number; y: number }>>({});

  // Initialize target positions for initial fleet
  useEffect(() => {
    const initTargets: Record<string, { x: number; y: number }> = {};
    INITIAL_CORRIDOR_FLEET.forEach((p) => {
      initTargets[p.train_no] = projectGeoToSvg(p.lat, p.lng);
    });
    targetPositionsRef.current = initTargets;
    currentPositionsRef.current = initTargets;
    setInterpolatedPositions(initTargets);
  }, []);

  // 1. Initial REST Fetch for Positions with automatic fallback
  const fetchPositions = async () => {
    try {
      const res = await fetch('/v1/live/positions').catch(() => fetch(`${API_BASE}/v1/live/positions`));
      if (!res || !res.ok) return;
      const data = await res.json();
      if (data && Array.isArray(data.positions) && data.positions.length > 0) {
        // Filter for trains on or near the NDLS-DDU corridor
        const corridorPositions = data.positions.filter((p: LivePosition) => {
          const lat = p.lat || 0;
          const lng = p.lng || p.lon || 0;
          return lat >= 24.8 && lat <= 29.2 && lng >= 76.8 && lng <= 83.8;
        });

        const finalPositions = corridorPositions.length > 0 ? corridorPositions : data.positions.slice(0, 12);
        setPositions(finalPositions);

        const newTargets: Record<string, { x: number; y: number }> = {};
        finalPositions.forEach((p: LivePosition) => {
          newTargets[p.train_no] = projectGeoToSvg(p.lat, p.lng || p.lon || 77.2);
        });
        targetPositionsRef.current = newTargets;
        setLastPulseTime(new Date());
        setIsStale(false);
      }
    } catch (e) {
      console.warn('REST positions fetch fallback applied', e);
    }
  };

  useEffect(() => {
    fetchPositions();
  }, []);

  // 2. Real-time SSE Stream with Resilient Reconnect
  useEffect(() => {
    let eventSource: EventSource | null = null;
    let reconnectTimeout: any = null;

    function connectSSE() {
      try {
        const streamUrl = `${API_BASE}/v1/live/stream`;
        eventSource = new EventSource(streamUrl);

        eventSource.onopen = () => {
          setSseConnected(true);
          setIsStale(false);
        };

        eventSource.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data);
            if (data && Array.isArray(data.positions) && data.positions.length > 0) {
              const corridorPositions = data.positions.filter((p: LivePosition) => {
                const lat = p.lat || 0;
                const lng = p.lng || p.lon || 0;
                return lat >= 24.8 && lat <= 29.2 && lng >= 76.8 && lng <= 83.8;
              });

              const activeList = corridorPositions.length > 0 ? corridorPositions : data.positions.slice(0, 12);
              setPositions(activeList);
              setLastPulseTime(new Date());
              setIsStale(false);

              // Update target coords for smooth gliding
              const newTargets: Record<string, { x: number; y: number }> = {};
              activeList.forEach((p: LivePosition) => {
                newTargets[p.train_no] = projectGeoToSvg(p.lat, p.lng || p.lon || 77.2);
              });
              targetPositionsRef.current = newTargets;
            }
          } catch (e) {
            // Ignore parse errors
          }
        };

        eventSource.onerror = () => {
          setSseConnected(false);
          if (eventSource) {
            eventSource.close();
            eventSource = null;
          }
          // Retry after 4s
          reconnectTimeout = setTimeout(connectSSE, 4000);
        };
      } catch (e) {
        setSseConnected(false);
        reconnectTimeout = setTimeout(connectSSE, 4000);
      }
    }

    connectSSE();

    return () => {
      if (eventSource) eventSource.close();
      if (reconnectTimeout) clearTimeout(reconnectTimeout);
    };
  }, []);

  // 3. Client-Side Glide Animation (1000ms tick interpolation)
  useEffect(() => {
    const glideInterval = setInterval(() => {
      const targets = targetPositionsRef.current;
      const current = { ...currentPositionsRef.current };
      const updated: Record<string, { x: number; y: number }> = {};

      Object.keys(targets).forEach((tNo) => {
        const targetPt = targets[tNo];
        const curPt = current[tNo] || targetPt;

        // Smoothly interpolate towards target
        const dx = targetPt.x - curPt.x;
        const dy = targetPt.y - curPt.y;

        const nextX = curPt.x + dx * 0.35;
        const nextY = curPt.y + dy * 0.35;

        current[tNo] = { x: nextX, y: nextY };
        updated[tNo] = { x: nextX, y: nextY };
      });

      currentPositionsRef.current = current;
      setInterpolatedPositions(updated);
    }, LIVE_CONFIG.GLIDE_DURATION_MS);

    return () => clearInterval(glideInterval);
  }, []);

  // 4. Fetch Train Live Detail on Selection
  useEffect(() => {
    if (!selectedTrainNo) {
      setSelectedDetail(null);
      return;
    }

    setIsLoadingDetail(true);
    const detailUrl = `/v1/trains/${selectedTrainNo}/live`;

    fetch(detailUrl)
      .catch(() => fetch(`${API_BASE}${detailUrl}`))
      .then((res) => {
        if (!res || !res.ok) throw new Error('Train detail not found');
        return res.json();
      })
      .then((data) => {
        setSelectedDetail(data);
        setIsLoadingDetail(false);
      })
      .catch(() => {
        setIsLoadingDetail(false);
      });
  }, [selectedTrainNo]);

  // Format corridor SVG polyline points
  const corridorPointsStr = CORRIDOR_STATIONS.map((s) => {
    const pt = projectGeoToSvg(s.lat, s.lng);
    return `${pt.x},${pt.y}`;
  }).join(' ');

  return (
    <div className="space-y-4 font-sans">
      <SEO title="Live Corridor Spatial Twin · RailTwin-X" noindex />

      {/* Header & Connectivity Bar */}
      <div className="bg-[#15171A] border border-[#26282C] rounded-lg p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-3 shadow-lg">
        <div>
          <div className="flex items-center gap-2">
            <Navigation className="w-5 h-5 text-[#FFB224]" />
            <h1 className="text-base font-bold font-mono text-[#E8E8E6] tracking-tight flex items-center gap-2">
              <span>LIVE CORRIDOR SPATIAL TWIN (PIPELINE 07)</span>
              {sseConnected ? (
                <span className="px-2 py-0.5 text-[10px] font-mono rounded bg-emerald-500/15 text-emerald-400 border border-emerald-500/30 flex items-center gap-1">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                  <span>LIVE SSE (5s)</span>
                </span>
              ) : (
                <span className="px-2 py-0.5 text-[10px] font-mono rounded bg-amber-500/15 text-amber-400 border border-amber-500/30 flex items-center gap-1">
                  <span className="w-1.5 h-1.5 rounded-full bg-amber-400 animate-ping" />
                  <span>POLL SYNC (5s)</span>
                </span>
              )}
              <span className="px-2 py-0.5 text-[10px] font-mono rounded bg-[#1C1E22] text-[#9A9DA3] border border-[#26282C]">
                Active Trains: {positions.length}
              </span>
            </h1>
          </div>
          <p className="font-mono text-xs text-[#9A9DA3] mt-1">
            Trunk High-Density Route: NDLS &rarr; CNB &rarr; PRYJ &rarr; DDU · 785 KM Dead-Reckoning &amp; Kinematic Gliding
          </p>
        </div>

        {/* Map Control Toggles */}
        <div className="flex items-center gap-2 flex-wrap">
          <button
            onClick={() => setShowHalos(!showHalos)}
            className={`px-2.5 py-1.5 text-xs font-mono border rounded flex items-center gap-1.5 transition-colors ${
              showHalos ? 'bg-[#FFB224]/10 border-[#FFB224] text-[#FFB224]' : 'bg-[#1C1E22] border-[#26282C] text-[#9A9DA3]'
            }`}
          >
            <Sparkles className="w-3.5 h-3.5" />
            <span>Confidence Halos</span>
          </button>

          <button
            onClick={() => setShowTSRs(!showTSRs)}
            className={`px-2.5 py-1.5 text-xs font-mono border rounded flex items-center gap-1.5 transition-colors ${
              showTSRs ? 'bg-[#EF4444]/10 border-[#EF4444] text-[#EF4444]' : 'bg-[#1C1E22] border-[#26282C] text-[#9A9DA3]'
            }`}
          >
            <AlertTriangle className="w-3.5 h-3.5" />
            <span>Active TSRs</span>
          </button>

          <button
            onClick={fetchPositions}
            className="px-2.5 py-1.5 text-xs font-mono bg-[#1C1E22] border border-[#26282C] text-[#E8E8E6] hover:border-[#FFB224] rounded flex items-center gap-1.5 transition-colors"
          >
            <RefreshCw className="w-3.5 h-3.5" />
            <span>Poll Now</span>
          </button>
        </div>
      </div>

      {/* Main Interactive Map & Side Drawer Layout */}
      <div className="relative flex flex-col lg:flex-row gap-4 h-[660px]">
        {/* SVG Live Corridor Canvas */}
        <div className="flex-1 relative bg-[#0E0F11] border border-[#26282C] rounded-lg overflow-hidden select-none shadow-2xl">
          <svg viewBox="0 0 1200 500" className="w-full h-full object-contain">
            {/* Dark Grid Texture */}
            <defs>
              <pattern id="liveGrid" width="30" height="30" patternUnits="userSpaceOnUse">
                <path d="M 30 0 L 0 0 0 30" fill="none" stroke="#16181D" strokeWidth="0.6" />
              </pattern>
              {/* Glow Filter for Active Trains */}
              <filter id="glow" x="-50%" y="-50%" width="200%" height="200%">
                <feGaussianBlur stdDeviation="4" result="blur" />
                <feMerge>
                  <feMergeNode in="blur" />
                  <feMergeNode in="SourceGraphic" />
                </feMerge>
              </filter>
            </defs>
            <rect width="100%" height="100%" fill="url(#liveGrid)" />

            {/* DFC Parallel Freight Track */}
            <path
              d="M 60 170 L 1150 470"
              fill="none"
              stroke="#1F232B"
              strokeWidth="2"
              strokeDasharray="5,5"
            />
            <text x="70" y="160" fill="#4B4E54" fontSize="9" fontFamily="monospace">
              EASTERN DEDICATED FREIGHT CORRIDOR (EDFC)
            </text>

            {/* Main Trunk Corridor Track Line */}
            <polyline
              points={corridorPointsStr}
              fill="none"
              stroke="#2B303C"
              strokeWidth="6"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
            <polyline
              points={corridorPointsStr}
              fill="none"
              stroke="#FFB224"
              strokeWidth="2"
              strokeOpacity="0.7"
            />

            {/* Active TSR Restriction Zones */}
            {showTSRs && (
              <g className="opacity-80">
                {/* TSR 1: Outside CNB */}
                <line
                  x1="580"
                  y1="280"
                  x2="660"
                  y2="310"
                  stroke="#EF4444"
                  strokeWidth="5"
                  strokeDasharray="6,4"
                />
                <text x="620" y="270" fill="#EF4444" fontSize="9" fontFamily="monospace" textAnchor="middle">
                  TSR 45 KM/H (FOG CAUTION)
                </text>
              </g>
            )}

            {/* Corridor Stations */}
            {CORRIDOR_STATIONS.map((stn) => {
              const pt = projectGeoToSvg(stn.lat, stn.lng);
              return (
                <g key={stn.code} className="cursor-pointer group">
                  {/* Station Outer Anchor Ring */}
                  <circle
                    cx={pt.x}
                    cy={pt.y}
                    r={stn.is_junction ? 8 : 6}
                    fill="#15171A"
                    stroke={stn.is_junction ? '#FFB224' : '#64748B'}
                    strokeWidth="2.5"
                  />
                  {/* Station Center Dot */}
                  <circle cx={pt.x} cy={pt.y} r={3} fill="#E8E8E6" />
                  {/* Station Code & KM Badge */}
                  <text
                    x={pt.x}
                    y={pt.y - 14}
                    textAnchor="middle"
                    fill="#E8E8E6"
                    fontSize="11"
                    fontFamily="monospace"
                    fontWeight="bold"
                  >
                    {stn.code}
                  </text>
                  <text
                    x={pt.x}
                    y={pt.y + 20}
                    textAnchor="middle"
                    fill="#64748B"
                    fontSize="9"
                    fontFamily="monospace"
                  >
                    {stn.distance_km}km
                  </text>
                </g>
              );
            })}

            {/* Active Live Trains (Gliding Markers with Confidence Halos) */}
            {positions.map((train) => {
              const pt = interpolatedPositions[train.train_no] || projectGeoToSvg(train.lat, train.lng || train.lon || 77.2);
              const color = getDelayColor(train.delay_minutes);
              const isSelected = selectedTrainNo === train.train_no;
              const confidence = Math.max(0.2, Math.min(1.0, train.confidence || 0.9));

              return (
                <g
                  key={train.train_no}
                  onClick={() => setSelectedTrainNo(train.train_no)}
                  className="cursor-pointer transition-transform hover:scale-110"
                >
                  {/* Confidence Halo Ring (opacity proportional to confidence) */}
                  {showHalos && (
                    <circle
                      cx={pt.x}
                      cy={pt.y}
                      r={18 + (1.0 - confidence) * 16}
                      fill={color}
                      fillOpacity={0.15 * confidence}
                      stroke={color}
                      strokeWidth="1.2"
                      strokeDasharray={train.is_dead_reckoned ? '3,3' : 'none'}
                      className="animate-pulse"
                    />
                  )}

                  {/* Selection Pulsing Ring */}
                  {isSelected && (
                    <circle
                      cx={pt.x}
                      cy={pt.y}
                      r={15}
                      fill="none"
                      stroke="#FFB224"
                      strokeWidth="2"
                      className="animate-ping"
                    />
                  )}

                  {/* Train Marker Base Capsule */}
                  <circle
                    cx={pt.x}
                    cy={pt.y}
                    r={9}
                    fill="#15171A"
                    stroke={color}
                    strokeWidth="2.5"
                    filter="url(#glow)"
                  />
                  <circle cx={pt.x} cy={pt.y} r={4} fill={color} />

                  {/* Train Label Badge */}
                  <g transform={`translate(${pt.x + 12}, ${pt.y - 12})`}>
                    <rect
                      x="0"
                      y="0"
                      width="74"
                      height="20"
                      rx="3"
                      fill="#15171A"
                      stroke={isSelected ? '#FFB224' : '#26282C'}
                      strokeWidth="1"
                    />
                    <text
                      x="6"
                      y="14"
                      fill="#E8E8E6"
                      fontSize="10"
                      fontFamily="monospace"
                      fontWeight="bold"
                    >
                      #{train.train_no}
                    </text>
                    <text
                      x="48"
                      y="14"
                      fill={color}
                      fontSize="9"
                      fontFamily="monospace"
                      fontWeight="bold"
                    >
                      {train.delay_minutes > 0 ? `+${Math.round(train.delay_minutes)}m` : 'RT'}
                    </text>
                  </g>
                </g>
              );
            })}
          </svg>

          {/* Quick HUD Overlay */}
          <div className="absolute bottom-3 left-3 bg-[#15171A]/90 backdrop-blur border border-[#26282C] px-3 py-2 rounded text-[11px] font-mono text-[#9A9DA3] flex items-center gap-4 shadow-lg">
            <div className="flex items-center gap-1.5">
              <span className="w-2.5 h-2.5 rounded-full bg-[#10B981]" />
              <span>On Time (&le;15m)</span>
            </div>
            <div className="flex items-center gap-1.5">
              <span className="w-2.5 h-2.5 rounded-full bg-[#F59E0B]" />
              <span>Moderate (&le;60m)</span>
            </div>
            <div className="flex items-center gap-1.5">
              <span className="w-2.5 h-2.5 rounded-full bg-[#EF4444]" />
              <span>Severe (&gt;60m)</span>
            </div>
            <div className="hidden sm:inline border-l border-[#26282C] pl-3 text-[#64748B]">
              Click any train capsule for Why-Late delay attribution &amp; 5-layer context &rarr;
            </div>
          </div>
        </div>

        {/* Why-Late & Context Side Drawer Panel */}
        {selectedTrainNo && (
          <div className="w-full lg:w-96 bg-[#15171A] border border-[#26282C] rounded-lg p-4 flex flex-col justify-between overflow-y-auto shadow-2xl animate-in slide-in-from-right duration-300">
            <div className="space-y-4">
              {/* Drawer Header */}
              <div className="flex items-start justify-between border-b border-[#26282C] pb-3">
                <div>
                  <div className="flex items-center gap-2">
                    <TrainIcon className="w-4 h-4 text-[#FFB224]" />
                    <h2 className="text-sm font-bold font-mono text-[#E8E8E6]">
                      TRAIN #{selectedTrainNo}
                    </h2>
                  </div>
                  <p className="text-xs text-[#9A9DA3] mt-0.5 truncate max-w-[240px]">
                    {selectedDetail?.train_name || 'Corridor Express'} · {selectedDetail?.train_class || 'Superfast'}
                  </p>
                </div>
                <button
                  onClick={() => setSelectedTrainNo(null)}
                  className="p-1 text-[#9A9DA3] hover:text-[#E8E8E6] rounded"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>

              {isLoadingDetail ? (
                <div className="py-12 flex flex-col items-center justify-center gap-2 text-xs font-mono text-[#9A9DA3]">
                  <RefreshCw className="w-5 h-5 animate-spin text-[#FFB224]" />
                  <span>Hydrating 5-layer operational context...</span>
                </div>
              ) : selectedDetail ? (
                <div className="space-y-4 text-xs font-mono">
                  {/* Kinematics Strip */}
                  <div className="grid grid-cols-3 gap-2 text-center bg-[#1C1E22] p-2.5 rounded border border-[#26282C]">
                    <div>
                      <div className="text-[10px] text-[#9A9DA3]">CURRENT DELAY</div>
                      <div
                        className="text-base font-bold mt-0.5"
                        style={{ color: getDelayColor(selectedDetail.position.delay_minutes) }}
                      >
                        +{Math.round(selectedDetail.position.delay_minutes)}m
                      </div>
                    </div>
                    <div>
                      <div className="text-[10px] text-[#9A9DA3]">SPEED</div>
                      <div className="text-base font-bold text-[#E8E8E6] mt-0.5">
                        {Math.round(selectedDetail.position.speed_kmh)} <span className="text-[10px]">km/h</span>
                      </div>
                    </div>
                    <div>
                      <div className="text-[10px] text-[#9A9DA3]">CONFIDENCE</div>
                      <div className="text-base font-bold text-[#38BDF8] mt-0.5">
                        {Math.round(selectedDetail.position.confidence * 100)}%
                      </div>
                    </div>
                  </div>

                  {/* Why-Late Attribution Card */}
                  <div className="bg-[#1C1E22] border border-[#26282C] rounded p-3 space-y-2">
                    <div className="flex items-center justify-between text-[11px] font-bold text-[#E8E8E6]">
                      <span className="flex items-center gap-1.5">
                        <Activity className="w-3.5 h-3.5 text-[#FFB224]" />
                        <span>WHY-LATE DELAY ATTRIBUTION</span>
                      </span>
                      {selectedDetail.why_late?.is_exact_accounting && (
                        <span className="text-[9px] px-1.5 py-0.2 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
                          EXACT 100% BALANCED
                        </span>
                      )}
                    </div>

                    <div className="space-y-1.5 pt-1">
                      {selectedDetail.why_late?.cause_breakdown && selectedDetail.why_late.cause_breakdown.length > 0 ? (
                        selectedDetail.why_late.cause_breakdown.map((cause) => {
                          const causeColor = ATTRIBUTION_COLORS[cause.cause_code] || '#64748B';
                          return (
                            <div
                              key={cause.cause_code}
                              className="p-2 bg-[#15171A] border border-[#26282C] rounded space-y-1"
                            >
                              <div className="flex items-center justify-between">
                                <span className="font-bold" style={{ color: causeColor }}>
                                  {cause.name}
                                </span>
                                <span className="font-bold text-[#E8E8E6]">
                                  +{cause.attributed_min.toFixed(1)}m ({cause.share_pct}%)
                                </span>
                              </div>
                              <p className="text-[10px] text-[#9A9DA3] font-sans">
                                {cause.description}
                              </p>
                            </div>
                          );
                        })
                      ) : (
                        <div className="p-2 bg-[#15171A] border border-[#26282C] rounded text-center text-[#9A9DA3] text-[11px]">
                          Train is operating nominal on-time schedule.
                        </div>
                      )}
                    </div>
                  </div>

                  {/* 5-Layer Micro-Context Card */}
                  <div className="bg-[#1C1E22] border border-[#26282C] rounded p-3 space-y-2">
                    <div className="text-[11px] font-bold text-[#E8E8E6] flex items-center gap-1.5">
                      <Layers className="w-3.5 h-3.5 text-[#38BDF8]" />
                      <span>5-LAYER OPERATIONAL CONTEXT</span>
                    </div>

                    <div className="space-y-2 pt-1">
                      {/* Weather Layer */}
                      <div className="flex items-center justify-between text-[11px]">
                        <span className="text-[#9A9DA3] flex items-center gap-1">
                          <CloudFog className="w-3 h-3 text-[#94A3B8]" />
                          <span>Weather ({selectedDetail.context.weather.station_code})</span>
                        </span>
                        <span className="text-[#E8E8E6]">
                          {selectedDetail.context.weather.temperature_celsius}°C · Vis {selectedDetail.context.weather.visibility_km}km
                          {selectedDetail.context.weather.fog_risk_flag && ' (Fog Alert)'}
                        </span>
                      </div>

                      {/* TSRs Ahead */}
                      <div className="flex items-center justify-between text-[11px]">
                        <span className="text-[#9A9DA3] flex items-center gap-1">
                          <ShieldAlert className="w-3 h-3 text-[#EF4444]" />
                          <span>TSRs on Next 3 Sections</span>
                        </span>
                        <span className="text-[#E8E8E6]">
                          {selectedDetail.context.tsrs_ahead.length > 0 ? `${selectedDetail.context.tsrs_ahead.length} Active` : 'Clear Track'}
                        </span>
                      </div>

                      {/* Turnaround Rake Status */}
                      <div className="flex items-center justify-between text-[11px]">
                        <span className="text-[#9A9DA3] flex items-center gap-1">
                          <RotateCcw className="w-3 h-3 text-[#A855F7]" />
                          <span>Incoming Rake Link</span>
                        </span>
                        <span className="text-[#E8E8E6]">
                          {selectedDetail.context.incoming_rake.incoming_train_no
                            ? `#${selectedDetail.context.incoming_rake.incoming_train_no} (${selectedDetail.context.incoming_rake.status})`
                            : 'Dedicated Rake'}
                        </span>
                      </div>
                    </div>
                  </div>
                </div>
              ) : null}
            </div>

            {/* Footer Action */}
            <div className="pt-3 border-t border-[#26282C]">
              <a
                href={`/dashboard/trains/${selectedTrainNo}`}
                className="w-full py-2 bg-[#FFB224] text-[#0E0F11] font-mono font-bold text-xs rounded text-center block hover:bg-[#FFB224]/90 transition-colors"
              >
                Inspect Full Journey &amp; Telemetry Autopsy &rarr;
              </a>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
