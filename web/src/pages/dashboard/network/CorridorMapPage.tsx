import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/api';
import { queryKeys } from '@/lib/queryKeys';
import { Train } from '@/mock/types';
import { SEO } from '@/lib/seo';
import { DataFreshnessBadge } from '@/components/common/DataFreshnessBadge';
import { Layers, Train as TrainIcon, AlertTriangle, ShieldCheck, Eye, EyeOff, Navigation } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

// Coordinates for Northern Railway Corridor stations
const STATIONS_GEO = [
  { code: 'NDLS', name: 'New Delhi', x: 80, y: 120, km: 0 },
  { code: 'GZB', name: 'Ghaziabad Jn', x: 180, y: 140, km: 28 },
  { code: 'ALJN', name: 'Aligarh Jn', x: 340, y: 200, km: 126 },
  { code: 'TDL', name: 'Tundla Jn', x: 480, y: 260, km: 204 },
  { code: 'ETW', name: 'Etawah Jn', x: 620, y: 310, km: 296 },
  { code: 'CNB', name: 'Kanpur Central', x: 780, y: 350, km: 437 },
  { code: 'PRYJ', name: 'Prayagraj Jn', x: 960, y: 400, km: 632 },
  { code: 'DDU', name: 'Pt. Deen Dayal Upadhyaya', x: 1140, y: 440, km: 785 },
];

