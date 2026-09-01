import React, { useState, useEffect, useRef } from 'react';
import { useQuery } from '@tanstack/react-query';
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

interface LivePosition {
  train_no: string;
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
  heading: number;
  delay_minutes: number;
  confidence: number;
  progress_pct: number;
  is_dead_reckoned: boolean;
  basis: string;
  source: string;
  status: string;
  last_event_time?: string;
  updated_at: string;
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
      dwell_min: number;
    };
  };
  why_late: {
    train_no: string;
    run_date: string;
    total_attributed_delay_min: number;
    is_exact_accounting: boolean;
    cause_breakdown: Array<{
      cause_code: string;
      attributed_min: number;
      percentage: number;
    }>;
    timeline: Array<{
      id: number;
      timestamp: string;
      delay_change_min: number;
      previous_delay_min: number;
      current_delay_min: number;
      primary_cause: string;
      secondary_cause?: string;
    }>;
  };
}

// Project coordinate (lat, lon) to SVG viewBox (0..1200, 0..500)
function projectGeoToSvg(lat: number, lon: number): { x: number; y: number } {
  const minLat = 25.0;
  const maxLat = 29.0;
  const minLon = 77.0;
  const maxLon = 83.5;

  const normX = (lon - minLon) / (maxLon - minLon);
  const normY = (maxLat - lat) / (maxLat - minLat);

  const x = 70 + normX * 1060;
  const y = 80 + normY * 340;
  return { x: Math.max(50, Math.min(1150, x)), y: Math.max(50, Math.min(450, y)) };
}

function getDelayColor(delayMin: number): string {
  if (delayMin <= 15) return COLOR_TOKENS.SUCCESS;
  if (delayMin <= 60) return COLOR_TOKENS.WARNING;
  return COLOR_TOKENS.DANGER;
}

