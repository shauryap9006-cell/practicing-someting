import React, { useState, useEffect } from 'react';
import { AspectLamp, AspectType } from './AspectLamp';

export interface SpineTrain {
  id: string;
  trainNo: string;
  trainName?: string;
  km: number;
  delayMin: number;
  aspect?: AspectType;
  direction?: 'UP' | 'DN';
  confidenceP10Km?: number;
  confidenceP90Km?: number;
  speedKmh?: number;
  nextStation?: string;
}

export const CORRIDOR_CHAINAGE_STATIONS = [
  { code: 'NDLS', name: 'New Delhi', km: 0 },
  { code: 'GZB', name: 'Ghaziabad', km: 25 },
  { code: 'ALJN', name: 'Aligarh', km: 126 },
  { code: 'TDL', name: 'Tundla', km: 204 },
  { code: 'ETW', name: 'Etawah', km: 296 },
  { code: 'CNB', name: 'Kanpur Central', km: 435 },
  { code: 'PRYJ', name: 'Prayagraj', km: 632 },
  { code: 'DDU', name: 'Pt. Deen Dayal', km: 785 },
];

export const TOTAL_CORRIDOR_KM = 785;

export const DEFAULT_SPINE_TRAINS: SpineTrain[] = [
  {
    id: '12034',
    trainNo: '12034',
    trainName: 'Kanpur Shatabdi',
    km: 140,
    delayMin: 18,
    aspect: 'caution',
    direction: 'UP',
    confidenceP10Km: 120,
    confidenceP90Km: 165,
    speedKmh: 110,
    nextStation: 'ALJN',
  },
  {
    id: '22436',
    trainNo: '22436',
    trainName: 'Vande Bharat',
    km: 260,
    delayMin: 2,
    aspect: 'clear',
    direction: 'DN',
    confidenceP10Km: 250,
    confidenceP90Km: 270,
    speedKmh: 130,
    nextStation: 'ETW',
  },
  {
    id: '12301',
    trainNo: '12301',
    trainName: 'Howrah Rajdhani',
    km: 610,
    delayMin: 27,
    aspect: 'caution',
    direction: 'UP',
    confidenceP10Km: 580,
    confidenceP90Km: 645,
    speedKmh: 95,
    nextStation: 'PRYJ',
  },
  {
    id: '12424',
    trainNo: '12424',
    trainName: 'Dibrugarh Rajdhani',
    km: 430,
    delayMin: 45,
    aspect: 'restrict',
    direction: 'DN',
    confidenceP10Km: 390,
    confidenceP90Km: 460,
    speedKmh: 65,
    nextStation: 'CNB',
  },
];

interface CorridorSpineProps {
  density?: 'hero' | 'panel' | 'inline';
  trains?: SpineTrain[];
  selectedTrainId?: string;
  onSelectTrain?: (train: SpineTrain) => void;
  showCones?: boolean;
  highlightKm?: number;
  highlightTrainNo?: string;
  interactive?: boolean;
  animateCrawl?: boolean;
  className?: string;
}