export function CorridorMapPage() {
  const navigate = useNavigate();
  const { data: trains = [], dataUpdatedAt } = useQuery({
    queryKey: queryKeys.board('NDLS'),
    queryFn: () => api.getTrains(),
  });
  const [showTSR, setShowTSR] = useState(true);
  const [showBlocks, setShowBlocks] = useState(true);
  const [showFreight, setShowFreight] = useState(true);
  const [selectedTrain, setSelectedTrain] = useState<Train | null>(null);

  return (
    <div className="space-y-4">
      <SEO title="Corridor GIS Spatial Map · RailTwin-X" noindex />

      {/* Header & Layer Toggles */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-3 border-b border-[#26282C] gap-3">
        <div>
          <h1 className="text-lg font-semibold text-[#E8E8E6] flex items-center gap-2">
            <Navigation className="w-4 h-4 text-[#FFB224]" />
            <span>Corridor GIS Spatial Map</span>
            <DataFreshnessBadge dataUpdatedAt={dataUpdatedAt} />
          </h1>
          <p className="font-mono text-xs text-[#9A9DA3]">
            Trunk Corridor: NDLS – GZB – ALJN – TDL – ETW – CNB – PRYJ – DDU · 785 KM
          </p>
        </div>

        <div className="flex items-center gap-2 flex-wrap">
          <button
            onClick={() => setShowTSR(!showTSR)}
            className={`px-2.5 py-1 text-xs font-mono border flex items-center gap-1.5 transition-colors ${
              showTSR ? 'bg-[#FFB224]/10 border-[#FFB224] text-[#FFB224]' : 'bg-[#15171A] border-[#26282C] text-[#9A9DA3]'
            }`}
          >
            <AlertTriangle className="w-3 h-3" />
            <span>TSR Caution Zones</span>
          </button>

          <button
            onClick={() => setShowBlocks(!showBlocks)}
            className={`px-2.5 py-1 text-xs font-mono border flex items-center gap-1.5 transition-colors ${
              showBlocks ? 'bg-[#3ECF8E]/10 border-[#3ECF8E] text-[#3ECF8E]' : 'bg-[#15171A] border-[#26282C] text-[#9A9DA3]'
            }`}
          >
            <ShieldCheck className="w-3 h-3" />
            <span>Track Blocks</span>
          </button>

          <button
            onClick={() => setShowFreight(!showFreight)}
            className={`px-2.5 py-1 text-xs font-mono border flex items-center gap-1.5 transition-colors ${
              showFreight ? 'bg-[#E8E8E6]/10 border-[#E8E8E6] text-[#E8E8E6]' : 'bg-[#15171A] border-[#26282C] text-[#9A9DA3]'
            }`}
          >
            <TrainIcon className="w-3 h-3" />
            <span>DFC Freight Rakes</span>
          </button>
        </div>
      </div>

      {/* Main Map Canvas Area */}
      <div className="relative bg-[#0E0F11] border border-[#26282C] h-[620px] overflow-hidden select-none">
        {/* SVG Track Alignment Renderer */}
        <svg viewBox="0 0 1250 550" className="w-full h-full object-contain">
          {/* Grid Background */}
          <defs>
            <pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse">
              <path d="M 40 0 L 0 0 0 40" fill="none" stroke="#181A1F" strokeWidth="0.8" />
            </pattern>
          </defs>
          <rect width="100%" height="100%" fill="url(#grid)" />

          {/* DFC Dedicated Freight Corridor Line */}
          <path
            d="M 60 160 L 1180 480"
            fill="none"
            stroke="#26282C"
            strokeWidth="3"
            strokeDasharray="6 6"
          />
          <text x="70" y="180" fill="#6B6E74" fontSize="10" fontFamily="IBM Plex Mono">
            EASTERN DFC FREIGHT CORRIDOR (ROOMA - PANKI LINK)
          </text>

          {/* UP Main & DOWN Main Lines */}
          <path
            d="M 80 120 L 180 140 L 340 200 L 480 260 L 620 310 L 780 350 L 960 400 L 1140 440"
            fill="none"
            stroke="#3A3D45"
            strokeWidth="4"
          />
          <path
            d="M 80 126 L 180 146 L 340 206 L 480 266 L 620 316 L 780 356 L 960 406 L 1140 446"
            fill="none"
            stroke="#3A3D45"
            strokeWidth="4"
          />

          {/* Active Caution Orders (TSR) Zone */}
          {showTSR && (
            <g>
              <rect x="740" y="338" width="100" height="24" fill="#FFB224" fillOpacity="0.15" stroke="#FFB224" strokeWidth="1" strokeDasharray="3 3" />
              <text x="745" y="332" fill="#FFB224" fontSize="9" fontFamily="IBM Plex Mono" fontWeight="bold">
                TSR KM 1012-1018 (30 km/h)
              </text>
            </g>
          )}

          {/* Maintenance Block Geofence */}
          {showBlocks && (
            <g>
              <rect x="440" y="248" width="80" height="24" fill="#F0533A" fillOpacity="0.15" stroke="#F0533A" strokeWidth="1" />
              <text x="445" y="242" fill="#F0533A" fontSize="9" fontFamily="IBM Plex Mono" fontWeight="bold">
                MNT POSSESSION (TDL-ETW)
              </text>
            </g>
          )}

          {/* Station Markers */}
          {STATIONS_GEO.map(stn => (
            <g key={stn.code} className="cursor-pointer" onClick={() => navigate('/dashboard')}>
              <rect x={stn.x - 6} y={stn.y - 6} width="12" height="12" fill="#15171A" stroke="#FFB224" strokeWidth="2" />
              <text x={stn.x} y={stn.y - 12} fill="#E8E8E6" fontSize="12" fontFamily="IBM Plex Mono" fontWeight="bold" textAnchor="middle">
                {stn.code}
              </text>
              <text x={stn.x} y={stn.y + 22} fill="#9A9DA3" fontSize="9" fontFamily="IBM Plex Mono" textAnchor="middle">
                KM {stn.km}
              </text>
            </g>
          ))}

          {/* Live Train Dots with Speed Vectors */}
          {trains.slice(0, 16).map((train, idx) => {
            // Compute interpolated position along corridor
            const progress = ((idx * 7 + 12) % 100) / 100;
            const startX = 80;
            const endX = 1140;
            const curX = startX + progress * (endX - startX);
            const curY = 120 + progress * 320;
            const isDelayed = train.delayMinutes > 0;
            const isFreight = train.type.includes('Freight');

            if (isFreight && !showFreight) return null;

            return (
              <g
                key={train.number}
                className="cursor-pointer hover:opacity-80 transition-opacity"
                onClick={() => setSelectedTrain(train)}
              >
                {/* Ping animation ring */}
                <circle cx={curX} cy={curY} r="8" fill={isDelayed ? '#FFB224' : '#3ECF8E'} fillOpacity="0.2" className="animate-ping" />
                <circle cx={curX} cy={curY} r="5" fill={isDelayed ? '#FFB224' : '#3ECF8E'} stroke="#0E0F11" strokeWidth="1.5" />
                <text x={curX + 8} y={curY + 3} fill="#E8E8E6" fontSize="9" fontFamily="IBM Plex Mono" fontWeight="bold">
                  {train.number}
                </text>
              </g>
            );
          })}
        </svg>

        {/* Legend Panel (Bottom Left) */}
        <div className="absolute bottom-4 left-4 bg-[#15171A] border border-[#26282C] p-3 font-mono text-[11px] space-y-1.5">
          <div className="text-[10px] text-[#9A9DA3] uppercase tracking-wider font-semibold border-b border-[#26282C] pb-1">
            Map Legend
          </div>
          <div className="flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full bg-[#3ECF8E]" />
            <span className="text-[#E8E8E6]">On-Time Train (&lt;5m)</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full bg-[#FFB224]" />
            <span className="text-[#E8E8E6]">Delayed Train (&gt;5m)</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="w-3 h-1 bg-[#FFB224] border border-dashed border-[#FFB224]" />
            <span className="text-[#E8E8E6]">Active TSR Speed Cap</span>
          </div>
        </div>

        {/* Train Quick Inspector Drawer (Top Right when selected) */}
        {selectedTrain && (
          <div className="absolute top-4 right-4 w-80 bg-[#15171A] border border-[#26282C] p-4 font-mono text-xs space-y-3 shadow-xl">
            <div className="flex items-center justify-between border-b border-[#26282C] pb-2">
              <div className="flex items-center gap-2">
                <span className="w-2 h-2 rounded-none bg-[#FFB224]" />
                <span className="font-bold text-[#E8E8E6]">{selectedTrain.number}</span>
              </div>
              <button onClick={() => setSelectedTrain(null)} className="text-[#9A9DA3] hover:text-[#E8E8E6]">
                ✕
              </button>
            </div>

            <div>
              <div className="text-sm font-semibold text-[#E8E8E6] truncate">{selectedTrain.name}</div>
              <div className="text-[11px] text-[#9A9DA3]">{selectedTrain.origin} → {selectedTrain.destination}</div>
            </div>

            <div className="grid grid-cols-2 gap-2 bg-[#0E0F11] p-2 border border-[#26282C]">
              <div>
                <span className="text-[10px] text-[#9A9DA3] block">EXPECTED ETA</span>
                <span className="font-bold text-[#E8E8E6] text-sm">{selectedTrain.predictedArrival}</span>
              </div>
              <div>
                <span className="text-[10px] text-[#9A9DA3] block">DELAY</span>
                <span className={`font-bold text-sm ${selectedTrain.delayMinutes > 0 ? 'text-[#FFB224]' : 'text-[#3ECF8E]'}`}>
                  {selectedTrain.delayMinutes > 0 ? `+${selectedTrain.delayMinutes} min` : 'ON TIME'}
                </span>
              </div>
            </div>

            <div className="flex items-center justify-between text-[11px] pt-1">
              <span className="text-[#9A9DA3]">Platform: {selectedTrain.platform}</span>
              <button
                onClick={() => navigate(`/dashboard/trains/${selectedTrain.number}`)}
                className="text-[#FFB224] hover:underline"
              >
                Full Journey &rarr;
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
