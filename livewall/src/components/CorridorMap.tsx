import React, { useState } from 'react';
import type { LivePosition, CorridorStation, NetworkState } from '../lib/types';
import { useCorridorMotionEngine, getDelayColor, AnimatedTrain } from '../lib/motion';

interface CorridorMapProps {
  positions: LivePosition[];
  stations: CorridorStation[];
  network: NetworkState | null;
  isStale: boolean;
  selectedTrainNo?: string | null;
  selectedStationCode?: string | null;
  onSelectTrain?: (trainNo: string | null) => void;
  onSelectStation?: (stationCode: string) => void;
}

interface BlockSignal {
  id: string;
  km: number;
  direction: 'UP' | 'DOWN';
  aspect: 'GREEN' | 'YELLOW' | 'RED';
}

export const CorridorMap: React.FC<CorridorMapProps> = ({
  positions,
  stations,
  network,
  isStale,
  selectedTrainNo,
  selectedStationCode,
  onSelectTrain,
  onSelectStation,
}) => {
  const animatedTrains = useCorridorMotionEngine(positions, stations);
  const [hoveredTrain, setHoveredTrain] = useState<AnimatedTrain | null>(null);

  const totalCorridorKm = stations.length > 0 ? stations[stations.length - 1].km || 440 : 440;
  const startX = 90;
  const endX = 1350;
  const trackWidth = endX - startX;

  // Build a lookup map of train names from network state
  const trainNameMap = new Map<string, string>();
  if (network?.trains) {
    for (const t of network.trains) {
      trainNameMap.set(t.train_no, t.train_name);
    }
  }

  // Determine active selected train object
  const activeSelectedTrain = animatedTrains.find((t) => t.train_no === selectedTrainNo) || null;

  // Check which stations currently have an occupying train within 3.5km
  const occupiedStationCodes = new Set<string>();
  for (const t of animatedTrains) {
    for (const s of stations) {
      if (Math.abs(t.renderKm - s.km) < 3.5 || t.current_station_code?.toUpperCase() === s.code.toUpperCase()) {
        occupiedStationCodes.add(s.code.toUpperCase());
      }
    }
  }

  // Dynamic Terminal boundaries based on active corridor stations
  const term1Km = (stations[0]?.km || 0) + 8;
  const term2Km = Math.max(term1Km + 1, totalCorridorKm - 8);

  // Filter and prioritize trains for authentic Centralized Traffic Control display:
  const movingTrains: AnimatedTrain[] = [];
  const intermediateStationTrains: AnimatedTrain[] = [];
  const term1UpTrains: AnimatedTrain[] = [];
  const term1DnTrains: AnimatedTrain[] = [];
  const term2UpTrains: AnimatedTrain[] = [];
  const term2DnTrains: AnimatedTrain[] = [];

  for (const t of animatedTrains) {
    if (t.isMoving || (t.renderKm > term1Km && t.renderKm < term2Km)) {
      if (t.renderKm > term1Km && t.renderKm < term2Km && !t.isMoving) {
        intermediateStationTrains.push(t);
      } else {
        movingTrains.push(t);
      }
    } else if (t.renderKm <= term1Km) {
      if (t.direction === 'UP') term1UpTrains.push(t);
      else term1DnTrains.push(t);
    } else {
      if (t.direction === 'UP') term2UpTrains.push(t);
      else term2DnTrains.push(t);
    }
  }

  const sortBerthed = (arr: AnimatedTrain[]) =>
    arr.sort((a, b) => {
      if (a.train_no === selectedTrainNo) return -1;
      if (b.train_no === selectedTrainNo) return 1;
      return b.delay_minutes - a.delay_minutes;
    });

  sortBerthed(term1UpTrains);
  sortBerthed(term1DnTrains);
  sortBerthed(term2UpTrains);
  sortBerthed(term2DnTrains);

  const displayedTrains: AnimatedTrain[] = [
    ...movingTrains,
    ...intermediateStationTrains,
    ...term1UpTrains.slice(0, 2),
    ...term1DnTrains.slice(0, 2),
    ...term2UpTrains.slice(0, 2),
    ...term2DnTrains.slice(0, 2),
  ];

  const term1ExtraCount = Math.max(0, term1UpTrains.length - 2) + Math.max(0, term1DnTrains.length - 2);
  const term2ExtraCount = Math.max(0, term2UpTrains.length - 2) + Math.max(0, term2DnTrains.length - 2);

  // Compute neat platform loop offsets for adjacent trains
  const upDisplayed = displayedTrains.filter((t) => t.direction === 'UP').sort((a, b) => a.renderKm - b.renderKm);
  const dnDisplayed = displayedTrains.filter((t) => t.direction === 'DOWN').sort((a, b) => a.renderKm - b.renderKm);
  const trainYOffsets = new Map<string, number>();

  function calculateOffsets(list: AnimatedTrain[]) {
    for (let i = 0; i < list.length; i++) {
      let overlapCount = 0;
      for (let j = 0; j < i; j++) {
        if (Math.abs(list[i].renderKm - list[j].renderKm) < 14) {
          overlapCount++;
        }
      }
      const offset = overlapCount === 0 ? 0 : (overlapCount % 2 === 1 ? -1 : 1) * 14;
      trainYOffsets.set(list[i].train_no, offset);
    }
  }
  calculateOffsets(upDisplayed);
  calculateOffsets(dnDisplayed);

  // Generate track sleepers (cross-ties) every 13px along the track
  const sleepers: number[] = [];
  for (let x = startX; x <= endX; x += 13) {
    sleepers.push(x);
  }

  // Dynamic Automatic Block Signaling (ABS) posts between stations along the corridor
  const blockSignals: BlockSignal[] = [];
  if (stations.length > 1) {
    for (let i = 0; i < stations.length - 1; i++) {
      const k1 = stations[i].km;
      const k2 = stations[i + 1].km;
      const diff = k2 - k1;
      const points = diff > 40 ? [k1 + diff * 0.33, k1 + diff * 0.67] : [k1 + diff * 0.5];

      for (const pKm of points) {
        const skm = Math.round(pKm);
        // UP track signal
        let upAspect: 'GREEN' | 'YELLOW' | 'RED' = 'GREEN';
        for (const t of displayedTrains) {
          if (t.direction === 'UP') {
            const distAhead = t.renderKm - skm;
            if (distAhead >= 0 && distAhead < 20) {
              upAspect = 'RED';
              break;
            } else if (distAhead >= 20 && distAhead < 40) {
              upAspect = 'YELLOW';
            }
          }
        }
        blockSignals.push({ id: `sig-up-${skm}`, km: skm, direction: 'UP', aspect: upAspect });

        // DOWN track signal
        let dnAspect: 'GREEN' | 'YELLOW' | 'RED' = 'GREEN';
        for (const t of displayedTrains) {
          if (t.direction === 'DOWN') {
            const distAhead = skm - t.renderKm;
            if (distAhead >= 0 && distAhead < 20) {
              dnAspect = 'RED';
              break;
            } else if (distAhead >= 20 && distAhead < 40) {
              dnAspect = 'YELLOW';
            }
          }
        }
        blockSignals.push({ id: `sig-dn-${skm}`, km: skm, direction: 'DOWN', aspect: dnAspect });
      }
    }
  }

  // Active TSR zones
  const activeTsrs = network?.active_tsrs || [];

  return (
    <div className="corridor-map-container">
      {/* Legend Header */}
      <div className="map-legend-bar">
        <div className="legend-left">
          <span className="legend-title">
            <span style={{ color: 'var(--ochre)', fontWeight: 700 }}>[CTC]</span>
            CENTRALIZED TRAFFIC CONTROL &bull; DUAL MAINLINE CTC ({stations[0]?.code || 'START'} &lt;-&gt; {stations[stations.length - 1]?.code || 'END'} {totalCorridorKm} KM)
          </span>
          <div className="legend-item">
            <div className="legend-dot" style={{ background: 'var(--signal-green)' }} />
            <span>On-Time (&le;0m)</span>
          </div>
          <div className="legend-item">
            <div className="legend-dot" style={{ background: 'var(--signal-amber)' }} />
            <span>Delay (1-15m)</span>
          </div>
          <div className="legend-item">
            <div className="legend-dot" style={{ background: 'var(--signal-red)' }} />
            <span>Severe / Hold (&gt;15m)</span>
          </div>
          <div className="legend-item">
            <div className="legend-dot" style={{ background: 'var(--kiosk-gold)' }} />
            <span>Station Berth Occupied</span>
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
          {activeTsrs.length > 0 && (
            <span style={{ color: 'var(--signal-amber)', fontWeight: 700, fontFamily: 'var(--font-mono)' }}>
              [TSR] {activeTsrs.length} ACTIVE TSR ZONE{activeTsrs.length > 1 ? 'S' : ''}
            </span>
          )}
          {isStale && (
            <span style={{ color: 'var(--signal-amber)', fontWeight: 700 }}>
              [TELEMETRY GLIDE &bull; RECONNECTING]
            </span>
          )}
        </div>
      </div>

      {/* Main SVG CTC Canvas */}
      <svg
        viewBox="0 0 1440 330"
        className="map-svg"
        preserveAspectRatio="xMidYMid meet"
      >
        <defs>
          {/* Station Occupancy Pulse Filter */}
          <filter id="station-glow" x="-50%" y="-50%" width="200%" height="200%">
            <feGaussianBlur stdDeviation="5" result="blur" />
            <feMerge>
              <feMergeNode in="blur" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>

          {/* Train Headlight Beam Gradients */}
          <linearGradient id="headlight-up" x1="0%" y1="50%" x2="100%" y2="50%">
            <stop offset="0%" stopColor="#FFF" stopOpacity="0.8" />
            <stop offset="35%" stopColor="#F5A524" stopOpacity="0.35" />
            <stop offset="100%" stopColor="#F5A524" stopOpacity="0" />
          </linearGradient>

          <linearGradient id="headlight-dn" x1="100%" y1="50%" x2="0%" y2="50%">
            <stop offset="0%" stopColor="#FFF" stopOpacity="0.8" />
            <stop offset="35%" stopColor="#F5A524" stopOpacity="0.35" />
            <stop offset="100%" stopColor="#F5A524" stopOpacity="0" />
          </linearGradient>

          {/* TSR Caution Pattern */}
          <pattern id="tsr-stripes" width="10" height="10" patternTransform="rotate(45 0 0)" patternUnits="userSpaceOnUse">
            <line x1="0" y1="0" x2="0" y2="10" stroke="rgba(245, 165, 36, 0.4)" strokeWidth="4" />
          </pattern>
        </defs>

        {/* 1. Track Ballast Bed Background */}
        <rect
          x={startX - 10}
          y={136}
          width={trackWidth + 20}
          height={48}
          rx={4}
          fill="#101318"
          stroke="var(--line-subtle)"
          strokeWidth="1"
        />

        {/* Track direction indicators */}
        <text x={startX - 40} y={148} fill="#6F6A5C" fontFamily="var(--font-mono)" fontSize="9" fontWeight="700">UP &gt;</text>
        <text x={startX - 40} y={178} fill="#6F6A5C" fontFamily="var(--font-mono)" fontSize="9" fontWeight="700">&lt; DN</text>
        <text x={endX + 10} y={148} fill="#6F6A5C" fontFamily="var(--font-mono)" fontSize="9" fontWeight="700">&gt; UP</text>
        <text x={endX + 10} y={178} fill="#6F6A5C" fontFamily="var(--font-mono)" fontSize="9" fontWeight="700">&lt; DN</text>

        {/* 2. Track Sleepers (Cross-Ties) */}
        {sleepers.map((sx) => (
          <line
            key={`slp-${sx}`}
            x1={sx}
            y1={140}
            x2={sx}
            y2={180}
            stroke="#202530"
            strokeWidth="2"
          />
        ))}

        {/* 3. Active TSR Zones (Hatched caution bands) */}
        {activeTsrs.map((tsr, idx) => {
          const fromStn = stations.find((s) => s.code.toUpperCase() === tsr.from_code.toUpperCase());
          const toStn = stations.find((s) => s.code.toUpperCase() === tsr.to_code.toUpperCase());
          if (!fromStn || !toStn) return null;
          const x1 = startX + (Math.min(fromStn.km, toStn.km) / totalCorridorKm) * trackWidth;
          const x2 = startX + (Math.max(fromStn.km, toStn.km) / totalCorridorKm) * trackWidth;
          const width = Math.max(16, x2 - x1);

          return (
            <g key={`tsr-${idx}`}>
              <rect
                x={x1}
                y={137}
                width={width}
                height={46}
                fill="url(#tsr-stripes)"
                stroke="var(--signal-amber)"
                strokeWidth="1"
                strokeDasharray="3 3"
                opacity="0.8"
              />
              <rect
                x={x1 + width / 2 - 28}
                y={122}
                width={56}
                height={13}
                rx={2}
                fill="var(--bg-night-1)"
                stroke="var(--signal-amber)"
                strokeWidth="1"
              />
              <text
                x={x1 + width / 2}
                y={132}
                textAnchor="middle"
                fill="var(--signal-amber)"
                fontFamily="var(--font-mono)"
                fontSize="8"
                fontWeight="700"
              >
                TSR {tsr.speed_limit_kmph}k
              </text>
            </g>
          );
        })}

        {/* 4. UP Track Steel Rails (Eastbound: NDLS -> LKO, y = 145) */}
        <line x1={startX} y1={143} x2={endX} y2={143} stroke="#3D4554" strokeWidth="2" strokeLinecap="round" />
        <line x1={startX} y1={148} x2={endX} y2={148} stroke="#3D4554" strokeWidth="2" strokeLinecap="round" />

        {/* Center Cess / Inter-Track Divider */}
        <line x1={startX} y1={160} x2={endX} y2={160} stroke="#23272F" strokeWidth="1" strokeDasharray="6 4" />

        {/* 5. DOWN Track Steel Rails (Westbound: LKO -> NDLS, y = 175) */}
        <line x1={startX} y1={172} x2={endX} y2={172} stroke="#3D4554" strokeWidth="2" strokeLinecap="round" />
        <line x1={startX} y1={177} x2={endX} y2={177} stroke="#3D4554" strokeWidth="2" strokeLinecap="round" />

        {/* 6. Automatic Block Signals (ABS Signal Masts) */}
        {blockSignals.map((sig) => {
          const x = startX + (sig.km / totalCorridorKm) * trackWidth;
          const isUp = sig.direction === 'UP';
          const mastY1 = isUp ? 139 : 181;
          const mastY2 = isUp ? 129 : 191;
          const lampCenterY = isUp ? 127 : 193;
          const aspectColor =
            sig.aspect === 'RED'
              ? 'var(--signal-red)'
              : sig.aspect === 'YELLOW'
              ? 'var(--signal-amber)'
              : 'var(--signal-green)';

          return (
            <g key={sig.id} className="signal-mast">
              {/* Mast post */}
              <line x1={x} y1={mastY1} x2={x} y2={mastY2} stroke="#4A5568" strokeWidth="1.5" />
              {/* Signal housing */}
              <circle cx={x} cy={lampCenterY} r={3.5} fill="#0A0B0D" stroke="#4A5568" strokeWidth="1" />
              {/* Active Aspect Lamp */}
              <circle cx={x} cy={lampCenterY} r={2.2} fill={aspectColor} />
            </g>
          );
        })}

        {/* 7. Station Gantries, Code, Hindi Name, Km Milestones & Platforms */}
        {stations.map((stn) => {
          const x = startX + (stn.km / totalCorridorKm) * trackWidth;
          const isOccupied = occupiedStationCodes.has(stn.code.toUpperCase());
          const isSelected = selectedStationCode?.toUpperCase() === stn.code.toUpperCase();
          const gantryColor = isSelected ? 'var(--kiosk-gold)' : isOccupied ? 'var(--ochre)' : 'var(--line-strong)';

          return (
            <g
              key={stn.code}
              className={`station-gantry-group ${isSelected ? 'selected' : ''}`}
              style={{ cursor: 'pointer' }}
              onClick={() => onSelectStation?.(stn.code)}
            >
              {/* Selected Station Glowing Gantry Backdrop */}
              {isSelected && (
                <rect
                  x={x - 30}
                  y={66}
                  width={60}
                  height={176}
                  rx={4}
                  fill="rgba(255, 215, 0, 0.08)"
                  stroke="var(--kiosk-gold)"
                  strokeWidth="1.5"
                  strokeDasharray="4 2"
                />
              )}

              {/* Vertical Station Alignment Line */}
              <line
                x1={x}
                y1={isSelected ? 70 : 120}
                x2={x}
                y2={isSelected ? 240 : 200}
                stroke={gantryColor}
                strokeWidth={isSelected ? 2.5 : isOccupied ? 2 : 1}
                strokeDasharray={isSelected || isOccupied ? undefined : '2 2'}
              />

              {/* Station Loop Siding Branch Indicator for Junctions */}
              {stn.platforms && stn.platforms >= 6 && (
                <path
                  d={`M ${x - 14} 160 L ${x} 160 L ${x + 14} 160`}
                  stroke="var(--ochre)"
                  strokeWidth="1.5"
                  opacity="0.7"
                />
              )}

              {/* Station Occupied Beacon Glow Ring */}
              {(isOccupied || isSelected) && (
                <circle
                  cx={x}
                  cy={160}
                  r={isSelected ? 14 : 12}
                  fill="none"
                  stroke={isSelected ? 'var(--kiosk-gold)' : 'var(--ochre)'}
                  strokeWidth={1.5}
                  opacity="0.8"
                  filter="url(#station-glow)"
                />
              )}

              {/* Station Center Node Pip */}
              <circle
                cx={x}
                cy={160}
                r={isSelected ? 7 : isOccupied ? 6 : 4.5}
                fill={isSelected ? 'var(--kiosk-gold)' : isOccupied ? 'var(--ochre)' : 'var(--bg-night-2)'}
                stroke={isSelected ? '#FFF' : 'var(--text-secondary)'}
                strokeWidth="2"
              />

              {/* Inspecting Active Tag */}
              {isSelected && (
                <g>
                  <rect
                    x={x - 34}
                    y={70}
                    width={68}
                    height={13}
                    rx={2}
                    fill="var(--bg-night-0)"
                    stroke="var(--kiosk-gold)"
                    strokeWidth="1"
                  />
                  <text
                    x={x}
                    y={80}
                    textAnchor="middle"
                    fill="var(--kiosk-gold)"
                    fontFamily="var(--font-mono)"
                    fontSize="7.5"
                    fontWeight="800"
                  >
                    [INSPECTING]
                  </text>
                </g>
              )}

              {/* Station English Code (Above Track) */}
              <text
                x={x}
                y={isSelected ? 94 : 98}
                textAnchor="middle"
                fill={isSelected ? 'var(--kiosk-gold)' : isOccupied ? 'var(--kiosk-gold)' : 'var(--text-primary)'}
                fontFamily="var(--font-mono)"
                fontSize={isSelected ? '14' : '13'}
                fontWeight={isSelected ? '800' : '700'}
                letterSpacing="1"
              >
                {stn.code}
              </text>

              {/* Station Hindi Name (Authentic Bilingual Railway Gantry) */}
              <text
                x={x}
                y={isSelected ? 108 : 113}
                textAnchor="middle"
                fill={isSelected ? 'var(--kiosk-gold)' : 'var(--ochre)'}
                fontFamily="var(--font-hindi)"
                fontSize="10"
                fontWeight="600"
              >
                {stn.name_hi || stn.name}
              </text>

              {/* Station Km Milestone (Below Track) */}
              <text
                x={x}
                y={216}
                textAnchor="middle"
                fill={isSelected ? 'var(--kiosk-gold)' : 'var(--text-dim)'}
                fontFamily="var(--font-mono)"
                fontSize="10"
                fontWeight="600"
              >
                {stn.km} km
              </text>

              {/* Station Platforms Count Tag */}
              <g transform={`translate(${x - 16}, 224)`}>
                <rect
                  x="0"
                  y="0"
                  width="32"
                  height="12"
                  rx="2"
                  fill={isSelected ? 'var(--ochre-wash)' : 'var(--bg-night-1)'}
                  stroke={isSelected ? 'var(--kiosk-gold)' : 'var(--line-subtle)'}
                  strokeWidth="1"
                />
                <text
                  x="16"
                  y="9"
                  textAnchor="middle"
                  fill={isSelected ? 'var(--kiosk-gold)' : 'var(--text-dim)'}
                  fontFamily="var(--font-mono)"
                  fontSize="8"
                  fontWeight="600"
                >
                  {stn.platforms || 4} PF
                </text>
              </g>

              {/* Terminal Yard Depot Badges */}
              {stn.code === stations[0]?.code && term1ExtraCount > 0 && (
                <g transform={`translate(${x - 34}, 166)`}>
                  <rect x="0" y="0" width="30" height="11" rx="2" fill="var(--bg-night-0)" stroke="var(--line-subtle)" strokeWidth="0.8" />
                  <text x="15" y="8" textAnchor="middle" fill="var(--text-dim)" fontFamily="var(--font-mono)" fontSize="7.5" fontWeight="600">
                    +{term1ExtraCount} YD
                  </text>
                </g>
              )}

              {stn.code === stations[stations.length - 1]?.code && term2ExtraCount > 0 && (
                <g transform={`translate(${x + 6}, 166)`}>
                  <rect x="0" y="0" width="30" height="11" rx="2" fill="var(--bg-night-0)" stroke="var(--line-subtle)" strokeWidth="0.8" />
                  <text x="15" y="8" textAnchor="middle" fill="var(--text-dim)" fontFamily="var(--font-mono)" fontSize="7.5" fontWeight="600">
                    +{term2ExtraCount} YD
                  </text>
                </g>
              )}
            </g>
          );
        })}

        {/* 8. Motion Trails for Moving Trains */}
        {displayedTrains.map((train) => {
          if (!train.isMoving || train.trailPoints.length < 2) return null;
          const yOffset = trainYOffsets.get(train.train_no) || 0;
          const y = (train.direction === 'UP' ? 145 : 175) + yOffset;
          const color = getDelayColor(train.delay_minutes);
          const currentX = startX + train.progressFrac * trackWidth;
          const prevFrac = train.trailPoints[0];
          const prevX = startX + prevFrac * trackWidth;

          return (
            <line
              key={`trail-${train.train_no}`}
              x1={prevX}
              y1={y}
              x2={currentX}
              y2={y}
              stroke={color}
              strokeWidth="4"
              strokeOpacity="0.4"
              strokeLinecap="round"
            />
          );
        })}

        {/* 9. Realistic Locomotive & Train Capsules */}
        {displayedTrains.map((train) => {
          const x = startX + train.progressFrac * trackWidth;
          const isUp = train.direction === 'UP';
          const yOffset = trainYOffsets.get(train.train_no) || 0;
          const y = (isUp ? 145 : 175) + yOffset;
          const delayColor = getDelayColor(train.delay_minutes);
          const isRedSignal = train.inferred_signal_aspect === 'RED';
          const isSelected = selectedTrainNo === train.train_no;
          const arrow = isUp ? '>' : '<';

          // Beam length depending on speed
          const beamLen = Math.min(44, Math.max(16, (train.speed_kmh / 120) * 40));
          const beamX = isUp ? x : x - beamLen;

          return (
            <g
              key={`train-${train.train_no}`}
              style={{ cursor: 'pointer' }}
              onClick={() => onSelectTrain?.(isSelected ? null : train.train_no)}
              onMouseEnter={() => setHoveredTrain(train)}
              onMouseLeave={() => setHoveredTrain(null)}
            >
              {/* Forward Headlight Cone Beam when running at speed */}
              {train.isMoving && (
                <rect
                  x={beamX}
                  y={y - 5}
                  width={beamLen}
                  height={10}
                  fill={isUp ? 'url(#headlight-up)' : 'url(#headlight-dn)'}
                  opacity="0.75"
                />
              )}

              {/* Selection Focus Pulse Ring */}
              {isSelected && (
                <circle
                  cx={x}
                  cy={y}
                  r={16}
                  fill="none"
                  stroke="var(--ochre)"
                  strokeWidth="2"
                  strokeDasharray="4 2"
                  filter="url(#station-glow)"
                />
              )}

              {/* Red Signal Hold Halo Ring */}
              {isRedSignal && (
                <circle
                  cx={x}
                  cy={y}
                  r={13}
                  fill="none"
                  stroke="var(--signal-red)"
                  strokeWidth="1.8"
                  opacity="0.85"
                />
              )}

              {/* Locomotive Capsule Body */}
              <g transform={`translate(${x}, ${y})`}>
                <rect
                  x="-24"
                  y="-8"
                  width="48"
                  height="16"
                  rx="3"
                  fill="var(--bg-night-1)"
                  stroke={isSelected ? 'var(--kiosk-gold)' : delayColor}
                  strokeWidth={isSelected ? '2' : '1.5'}
                />

                {/* Train Number in crisp monospace */}
                <text
                  x="-2"
                  y="3.5"
                  textAnchor="middle"
                  fill="var(--text-primary)"
                  fontFamily="var(--font-mono)"
                  fontSize="9.5"
                  fontWeight="700"
                >
                  {train.train_no}
                </text>

                {/* Direction arrow pointer */}
                <text
                  x={isUp ? '16' : '-17'}
                  y="3.5"
                  textAnchor="middle"
                  fill={delayColor}
                  fontFamily="var(--font-mono)"
                  fontSize="8"
                  fontWeight="700"
                >
                  {arrow}
                </text>
              </g>

              {/* Speed & Aspect Pill */}
              <g transform={`translate(${x}, ${isUp ? y - 16 : y + 17})`}>
                <rect
                  x="-18"
                  y="-6"
                  width="36"
                  height="11"
                  rx="2"
                  fill="var(--bg-night-0)"
                  stroke="var(--line-subtle)"
                  strokeWidth="0.8"
                  opacity="0.9"
                />
                <text
                  x="0"
                  y="2.5"
                  textAnchor="middle"
                  fill={train.isMoving ? 'var(--text-secondary)' : 'var(--signal-red)'}
                  fontFamily="var(--font-mono)"
                  fontSize="7.5"
                  fontWeight="600"
                >
                  {train.isMoving ? `${train.speed_kmh}k` : 'HALT'}
                </text>
              </g>
            </g>
          );
        })}
      </svg>

      {/* Interactive Selected Train Telemetry HUD Card */}
      {(activeSelectedTrain || hoveredTrain) && (
        <div className="train-hud-overlay">
          {(() => {
            const t = activeSelectedTrain || hoveredTrain!;
            const delayCol = getDelayColor(t.delay_minutes);
            const trainName = trainNameMap.get(t.train_no) || 'Superfast Express';

            return (
              <>
                <div className="train-hud-header">
                  <div className="train-hud-title">
                    <span>#{t.train_no}</span>
                    <span style={{ color: 'var(--text-primary)', fontSize: '11px', fontWeight: 600 }}>
                      {trainName}
                    </span>
                  </div>
                  {activeSelectedTrain && (
                    <button
                      className="train-hud-close"
                      onClick={() => onSelectTrain?.(null)}
                      title="Close HUD"
                    >
                      [X]
                    </button>
                  )}
                </div>

                <div className="train-hud-grid">
                  <div>
                    <span style={{ color: 'var(--text-dim)' }}>Direction: </span>
                    <span style={{ color: 'var(--text-primary)', fontWeight: 700 }}>
                      {t.direction === 'UP'
                        ? `UP (${stations[0]?.code || 'START'} → ${stations[stations.length - 1]?.code || 'END'})`
                        : `DN (${stations[stations.length - 1]?.code || 'END'} → ${stations[0]?.code || 'START'})`}
                    </span>
                  </div>
                  <div>
                    <span style={{ color: 'var(--text-dim)' }}>Speed: </span>
                    <span style={{ color: 'var(--text-primary)', fontWeight: 700 }}>
                      {t.speed_kmh} km/h
                    </span>
                  </div>
                  <div>
                    <span style={{ color: 'var(--text-dim)' }}>Corridor Km: </span>
                    <span style={{ color: 'var(--kiosk-gold)', fontWeight: 600 }}>
                      {t.renderKm.toFixed(1)} km / {totalCorridorKm} km
                    </span>
                  </div>
                  <div>
                    <span style={{ color: 'var(--text-dim)' }}>Delay: </span>
                    <span style={{ color: delayCol, fontWeight: 700 }}>
                      {t.delay_minutes > 0 ? `+${Math.round(t.delay_minutes)}m` : 'ON TIME'}
                    </span>
                  </div>
                  <div>
                    <span style={{ color: 'var(--text-dim)' }}>Aspect: </span>
                    <span style={{
                      color: t.inferred_signal_aspect === 'RED'
                        ? 'var(--signal-red)'
                        : t.inferred_signal_aspect === 'YELLOW'
                        ? 'var(--signal-amber)'
                        : 'var(--signal-green)',
                      fontWeight: 700,
                    }}>
                      ● {t.inferred_signal_aspect}
                    </span>
                  </div>
                  <div>
                    <span style={{ color: 'var(--text-dim)' }}>Next Berth: </span>
                    <span style={{ color: 'var(--text-primary)' }}>
                      {t.next_station_code || '--'}
                    </span>
                  </div>
                </div>
              </>
            );
          })()}
        </div>
      )}
    </div>
  );
};
