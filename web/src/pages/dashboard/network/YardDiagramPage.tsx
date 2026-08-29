import React, { useState } from 'react';
import { SEO } from '@/lib/seo';
import { Layers, Activity, Radio, Info } from 'lucide-react';

interface TrackItem {
  id: string;
  name: string;
  type: 'platform' | 'loop' | 'siding' | 'main';
  occupant?: string;
  status: 'FREE' | 'OCCUPIED' | 'BLOCKED';
  signalAspect: 'GREEN' | 'AMBER' | 'RED';
}

const YARD_TRACKS: Record<string, TrackItem[]> = {
  CNB: [
    { id: 'PF-1', name: 'Platform 1 (Main UP)', type: 'platform', occupant: '12424 Dibrugarh Raj', status: 'OCCUPIED', signalAspect: 'RED' },
    { id: 'PF-2', name: 'Platform 2 (Loop UP)', type: 'platform', occupant: '12034 Shatabdi', status: 'OCCUPIED', signalAspect: 'AMBER' },
    { id: 'PF-3', name: 'Platform 3 (Main DN)', type: 'platform', status: 'FREE', signalAspect: 'GREEN' },
    { id: 'PF-4', name: 'Platform 4 (Loop DN)', type: 'platform', occupant: '12301 Howrah Raj', status: 'OCCUPIED', signalAspect: 'AMBER' },
    { id: 'PF-5', name: 'Platform 5 (Jhansi Branch)', type: 'platform', status: 'FREE', signalAspect: 'GREEN' },
    { id: 'PF-6', name: 'Platform 6 (Lucknow Chord)', type: 'platform', status: 'FREE', signalAspect: 'GREEN' },
    { id: 'PF-7', name: 'Platform 7', type: 'platform', status: 'FREE', signalAspect: 'GREEN' },
    { id: 'PF-8', name: 'Platform 8', type: 'platform', status: 'FREE', signalAspect: 'GREEN' },
    { id: 'PF-9', name: 'Platform 9', type: 'platform', status: 'FREE', signalAspect: 'GREEN' },
    { id: 'PF-10', name: 'Platform 10', type: 'platform', status: 'FREE', signalAspect: 'GREEN' },
    { id: 'PANKI-SIDING', name: 'Panki West Siding Line 1', type: 'siding', occupant: 'MNT-Kart 04', status: 'BLOCKED', signalAspect: 'RED' },
    { id: 'JUHI-YARD', name: 'Juhi Freight Marshaling Yard', type: 'siding', occupant: 'BOXN-7041 (Coal)', status: 'OCCUPIED', signalAspect: 'RED' },
    { id: 'ROOMA-DFC', name: 'Rooma DFC Exchange Loop', type: 'loop', occupant: 'BTPN-3092 (POL)', status: 'OCCUPIED', signalAspect: 'AMBER' },
  ],
  NDLS: [
    { id: 'PF-1', name: 'Platform 1 (Ajmeri Gate)', type: 'platform', occupant: '12004 Shatabdi', status: 'OCCUPIED', signalAspect: 'RED' },
    { id: 'PF-2', name: 'Platform 2', type: 'platform', status: 'FREE', signalAspect: 'GREEN' },
    { id: 'PF-3', name: 'Platform 3 (Pahar Ganj)', type: 'platform', occupant: '22436 Vande Bharat', status: 'OCCUPIED', signalAspect: 'AMBER' },
    { id: 'PF-4', name: 'Platform 4', type: 'platform', status: 'FREE', signalAspect: 'GREEN' },
    { id: 'PF-5', name: 'Platform 5', type: 'platform', status: 'FREE', signalAspect: 'GREEN' },
  ],
  GZB: [
    { id: 'PF-1', name: 'Platform 1 (Main UP)', type: 'platform', occupant: '14218 Unchahar Exp', status: 'OCCUPIED', signalAspect: 'RED' },
    { id: 'PF-2', name: 'Platform 2 (Main DN)', type: 'platform', status: 'FREE', signalAspect: 'GREEN' },
    { id: 'PF-3', name: 'Platform 3 (Moradabad Loop)', type: 'platform', status: 'FREE', signalAspect: 'GREEN' },
  ],
};