export const CorridorSpine: React.FC<CorridorSpineProps> = ({
  density = 'panel',
  trains: initialTrains,
  selectedTrainId,
  onSelectTrain,
  showCones = true,
  highlightKm,
  highlightTrainNo,
  interactive = true,
  animateCrawl = false,
  className = '',
}) => {
  const [trains, setTrains] = useState<SpineTrain[]>(initialTrains || DEFAULT_SPINE_TRAINS);
  const [hoveredTrain, setHoveredTrain] = useState<SpineTrain | null>(null);

  useEffect(() => {
    if (initialTrains) {
      setTrains(initialTrains);
    }
  }, [initialTrains]);

  // Subtle crawling animation for hero demo
  useEffect(() => {
    if (!animateCrawl) return;
    const interval = setInterval(() => {
      setTrains(prev =>
        prev.map(t => {
          const delta = t.direction === 'UP' ? -1.5 : 1.5;
          let nextKm = t.km + delta;
          if (nextKm < 10) nextKm = TOTAL_CORRIDOR_KM - 20;
          if (nextKm > TOTAL_CORRIDOR_KM - 10) nextKm = 20;
          return { ...t, km: nextKm };
        })
      );
    }, 2000);
    return () => clearInterval(interval);
  }, [animateCrawl]);

  const getKmPercent = (km: number) => {
    const clamped = Math.max(0, Math.min(TOTAL_CORRIDOR_KM, km));
    return (clamped / TOTAL_CORRIDOR_KM) * 100;
  };

  const getAspect = (t: SpineTrain): AspectType => {
    if (t.aspect) return t.aspect;
    if (t.delayMin <= 5) return 'clear';
    if (t.delayMin <= 25) return 'caution';
    return 'restrict';
  };

  return (
    <div
      className={`relative w-full select-none ${
        density === 'hero'
          ? 'py-8 px-4 sm:px-8 bg-[#101216] border border-[#23272F] rounded-lg'
          : density === 'inline'
          ? 'py-3 px-2 bg-[#0A0B0D] border-y border-[#23272F]'
          : 'py-6 px-4 bg-[#101216] border border-[#23272F] rounded-md'
      } ${className}`}
    >
      {/* Top Header Label in Panel / Hero modes */}
      {density === 'hero' && (
        <div className="flex items-center justify-between mb-8 pb-3 border-b border-[#23272F]">
          <div className="flex items-center gap-3">
            <span className="w-2 h-2 rounded-full bg-[#F5A524] shadow-[0_0_8px_rgba(245,165,36,0.6)] animate-pulse" />
            <span className="font-mono text-xs uppercase tracking-widest text-[#E9EBEE] font-bold">
              NCR TRUNK CORRIDOR TELEMETRY · 785 KM LIVE CHAINAGE
            </span>
          </div>
          <div className="flex items-center gap-4 font-mono text-xs text-[#A3ABB6]">
            <span>NDLS (KM 0) ─── DDU (KM 785)</span>
            <span className="text-[#3DDC97]">● {trains.length} FLEET ACTIVE</span>
          </div>
        </div>
      )}

      {/* Main Track Area */}
      <div className="relative w-full my-6">
        {/* Track Line (Physical Steel Rail Visual) */}
        <div className="relative h-2 w-full flex items-center">
          {/* Base hairline */}
          <div className="absolute inset-x-0 h-[2px] bg-[#2E333D]" />
          {/* Signal active flow pulse */}
          <div className="absolute inset-x-0 h-[1px] bg-gradient-to-r from-transparent via-[#F5A524]/40 to-transparent animate-pulse" />
        </div>

        {/* Station Ticks on Chainage */}
        <div className="relative w-full h-0">
          {CORRIDOR_CHAINAGE_STATIONS.map(stn => {
            const pct = getKmPercent(stn.km);
            const isHighlight =
              highlightKm !== undefined && Math.abs(highlightKm - stn.km) < 30;

            return (
              <div
                key={stn.code}
                className="absolute -top-3 transform -translate-x-1/2 flex flex-col items-center group cursor-default"
                style={{ left: `${pct}%` }}
              >
                {/* Station Node Ring */}
                <div
                  className={`w-3.5 h-3.5 rounded-full border-2 transition-colors ${
                    isHighlight
                      ? 'bg-[#F5A524] border-[#E9EBEE] shadow-[0_0_10px_#F5A524]'
                      : 'bg-[#15181D] border-[#6B7480] group-hover:border-[#E9EBEE]'
                  }`}
                />

                {/* Station Code & KM */}
                <div className="mt-2 text-center whitespace-nowrap">
                  <span
                    className={`block font-mono text-[11px] font-bold ${
                      isHighlight
                        ? 'text-[#F5A524]'
                        : 'text-[#E9EBEE] group-hover:text-[#F5A524]'
                    }`}
                  >
                    {stn.code}
                  </span>
                  {density !== 'inline' && (
                    <span className="block font-mono text-[9px] text-[#6B7480]">
                      {stn.km}k
                    </span>
                  )}
                </div>
              </div>
            );
          })}
        </div>

        {/* Dynamic Train Chips on Track */}
        <div className="relative w-full pt-8 min-h-[70px]">
          {trains.map((train, idx) => {
            const pct = getKmPercent(train.km);
            const aspect = getAspect(train);
            const isSelected = selectedTrainId === train.id || highlightTrainNo === train.trainNo;
            const p10Pct = train.confidenceP10Km ? getKmPercent(train.confidenceP10Km) : Math.max(0, pct - 5);
            const p90Pct = train.confidenceP90Km ? getKmPercent(train.confidenceP90Km) : Math.min(100, pct + 5);
            const coneWidth = Math.max(3, p90Pct - p10Pct);
            const coneLeft = Math.min(p10Pct, pct);

            // Stagger chips vertically if multiple trains are close
            const rowOffset = idx % 2 === 0 ? 0 : 32;

            return (
              <div
                key={train.id || train.trainNo}
                className="absolute transform -translate-x-1/2 transition-all duration-300"
                style={{ left: `${pct}%`, top: `${rowOffset}px` }}
              >
                {/* P10-P90 Uncertainty Cone Taper */}
                {showCones && (
                  <div
                    className="absolute -top-10 h-3 bg-gradient-to-r from-transparent via-[rgba(108,159,255,0.22)] to-transparent rounded pointer-events-none"
                    style={{
                      left: `${(coneLeft - pct) * 2}px`,
                      width: `${coneWidth * 5}px`,
                    }}
                    title={`P10–P90 Confidence Cone: km ${train.confidenceP10Km || train.km - 20} - ${
                      train.confidenceP90Km || train.km + 20
                    }`}
                  />
                )}

                {/* Train Pointer Arrow */}
                <div
                  className={`w-0 h-0 border-l-[4px] border-l-transparent border-r-[4px] border-r-transparent border-b-[6px] mx-auto mb-1 ${
                    aspect === 'clear'
                      ? 'border-b-[#3DDC97]'
                      : aspect === 'restrict'
                      ? 'border-b-[#F4506A]'
                      : 'border-b-[#F5A524]'
                  }`}
                />

                {/* Train Chip Button */}
                <button
                  type="button"
                  disabled={!interactive}
                  onClick={() => onSelectTrain?.(train)}
                  onMouseEnter={() => setHoveredTrain(train)}
                  onMouseLeave={() => setHoveredTrain(null)}
                  className={`group relative flex items-center gap-1.5 px-2 py-1 bg-[#15181D] border font-mono rounded-sm transition-all duration-120 whitespace-nowrap shadow-lg ${
                    isSelected
                      ? 'border-[#F5A524] ring-1 ring-[#F5A524] bg-[#1B1F26]'
                      : 'border-[#2E333D] hover:border-[#A3ABB6] hover:bg-[#1B1F26]'
                  }`}
                >
                  <span className="font-bold text-[#E9EBEE] text-xs">
                    {train.trainNo}
                  </span>

                  <AspectLamp
                    aspect={aspect}
                    label={train.delayMin <= 0 ? 'OT' : `+${train.delayMin}m`}
                    size="xs"
                  />

                  {train.direction && (
                    <span className="text-[9px] text-[#6B7480] uppercase">
                      {train.direction === 'UP' ? '↑' : '↓'}
                    </span>
                  )}
                </button>
              </div>
            );
          })}
        </div>
      </div>

      {/* Hovered Train Detail Tooltip */}
      {hoveredTrain && (
        <div className="mt-8 pt-3 border-t border-[#23272F] flex items-center justify-between text-xs font-mono text-[#A3ABB6]">
          <div className="flex items-center gap-3">
            <span className="font-bold text-[#E9EBEE]">{hoveredTrain.trainNo} {hoveredTrain.trainName}</span>
            <span>Chainage: KM {hoveredTrain.km}</span>
            {hoveredTrain.speedKmh && <span>Speed: {hoveredTrain.speedKmh} km/h</span>}
          </div>
          <div className="flex items-center gap-2">
            <span>Confidence Range: KM {hoveredTrain.confidenceP10Km || hoveredTrain.km - 15} – KM {hoveredTrain.confidenceP90Km || hoveredTrain.km + 20}</span>
            <AspectLamp
              aspect={getAspect(hoveredTrain)}
              label={hoveredTrain.delayMin <= 0 ? 'CLEAR (ON TIME)' : `+${hoveredTrain.delayMin} MIN DELAY`}
              size="xs"
            />
          </div>
        </div>
      )}
    </div>
  );
};