export function LiveMapPage() {
  const [positions, setPositions] = useState<LivePosition[]>([]);
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

  // 1. Initial REST Fetch for Positions
  useEffect(() => {
    fetch('/v1/live/positions')
      .then(res => res.json())
      .then(data => {
        if (data && Array.isArray(data.positions)) {
          setPositions(data.positions);
          const initialTargets: Record<string, { x: number; y: number }> = {};
          data.positions.forEach((p: LivePosition) => {
            const pt = projectGeoToSvg(p.lat, p.lng || p.lon || 77.2);
            initialTargets[p.train_no] = pt;
          });
          targetPositionsRef.current = initialTargets;
          currentPositionsRef.current = initialTargets;
          setInterpolatedPositions(initialTargets);
          setLastPulseTime(new Date());
        }
      })
      .catch(() => {
        setIsStale(true);
      });
  }, []);

  // 2. Real-time SSE Stream with Resilient Reconnect
  useEffect(() => {
    let eventSource: EventSource | null = null;
    let reconnectTimeout: any = null;

    function connectSSE() {
      try {
        eventSource = new EventSource('/v1/live/stream');

        eventSource.onopen = () => {
          setSseConnected(true);
          setIsStale(false);
        };

        eventSource.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data);
            if (data && Array.isArray(data.positions)) {
              setPositions(data.positions);
              setLastPulseTime(new Date());
              setIsStale(false);

              // Update target coords for smooth gliding
              const newTargets: Record<string, { x: number; y: number }> = {};
              data.positions.forEach((p: LivePosition) => {
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
          setIsStale(true);
          if (eventSource) {
            eventSource.close();
            eventSource = null;
          }
          // Exponential backoff retry after 4s
          reconnectTimeout = setTimeout(connectSSE, 4000);
        };
      } catch (e) {
        setSseConnected(false);
        setIsStale(true);
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

        const nextX = curPt.x + dx * 0.4;
        const nextY = curPt.y + dy * 0.4;

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
    fetch(`/v1/trains/${selectedTrainNo}/live`)
      .then((res) => {
        if (!res.ok) throw new Error('Train detail not found');
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
    <div className="space-y-4">
      <SEO title="Live Corridor Spatial Twin · RailTwin-X" noindex />

      {/* Header & Connectivity Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-3 border-b border-[#26282C] gap-3">
        <div>
          <div className="flex items-center gap-2">
            <Navigation className="w-5 h-5 text-[#FFB224]" />
            <h1 className="text-lg font-semibold text-[#E8E8E6]">Live Corridor Spatial Twin (Pipeline 07)</h1>
            {sseConnected ? (
              <span className="px-2 py-0.5 text-[10px] font-mono rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 flex items-center gap-1">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                <span>LIVE SSE (5s)</span>
              </span>
            ) : isStale ? (
              <span className="px-2 py-0.5 text-[10px] font-mono rounded bg-amber-500/10 text-amber-400 border border-amber-500/30 flex items-center gap-1">
                <WifiOff className="w-3 h-3" />
                <span>STALE TELEMETRY (RECONNECTING)</span>
              </span>
            ) : (
              <span className="px-2 py-0.5 text-[10px] font-mono rounded bg-slate-800 text-slate-400 border border-slate-700">
                CONNECTING...
              </span>
            )}
            <span className="font-mono text-xs text-[#9A9DA3]">
              Active Trains: {positions.length}
            </span>
          </div>
          <p className="font-mono text-xs text-[#9A9DA3] mt-0.5">
            Trunk High-Density Route: NDLS $\rightarrow$ CNB $\rightarrow$ PRYJ $\rightarrow$ DDU · 785 KM Dead-Reckoning & Kinematic Gliding
          </p>
        </div>

        {/* Map Control Toggles */}
        <div className="flex items-center gap-2 flex-wrap">
          <button
            onClick={() => setShowHalos(!showHalos)}
            className={`px-2.5 py-1 text-xs font-mono border flex items-center gap-1.5 transition-colors ${
              showHalos ? 'bg-[#FFB224]/10 border-[#FFB224] text-[#FFB224]' : 'bg-[#15171A] border-[#26282C] text-[#9A9DA3]'
            }`}
          >
            <Sparkles className="w-3 h-3" />
            <span>Confidence Halos</span>
          </button>

          <button
            onClick={() => setShowTSRs(!showTSRs)}
            className={`px-2.5 py-1 text-xs font-mono border flex items-center gap-1.5 transition-colors ${
              showTSRs ? 'bg-[#EF4444]/10 border-[#EF4444] text-[#EF4444]' : 'bg-[#15171A] border-[#26282C] text-[#9A9DA3]'
            }`}
          >
            <AlertTriangle className="w-3 h-3" />
            <span>Active TSRs</span>
          </button>

          <button
            onClick={() => {
              fetch('/v1/live/positions')
                .then(r => r.json())
                .then(d => { if (d && d.positions) setPositions(d.positions); });
            }}
            className="px-2.5 py-1 text-xs font-mono bg-[#15171A] border border-[#26282C] text-[#E8E8E6] hover:border-[#FFB224] flex items-center gap-1.5 transition-colors"
          >
            <RefreshCw className="w-3 h-3" />
            <span>Poll Now</span>
          </button>
        </div>
      </div>

      {/* Main Interactive Map & Side Drawer Layout */}
      <div className="relative flex flex-col lg:flex-row gap-4 h-[640px]">
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
                <feGaussianBlur stdDeviation="3" result="blur" />
                <feMerge>
                  <feMergeNode in="blur" />
                  <feMergeNode in="SourceGraphic" />
                </feMerge>
              </filter>
            </defs>
            <rect width="100%" height="100%" fill="url(#liveGrid)" />

            {/* DFC Parallel Freight Track */}
            <path
              d="M 60 160 L 1150 480"
              fill="none"
              stroke="#1F232B"
              strokeWidth="2"
              strokeDasharray="4,4"
            />

            {/* Main Trunk Corridor Track Line */}
            <polyline
              points={corridorPointsStr}
              fill="none"
              stroke="#333842"
              strokeWidth="4"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
            <polyline
              points={corridorPointsStr}
              fill="none"
              stroke="#FFB224"
              strokeWidth="1.5"
              strokeOpacity="0.4"
            />

            {/* Corridor Stations */}
            {CORRIDOR_STATIONS.map((stn) => {
              const pt = projectGeoToSvg(stn.lat, stn.lng);
              return (
                <g key={stn.code} className="cursor-pointer group">
                  {/* Station Outer Anchor Ring */}
                  <circle
                    cx={pt.x}
                    cy={pt.y}
                    r={stn.is_junction ? 7 : 5}
                    fill="#15171A"
                    stroke={stn.is_junction ? '#FFB224' : '#64748B'}
                    strokeWidth="2"
                  />
                  {/* Station Center Dot */}
                  <circle cx={pt.x} cy={pt.y} r={2.5} fill="#E8E8E6" />
                  {/* Station Code & KM Badge */}
                  <text
                    x={pt.x}
                    y={pt.y - 12}
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
                    y={pt.y + 18}
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
              const confidence = Math.max(0.1, Math.min(1.0, train.confidence));
              const isStaleTrain = train.confidence <= BACKEND_DEFAULTS.DEAD_RECKON_MIN_CONFIDENCE;

              return (
                <g
                  key={train.train_no}
                  onClick={() => setSelectedTrainNo(train.train_no)}
                  className="cursor-pointer transition-transform hover:scale-110"
                  style={{ transformOrigin: `${pt.x}px ${pt.y}px` }}
                >
                  {/* Confidence Halo Ring (opacity proportional to confidence) */}
                  {showHalos && (
                    <circle
                      cx={pt.x}
                      cy={pt.y}
                      r={isSelected ? 18 : 14}
                      fill="none"
                      stroke={color}
                      strokeWidth="1.5"
                      strokeDasharray={isStaleTrain ? '3,3' : 'none'}
                      opacity={confidence * 0.7}
                      className={isStaleTrain ? '' : 'animate-pulse'}
                    />
                  )}

                  {/* Train Main Marker */}
                  <circle
                    cx={pt.x}
                    cy={pt.y}
                    r={isSelected ? 8 : 6}
                    fill={color}
                    stroke="#0E0F11"
                    strokeWidth="2"
                    filter="url(#glow)"
                  />

                  {/* Train Number Label & Delay Chip */}
                  <g transform={`translate(${pt.x + 10}, ${pt.y - 10})`}>
                    <rect
                      x="0"
                      y="-10"
                      width="60"
                      height="18"
                      rx="3"
                      fill="#15171A"
                      stroke={isSelected ? '#FFB224' : '#26282C'}
                      strokeWidth="1"
                    />
                    <text
                      x="5"
                      y="2"
                      fill="#E8E8E6"
                      fontSize="9"
                      fontFamily="monospace"
                      fontWeight="bold"
                    >
                      #{train.train_no}
                    </text>
                    <text
                      x="40"
                      y="2"
                      fill={color}
                      fontSize="8"
                      fontFamily="monospace"
                      fontWeight="bold"
                    >
                      +{Math.round(train.delay_minutes)}m
                    </text>
                  </g>
                </g>
              );
            })}
          </svg>

          {/* Map Legend Overlay */}
          <div className="absolute bottom-3 left-3 bg-[#15171A]/90 backdrop-blur border border-[#26282C] rounded p-2.5 flex items-center gap-4 text-xs font-mono">
            <div className="flex items-center gap-1.5">
              <span className="w-2.5 h-2.5 rounded-full bg-[#10B981]" />
              <span className="text-[#9A9DA3]">On-Time (&le;15m)</span>
            </div>
            <div className="flex items-center gap-1.5">
              <span className="w-2.5 h-2.5 rounded-full bg-[#F59E0B]" />
              <span className="text-[#9A9DA3]">Moderate (15-60m)</span>
            </div>
            <div className="flex items-center gap-1.5">
              <span className="w-2.5 h-2.5 rounded-full bg-[#EF4444]" />
              <span className="text-[#9A9DA3]">Severe (&gt;60m)</span>
            </div>
            <div className="flex items-center gap-1.5">
              <span className="w-2.5 h-2.5 border border-[#FFB224] rounded-full" />
              <span className="text-[#9A9DA3]">Confidence Halo $\tau=1800s$</span>
            </div>
          </div>
        </div>

        {/* Train Detail & Why-Late Attribution Side Panel */}
        {selectedTrainNo && (
          <div className="w-full lg:w-96 bg-[#15171A] border border-[#26282C] rounded-lg p-4 flex flex-col gap-3 overflow-y-auto max-h-[640px] shadow-2xl">
            {/* Drawer Header */}
            <div className="flex items-center justify-between pb-2 border-b border-[#26282C]">
              <div>
                <div className="flex items-center gap-2">
                  <span className="text-sm font-bold font-mono text-[#FFB224]">
                    Train #{selectedTrainNo}
                  </span>
                  {selectedDetail && (
                    <span className="text-xs text-[#E8E8E6] font-medium truncate max-w-[160px]">
                      {selectedDetail.train_name}
                    </span>
                  )}
                </div>
                <div className="font-mono text-[10px] text-[#9A9DA3] flex items-center gap-2 mt-0.5">
                  <span>Class: {selectedDetail?.train_class || 'SUPERFAST'}</span>
                  <span>·</span>
                  <span>Date: {selectedDetail?.run_date || 'Today'}</span>
                </div>
              </div>
              <button
                onClick={() => setSelectedTrainNo(null)}
                className="p-1 hover:bg-[#26282C] rounded text-[#9A9DA3] hover:text-[#E8E8E6]"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {isLoadingDetail ? (
              <div className="py-12 flex flex-col items-center justify-center gap-2 text-xs font-mono text-[#9A9DA3]">
                <RefreshCw className="w-5 h-5 text-[#FFB224] animate-spin" />
                <span>Enriching live context & delay autopsy...</span>
              </div>
            ) : selectedDetail ? (
              <>
                {/* 1. Real-time Telemetry & Kinematics Card */}
                <div className="bg-[#1C1E22] border border-[#26282C] rounded p-3 space-y-2">
                  <div className="text-[11px] font-mono uppercase text-[#9A9DA3] flex items-center justify-between">
                    <span>Live Kinematics</span>
                    <span className="text-emerald-400 font-bold">
                      Confidence: {(selectedDetail.position.confidence * 100).toFixed(0)}%
                    </span>
                  </div>
                  <div className="grid grid-cols-2 gap-2 text-xs font-mono">
                    <div className="bg-[#15171A] p-2 rounded border border-[#26282C]">
                      <span className="text-[10px] text-[#9A9DA3] block">Speed</span>
                      <span className="text-sm font-bold text-[#E8E8E6]">
                        {selectedDetail.position.speed_kmh} km/h
                      </span>
                    </div>
                    <div className="bg-[#15171A] p-2 rounded border border-[#26282C]">
                      <span className="text-[10px] text-[#9A9DA3] block">Current Delay</span>
                      <span
                        className="text-sm font-bold"
                        style={{ color: getDelayColor(selectedDetail.position.delay_minutes) }}
                      >
                        +{Math.round(selectedDetail.position.delay_minutes)}m
                      </span>
                    </div>
                    <div className="bg-[#15171A] p-2 rounded border border-[#26282C]">
                      <span className="text-[10px] text-[#9A9DA3] block">Station Anchor</span>
                      <span className="text-xs font-bold text-[#E8E8E6]">
                        {selectedDetail.position.current_station_code || 'NDLS'}
                      </span>
                    </div>
                    <div className="bg-[#15171A] p-2 rounded border border-[#26282C]">
                      <span className="text-[10px] text-[#9A9DA3] block">Progress</span>
                      <span className="text-xs font-bold text-[#E8E8E6]">
                        {selectedDetail.position.progress_pct.toFixed(1)}% (
                        {(selectedDetail.position.progress_pct * 7.85).toFixed(0)} km)
                      </span>
                    </div>
                  </div>
                </div>

                {/* 2. WHY-LATE Delay Attribution Card (Honest Exact Accounting) */}
                <div className="bg-[#1C1E22] border border-[#26282C] rounded p-3 space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-[11px] font-mono uppercase text-[#FFB224] font-bold flex items-center gap-1.5">
                      <HelpCircle className="w-3.5 h-3.5" />
                      <span>Why-Late Delay Autopsy</span>
                    </span>
                    <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                      Exact Accounting &check;
                    </span>
                  </div>

                  {selectedDetail.why_late.cause_breakdown.length === 0 ? (
                    <div className="text-xs font-mono text-[#9A9DA3] py-2 text-center">
                      On time · No significant delay jumps recorded.
                    </div>
                  ) : (
                    <div className="space-y-2">
                      {selectedDetail.why_late.cause_breakdown.map((c) => {
                        const causeColor = ATTRIBUTION_COLORS[c.cause_code] || '#64748B';
                        return (
                          <div key={c.cause_code} className="space-y-1 font-mono text-xs">
                            <div className="flex items-center justify-between">
                              <span className="flex items-center gap-1.5">
                                <span
                                  className="w-2 h-2 rounded-full"
                                  style={{ backgroundColor: causeColor }}
                                />
                                <span className="text-[#E8E8E6] font-bold">{c.cause_code}</span>
                              </span>
                              <span className="text-[#9A9DA3]">
                                +{c.attributed_min}m ({c.percentage}%)
                              </span>
                            </div>
                            {/* Confidence / Share Bar */}
                            <div className="w-full bg-[#15171A] h-1.5 rounded overflow-hidden">
                              <div
                                className="h-full rounded"
                                style={{
                                  width: `${c.percentage}%`,
                                  backgroundColor: causeColor,
                                }}
                              />
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  )}
                </div>

                {/* 3. Operational Context Card (Weather, TSRs, Rake Links) */}
                <div className="bg-[#1C1E22] border border-[#26282C] rounded p-3 space-y-2 font-mono text-xs">
                  <div className="text-[11px] uppercase text-[#9A9DA3] font-bold flex items-center gap-1.5">
                    <Compass className="w-3.5 h-3.5 text-[#38BDF8]" />
                    <span>Corridor Context</span>
                  </div>

                  {/* Micro-Weather */}
                  <div className="bg-[#15171A] p-2 rounded border border-[#26282C] flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      {selectedDetail.context.weather.fog_risk_flag ? (
                        <CloudFog className="w-4 h-4 text-amber-400" />
                      ) : selectedDetail.context.weather.rain_risk_flag ? (
                        <CloudRain className="w-4 h-4 text-sky-400" />
                      ) : (
                        <Wind className="w-4 h-4 text-emerald-400" />
                      )}
                      <div>
                        <span className="text-[#E8E8E6] block">
                          Weather at {selectedDetail.context.weather.station_code}
                        </span>
                        <span className="text-[10px] text-[#9A9DA3]">
                          {selectedDetail.context.weather.temperature_celsius}&deg;C ·{' '}
                          {selectedDetail.context.weather.relative_humidity_percent}% RH · Vis{' '}
                          {selectedDetail.context.weather.visibility_km}km
                        </span>
                      </div>
                    </div>
                  </div>

                  {/* Incoming Rake Link */}
                  {selectedDetail.context.incoming_rake.incoming_train_no && (
                    <div className="bg-[#15171A] p-2 rounded border border-[#26282C] flex items-center justify-between">
                      <div>
                        <span className="text-[10px] text-[#9A9DA3] block">Incoming Rake Link</span>
                        <span className="text-[#E8E8E6] font-bold">
                          #{selectedDetail.context.incoming_rake.incoming_train_no} (
                          {selectedDetail.context.incoming_rake.status})
                        </span>
                      </div>
                      <span className="text-amber-400 font-bold">
                        Deficit: +{selectedDetail.context.incoming_rake.turnaround_deficit_min}m
                      </span>
                    </div>
                  )}

                  {/* Active TSR Caution Orders */}
                  {selectedDetail.context.tsrs_ahead.length > 0 && (
                    <div className="bg-[#15171A] p-2 rounded border border-[#26282C] space-y-1">
                      <span className="text-[10px] text-red-400 font-bold block flex items-center gap-1">
                        <AlertTriangle className="w-3 h-3" />
                        <span>Active TSR Ahead</span>
                      </span>
                      {selectedDetail.context.tsrs_ahead.map((tsr) => (
                        <div key={tsr.id} className="text-[10px] text-[#9A9DA3]">
                          {tsr.from_station} &rarr; {tsr.to_station}: Max {tsr.speed_limit_kmh} km/h ({tsr.reason})
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </>
            ) : null}
          </div>
        )}
      </div>
    </div>
  );
}