export function YardDiagramPage() {
  const [station, setStation] = useState<'CNB' | 'NDLS' | 'GZB'>('CNB');
  const [selectedTrack, setSelectedTrack] = useState<TrackItem | null>(YARD_TRACKS.CNB[0]);

  const tracks = YARD_TRACKS[station] || YARD_TRACKS.CNB;

  return (
    <div className="space-y-4">
      <SEO title="Station Yard Micro-Track Layout · RailTwin-X" noindex />

      {/* Header & Station Tabs */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-3 border-b border-[#26282C] gap-3">
        <div>
          <h1 className="text-lg font-semibold text-[#E8E8E6] flex items-center gap-2">
            <Layers className="w-4 h-4 text-[#FFB224]" />
            <span>Station Yard Micro-Track & Signal Interlocking Diagram</span>
          </h1>
          <p className="font-mono text-xs text-[#9A9DA3]">
            Relay Interlocking Panel · Platform Lines, Crossovers, Siding Loops & Live Signal Aspects
          </p>
        </div>

        {/* Station Selectors */}
        <div className="flex items-center gap-1 bg-[#15171A] p-1 border border-[#26282C]">
          {(['CNB', 'NDLS', 'GZB'] as const).map(code => (
            <button
              key={code}
              onClick={() => {
                setStation(code);
                setSelectedTrack(YARD_TRACKS[code][0]);
              }}
              className={`px-3 py-1 text-xs font-mono transition-colors ${
                station === code
                  ? 'bg-[#FFB224] text-[#0E0F11] font-bold'
                  : 'text-[#9A9DA3] hover:text-[#E8E8E6]'
              }`}
            >
              {code} Yard
            </button>
          ))}
        </div>
      </div>

      {/* Yard Schematic Panel */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
        {/* Left: SVG Physical Panel Layout */}
        <div className="lg:col-span-8 bg-[#0E0F11] border border-[#26282C] p-6 select-none relative overflow-x-auto">
          <div className="font-mono text-[10px] text-[#9A9DA3] uppercase tracking-wider mb-4 flex items-center justify-between">
            <span>INTERLOCKING SCHEMATIC · {station} STATION YARD</span>
            <div className="flex items-center gap-3">
              <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-[#3ECF8E]" /> GREEN</span>
              <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-[#FFB224]" /> CAUTION</span>
              <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-[#F0533A]" /> STOP</span>
            </div>
          </div>

          <svg viewBox="0 0 800 500" className="w-full min-w-[700px] h-[440px]">
            {/* Grid Lines */}
            <defs>
              <pattern id="yardGrid" width="20" height="20" patternUnits="userSpaceOnUse">
                <path d="M 20 0 L 0 0 0 20" fill="none" stroke="#15171A" strokeWidth="0.5" />
              </pattern>
            </defs>
            <rect width="100%" height="100%" fill="url(#yardGrid)" />

            {/* West Approach & Crossovers */}
            <line x1="40" y1="120" x2="160" y2="120" stroke="#3A3D45" strokeWidth="3" />
            <line x1="40" y1="180" x2="160" y2="180" stroke="#3A3D45" strokeWidth="3" />
            <line x1="160" y1="120" x2="220" y2="180" stroke="#3A3D45" strokeWidth="2" strokeDasharray="3 3" />
            <line x1="160" y1="180" x2="220" y2="120" stroke="#3A3D45" strokeWidth="2" strokeDasharray="3 3" />

            {/* Platform Lines 1 to 10 */}
            {tracks.filter(t => t.type === 'platform').map((t, idx) => {
              const y = 80 + idx * 36;
              const isSelected = selectedTrack?.id === t.id;
              const isOccupied = t.status === 'OCCUPIED';
              const isBlocked = t.status === 'BLOCKED';

              return (
                <g
                  key={t.id}
                  className="cursor-pointer"
                  onClick={() => setSelectedTrack(t)}
                >
                  {/* Track Line */}
                  <line
                    x1="220"
                    y1={y}
                    x2="600"
                    y2={y}
                    stroke={isSelected ? '#FFB224' : isBlocked ? '#F0533A' : isOccupied ? '#FFB224' : '#3A3D45'}
                    strokeWidth={isSelected ? 5 : 3}
                  />

                  {/* Signal Aspect Light at entrance */}
                  <circle
                    cx="200"
                    cy={y}
                    r="5"
                    fill={t.signalAspect === 'GREEN' ? '#3ECF8E' : t.signalAspect === 'AMBER' ? '#FFB224' : '#F0533A'}
                  />

                  {/* Platform Berthing Area Indicator */}
                  <rect
                    x="280"
                    y={y - 8}
                    width="260"
                    height="16"
                    fill={isOccupied ? '#FFB224' : isBlocked ? '#F0533A' : '#15171A'}
                    fillOpacity={isOccupied || isBlocked ? 0.2 : 0.8}
                    stroke={isSelected ? '#FFB224' : '#26282C'}
                    strokeWidth="1"
                  />

                  {/* Platform Label */}
                  <text x="230" y={y - 4} fill="#E8E8E6" fontSize="10" fontFamily="IBM Plex Mono" fontWeight="bold">
                    {t.id}
                  </text>

                  {/* Occupant Train Name */}
                  {t.occupant && (
                    <text x="300" y={y + 3} fill="#E8E8E6" fontSize="9" fontFamily="IBM Plex Mono" fontWeight="bold">
                      {t.occupant}
                    </text>
                  )}
                </g>
              );
            })}

            {/* East Crossovers and Approach */}
            <line x1="600" y1="120" x2="760" y2="120" stroke="#3A3D45" strokeWidth="3" />
            <line x1="600" y1="180" x2="760" y2="180" stroke="#3A3D45" strokeWidth="3" />
            <line x1="600" y1="120" x2="660" y2="180" stroke="#3A3D45" strokeWidth="2" strokeDasharray="3 3" />

            {/* Inset Yard Groups (Rooma, Juhi, Panki) */}
            {station === 'CNB' && (
              <g>
                <rect x="220" y="440" width="380" height="40" fill="#15171A" stroke="#26282C" strokeWidth="1" />
                <text x="230" y="465" fill="#9A9DA3" fontSize="10" fontFamily="IBM Plex Mono">
                  JUHI FREIGHT MARSHALING YARD · 12 SIDINGS (BOXN-7041 HELD)
                </text>
              </g>
            )}
          </svg>
        </div>

        {/* Right: Track / Signal Detail Inspector */}
        <div className="lg:col-span-4 bg-[#15171A] border border-[#26282C] p-5 font-mono text-xs space-y-4">
          <div className="flex items-center justify-between border-b border-[#26282C] pb-2">
            <span className="font-bold text-[#E8E8E6] uppercase text-sm">Track Segment Inspector</span>
            <span className="w-2 h-2 rounded-full bg-[#FFB224] animate-pulse" />
          </div>

          {selectedTrack ? (
            <div className="space-y-4">
              <div>
                <span className="text-[10px] text-[#9A9DA3] uppercase block">Track ID & Name</span>
                <span className="font-bold text-sm text-[#E8E8E6]">{selectedTrack.name}</span>
              </div>

              <div className="grid grid-cols-2 gap-3 bg-[#0E0F11] p-3 border border-[#26282C]">
                <div>
                  <span className="text-[10px] text-[#9A9DA3] block uppercase">Berth Status</span>
                  <span
                    className={`font-bold text-xs ${
                      selectedTrack.status === 'OCCUPIED'
                        ? 'text-[#FFB224]'
                        : selectedTrack.status === 'BLOCKED'
                        ? 'text-[#F0533A]'
                        : 'text-[#3ECF8E]'
                    }`}
                  >
                    {selectedTrack.status}
                  </span>
                </div>
                <div>
                  <span className="text-[10px] text-[#9A9DA3] block uppercase">Signal Aspect</span>
                  <span
                    className={`font-bold text-xs ${
                      selectedTrack.signalAspect === 'GREEN'
                        ? 'text-[#3ECF8E]'
                        : selectedTrack.signalAspect === 'AMBER'
                        ? 'text-[#FFB224]'
                        : 'text-[#F0533A]'
                    }`}
                  >
                    {selectedTrack.signalAspect}
                  </span>
                </div>
              </div>

              {selectedTrack.occupant && (
                <div className="bg-[#0E0F11] p-3 border border-[#26282C]">
                  <span className="text-[10px] text-[#9A9DA3] block uppercase">Current Berthing Occupant</span>
                  <span className="font-bold text-[#E8E8E6] text-xs mt-1 block">{selectedTrack.occupant}</span>
                </div>
              )}

              <div className="pt-2 border-t border-[#26282C] space-y-2 text-[11px] text-[#9A9DA3]">
                <div className="flex justify-between">
                  <span>Track Circuit:</span>
                  <span className="text-[#E8E8E6]">TC-{selectedTrack.id.replace('PF-', '')}A (CLEAR)</span>
                </div>
                <div className="flex justify-between">
                  <span>Point Machine Route:</span>
                  <span className="text-[#E8E8E6]">Set for Normal Reverse (Cross 14B)</span>
                </div>
                <div className="flex justify-between">
                  <span>OHE Traction:</span>
                  <span className="text-[#3ECF8E]">25kV Energized (Feeder 04)</span>
                </div>
              </div>
            </div>
          ) : (
            <div className="text-[#9A9DA3] py-8 text-center">Click any platform or track line to inspect.</div>
          )}
        </div>
      </div>
    </div>
  );
}
