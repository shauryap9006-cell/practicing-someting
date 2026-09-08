import React, { useState, useMemo, useRef, useCallback } from 'react';
import type { LivePosition, NetworkState, StationMeta } from '@railtwin/shared-types';

interface IndiaMapProps {
  positions: LivePosition[];
  stations: StationMeta[];
  network: NetworkState | null;
  selectedTrainNo: string | null;
  selectedStationCode: string | null;
  onSelectTrain: (trainNo: string) => void;
  onSelectStation: (stationCode: string) => void;
  activeCorridorId?: string;
  onSelectCorridor?: (corridorId: string) => void;
}

// Bounding box for India railway network coordinates
const MIN_LON = 68.0;
const MAX_LON = 95.5;
const MIN_LAT = 8.0;
const MAX_LAT = 34.5;
const SVG_WIDTH = 1000;
const SVG_HEIGHT = 1100;

function projectCoords(lat: number, lon: number): [number, number] {
  // Equirectangular / Mercator projection mapping
  const clampedLon = Math.max(MIN_LON, Math.min(MAX_LON, lon));
  const clampedLat = Math.max(MIN_LAT, Math.min(MAX_LAT, lat));
  const x = ((clampedLon - MIN_LON) / (MAX_LON - MIN_LON)) * (SVG_WIDTH - 120) + 60;
  const y = ((MAX_LAT - clampedLat) / (MAX_LAT - MIN_LAT)) * (SVG_HEIGHT - 120) + 60;
  return [x, y];
}

// Major railway trunk segments connecting key junction station codes across India (verified in DB)
const TRUNK_TRACKS: Array<[string, string]> = [
  // Northern & Eastern Mainline
  ['NDLS', 'GZB'], ['GZB', 'ALJN'], ['ALJN', 'TDL'], ['TDL', 'ETW'],
  ['ETW', 'CNB'], ['CNB', 'ON'], ['ON', 'LKO'], ['CNB', 'PRYJ'],
  ['PRYJ', 'BSB'], ['BSB', 'DDU'], ['DDU', 'GAYA'], ['GAYA', 'DHN'],
  ['DHN', 'ASN'], ['ASN', 'HWH'], ['HWH', 'SDAH'],
  ['DDU', 'DNR'], ['DNR', 'PNBE'], ['PNBE', 'BJU'], ['BJU', 'SPJ'], ['SPJ', 'DBG'],
  ['LKO', 'GKP'], ['GKP', 'CPR'], ['CPR', 'PNBE'],
  ['LKO', 'BE'], ['BE', 'MB'], ['MB', 'MTC'], ['MTC', 'GZB'],
  ['MTC', 'SRE'], ['SRE', 'HW'], ['HW', 'DDN'],

  // Northwest & Punjab / Jammu
  ['NDLS', 'UMB'], ['UMB', 'CDG'], ['UMB', 'LDH'], ['LDH', 'JUC'],
  ['JUC', 'ASR'], ['LDH', 'JAT'], ['JAT', 'SVDK'],

  // Western Trunk & Rajasthan
  ['NDLS', 'MTJ'], ['MTJ', 'KOTA'], ['KOTA', 'RTM'], ['RTM', 'BRC'],
  ['BRC', 'ST'], ['ST', 'MMCT'], ['MMCT', 'CSMT'],
  ['NDLS', 'JP'], ['JP', 'AII'], ['AII', 'ADI'], ['ADI', 'BRC'],
  ['JP', 'JU'], ['JU', 'BKN'],

  // Central Trunk (Grand Trunk: Delhi -> Chennai)
  ['MTJ', 'AGC'], ['AGC', 'GWL'], ['GWL', 'VGLJ'], ['VGLJ', 'BPL'],
  ['BPL', 'RKMP'], ['RKMP', 'NGP'], ['NGP', 'KZJ'], ['KZJ', 'BZA'],
  ['BZA', 'MAS'],

  // Hyderabad Connections
  ['KZJ', 'SC'], ['SC', 'HYB'], ['HYB', 'GTL'],

  // Mumbai - Howrah Trunk (Central India)
  ['CSMT', 'IGP'], ['IGP', 'NK'], ['NK', 'MMR'], ['MMR', 'BSL'],
  ['BSL', 'NGP'], ['NGP', 'DURG'], ['DURG', 'R'], ['R', 'BSP'],
  ['BSP', 'ROU'], ['ROU', 'TATA'], ['TATA', 'KGP'], ['KGP', 'HWH'],

  // Southern Network (Mumbai -> Chennai / Bangalore / Kerala)
  ['CSMT', 'PUNE'], ['PUNE', 'SUR'], ['SUR', 'GTL'], ['GTL', 'RU'],
  ['RU', 'MAS'], ['RU', 'TPTY'],
  ['GTL', 'SBC'], ['SBC', 'YPR'], ['SBC', 'MYS'], ['GTL', 'UBL'],
  ['SBC', 'SA'], ['SA', 'ED'], ['ED', 'CBE'], ['CBE', 'PGT'],
  ['PGT', 'TCR'], ['TCR', 'ERS'], ['ERS', 'QLN'], ['QLN', 'TVC'],
  ['ED', 'TPJ'], ['TPJ', 'MDU'], ['PGT', 'CLT'], ['CLT', 'CAN'],

  // East Coast (Kolkata -> Chennai)
  ['HWH', 'KGP'], ['KGP', 'CTC'], ['CTC', 'BBS'], ['BBS', 'KUR'],
  ['KUR', 'PURI'], ['KUR', 'VSKP'], ['VSKP', 'RJY'], ['RJY', 'BZA'],

  // Northeast Trunk
  ['PNBE', 'BJU'], ['BJU', 'NJP'], ['NJP', 'GHY'], ['GHY', 'DBRG'],
];

// Key Metropolitan & Zonal Hubs labeled prominently on Pan-India zoom
const NATIONAL_HUBS = new Set([
  'NDLS', 'CSMT', 'HWH', 'MAS', 'SBC', 'HYB', 'GHY', 'SVDK',
  'ADI', 'BPL', 'NGP', 'LKO', 'CNB', 'PRYJ', 'PNBE', 'VSKP',
  'TVC', 'JAT', 'ASR', 'JP', 'RTM', 'KOTA', 'BBS', 'PUNE'
]);

// Stylized silhouette of India mainland territory
const INDIA_COAST_PATH = `
  M 270,120 L 320,110 L 350,150 L 400,165 L 430,220 L 460,240 
  L 520,245 L 560,270 L 610,275 L 670,300 L 730,300 L 760,280
  L 830,290 L 890,320 L 920,380 L 880,420 L 840,430 L 780,440
  L 740,470 L 710,510 L 650,560 L 610,630 L 560,710 L 520,780
  L 470,840 L 430,920 L 380,990 L 350,1040 L 340,1010 L 330,950
  L 320,890 L 310,830 L 280,780 L 250,720 L 220,670 L 200,640
  L 180,590 L 150,560 L 130,520 L 140,480 L 180,440 L 200,380
  L 220,320 L 230,250 L 240,180 Z
`;

export const IndiaMap: React.FC<IndiaMapProps> = ({
  positions,
  stations,
  network,
  selectedTrainNo,
  selectedStationCode,
  onSelectTrain,
  onSelectStation,
  activeCorridorId = 'ALL-INDIA',
  onSelectCorridor,
}) => {
  const containerRef = useRef<HTMLDivElement>(null);

  // Pan and Zoom Transform State
  const [zoom, setZoom] = useState<number>(1.0);
  const [pan, setPan] = useState<{ x: number; y: number }>({ x: 0, y: 0 });
  const [isDragging, setIsDragging] = useState<boolean>(false);
  const [dragStart, setDragStart] = useState<{ x: number; y: number }>({ x: 0, y: 0 });

  // Hover Tooltip State
  const [hoveredEntity, setHoveredEntity] = useState<{
    type: 'train' | 'station';
    x: number;
    y: number;
    title: string;
    subtitle: string;
    details: Array<{ label: string; val: string; color?: string }>;
  } | null>(null);

  // Station Code -> Station Lookup Map
  const stationMap = useMemo(() => {
    const map = new Map<string, StationMeta>();
    for (const s of stations) {
      map.set(s.code.toUpperCase(), s);
    }
    return map;
  }, [stations]);

  // Train detail mapping from network state
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

  // Station occupancy count (trains currently at station)
  const stationOccupancyMap = useMemo(() => {
    const map = new Map<string, number>();
    for (const p of positions) {
      if (p.current_station_code) {
        const code = p.current_station_code.toUpperCase();
        map.set(code, (map.get(code) || 0) + 1);
      }
    }
    return map;
  }, [positions]);

  // Pre-project station positions to SVG space
  const stationPositions = useMemo(() => {
    const map = new Map<string, { x: number; y: number; meta: StationMeta }>();
    for (const s of stations) {
      if (s.lat && s.lon) {
        const [x, y] = projectCoords(s.lat, s.lon);
        map.set(s.code.toUpperCase(), { x, y, meta: s });
      }
    }
    return map;
  }, [stations]);

  // Handle Zoom In / Out / Reset
  const handleZoom = (factor: number) => {
    setZoom((prev) => Math.min(6.0, Math.max(0.7, prev * factor)));
  };

  const handleReset = () => {
    setZoom(1.0);
    setPan({ x: 0, y: 0 });
  };

  // Focus camera on specific coordinates
  const focusOnPoint = useCallback((x: number, y: number, targetZoom = 2.5) => {
    const svgCenterX = SVG_WIDTH / 2;
    const svgCenterY = SVG_HEIGHT / 2;
    setZoom(targetZoom);
    setPan({
      x: svgCenterX - x * targetZoom,
      y: svgCenterY - y * targetZoom,
    });
  }, []);

  const prevStationRef = useRef<string | null>(null);

  // Center on selected station if changed externally by user (skip auto-zoom on initial mount so Pan-India view is preserved)
  React.useEffect(() => {
    if (prevStationRef.current === null) {
      prevStationRef.current = selectedStationCode;
      return;
    }
    if (selectedStationCode && selectedStationCode !== prevStationRef.current) {
      prevStationRef.current = selectedStationCode;
      const pos = stationPositions.get(selectedStationCode.toUpperCase());
      if (pos) {
        focusOnPoint(pos.x, pos.y, 2.2);
      }
    }
  }, [selectedStationCode, stationPositions, focusOnPoint]);

  // Center on selected train if changed externally
  React.useEffect(() => {
    if (selectedTrainNo) {
      const p = positions.find((item) => item.train_no === selectedTrainNo);
      if (p && p.lat && p.lng) {
        const [x, y] = projectCoords(p.lat, p.lng);
        focusOnPoint(x, y, 3.0);
      }
    }
  }, [selectedTrainNo, positions, focusOnPoint]);

  // Mouse Drag Pan Events
  const handleMouseDown = (e: React.MouseEvent) => {
    if (e.button !== 0) return;
    setIsDragging(true);
    setDragStart({ x: e.clientX - pan.x, y: e.clientY - pan.y });
  };

  const handleMouseMove = (e: React.MouseEvent) => {
    if (isDragging) {
      setPan({
        x: e.clientX - dragStart.x,
        y: e.clientY - dragStart.y,
      });
    }
  };

  const handleMouseUp = () => {
    setIsDragging(false);
  };

  // Mouse Wheel Zoom Event
  const handleWheel = (e: React.WheelEvent) => {
    e.preventDefault();
    const zoomDelta = e.deltaY < 0 ? 1.15 : 0.87;
    setZoom((prev) => Math.min(6.0, Math.max(0.7, prev * zoomDelta)));
  };

  // Delay Color Helper (Strictly Ochre/Gold/Green/Amber/Crimson — NO BLUE)
  const getTrainColor = (p: LivePosition) => {
    if (p.signal_hold_active) return 'var(--ochre)';
    const delay = p.delay_minutes || 0;
    if (delay <= 10) return 'var(--signal-green)';
    if (delay <= 30) return 'var(--signal-amber)';
    return 'var(--signal-red)';
  };

  return (
    <div
      className="india-map-container"
      ref={containerRef}
      onMouseDown={handleMouseDown}
      onMouseMove={handleMouseMove}
      onMouseUp={handleMouseUp}
      onMouseLeave={handleMouseUp}
      onWheel={handleWheel}
      style={{ cursor: isDragging ? 'grabbing' : 'grab' }}
    >
      {/* Top HUD: Corridor Quick Selector */}
      <div className="map-hud-overlay">
        <div className="map-corridor-pills">
          {[
            { id: 'ALL-INDIA', label: 'PAN-INDIA (1000+ FLEET)' },
            { id: 'NDLS-LKO', label: 'DELHI–LUCKNOW (440KM)' },
            { id: 'NDLS-HWH', label: 'DELHI–HOWRAH (1447KM)' },
            { id: 'NDLS-CSMT', label: 'DELHI–MUMBAI (1384KM)' },
            { id: 'CSMT-MAS', label: 'MUMBAI–CHENNAI (1280KM)' },
            { id: 'NDLS-MAS', label: 'GRAND TRUNK (2182KM)' },
            { id: 'HWH-MAS', label: 'EAST COAST (1660KM)' },
          ].map((c) => (
            <button
              key={c.id}
              className={`corridor-pill-btn ${activeCorridorId === c.id ? 'active' : ''}`}
              onClick={(e) => {
                e.stopPropagation();
                onSelectCorridor?.(c.id);
                if (c.id === 'ALL-INDIA') {
                  handleReset();
                } else if (c.id === 'NDLS-LKO') {
                  const ndls = stationPositions.get('NDLS');
                  const lko = stationPositions.get('LKO');
                  if (ndls && lko) focusOnPoint((ndls.x + lko.x) / 2, (ndls.y + lko.y) / 2, 2.4);
                } else if (c.id === 'NDLS-HWH') {
                  const ndls = stationPositions.get('NDLS');
                  const hwh = stationPositions.get('HWH');
                  if (ndls && hwh) focusOnPoint((ndls.x + hwh.x) / 2, (ndls.y + hwh.y) / 2, 1.8);
                } else if (c.id === 'NDLS-CSMT') {
                  const ndls = stationPositions.get('NDLS');
                  const csmt = stationPositions.get('CSMT');
                  if (ndls && csmt) focusOnPoint((ndls.x + csmt.x) / 2, (ndls.y + csmt.y) / 2, 1.8);
                } else if (c.id === 'CSMT-MAS') {
                  const csmt = stationPositions.get('CSMT');
                  const mas = stationPositions.get('MAS');
                  if (csmt && mas) focusOnPoint((csmt.x + mas.x) / 2, (csmt.y + mas.y) / 2, 2.0);
                } else if (c.id === 'NDLS-MAS') {
                  const ndls = stationPositions.get('NDLS');
                  const mas = stationPositions.get('MAS');
                  if (ndls && mas) focusOnPoint((ndls.x + mas.x) / 2, (ndls.y + mas.y) / 2, 1.4);
                } else if (c.id === 'HWH-MAS') {
                  const hwh = stationPositions.get('HWH');
                  const mas = stationPositions.get('MAS');
                  if (hwh && mas) focusOnPoint((hwh.x + mas.x) / 2, (hwh.y + mas.y) / 2, 1.7);
                }
              }}
            >
              {c.label}
            </button>
          ))}
        </div>
      </div>

      {/* Bottom Left: Navigation & Zoom HUD */}
      <div className="map-zoom-hud">
        <button className="map-hud-btn" onClick={() => handleZoom(1.3)} title="Zoom In">
          [+]
        </button>
        <button className="map-hud-btn" onClick={() => handleZoom(0.77)} title="Zoom Out">
          [-]
        </button>
        <button className="map-hud-btn" onClick={handleReset} title="Reset Pan-India View">
          [FIT INDIA]
        </button>
      </div>

      {/* Bottom Right: Status Legend HUD */}
      <div className="map-legend-hud">
        <div style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
          <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: 'var(--signal-green)', display: 'inline-block' }} />
          <span>&lt;10m On-Time</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
          <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: 'var(--signal-amber)', display: 'inline-block' }} />
          <span>10–30m Minor</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
          <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: 'var(--signal-red)', display: 'inline-block' }} />
          <span>&gt;30m Delayed</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
          <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: 'var(--ochre)', display: 'inline-block' }} />
          <span>Hold / Station</span>
        </div>
      </div>

      {/* Floating Entity Hover Tooltip */}
      {hoveredEntity && (
        <div
          className="map-tooltip"
          style={{
            left: `${Math.min(window.innerWidth - 300, hoveredEntity.x + 15)}px`,
            top: `${Math.min(window.innerHeight - 150, hoveredEntity.y + 15)}px`,
          }}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
            <span style={{ color: 'var(--kiosk-gold)', fontWeight: 800 }}>{hoveredEntity.title}</span>
            <span
              style={{
                fontSize: '8.5px',
                padding: '1px 4px',
                borderRadius: '2px',
                background: 'var(--bg-night-0)',
                color: hoveredEntity.type === 'train' ? 'var(--signal-green)' : 'var(--ochre)',
                fontWeight: 700,
              }}
            >
              {hoveredEntity.type.toUpperCase()}
            </span>
          </div>
          <div style={{ color: 'var(--text-secondary)', fontSize: '10px', marginBottom: '6px' }}>
            {hoveredEntity.subtitle}
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '2px', borderTop: '1px solid var(--line-subtle)', paddingTop: '4px' }}>
            {hoveredEntity.details.map((d, i) => (
              <div key={i} style={{ display: 'flex', justifyContent: 'space-between', fontSize: '9.5px' }}>
                <span style={{ color: 'var(--text-dim)' }}>{d.label}:</span>
                <span style={{ color: d.color || 'var(--text-primary)', fontWeight: 700 }}>{d.val}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Main Interactive Pan-India SVG Canvas */}
      <svg
        className="india-map-svg"
        viewBox={`0 0 ${SVG_WIDTH} ${SVG_HEIGHT}`}
        preserveAspectRatio="xMidYMid meet"
      >
        <defs>
          {/* Subtle Glow Filter for Selected Train & Active Junctions */}
          <filter id="map-glow" x="-20%" y="-20%" width="140%" height="140%">
            <feGaussianBlur stdDeviation="3" result="blur" />
            <feComposite in="SourceGraphic" in2="blur" operator="over" />
          </filter>

          <pattern id="map-grid" width="40" height="40" patternUnits="userSpaceOnUse">
            <path d="M 40 0 L 0 0 0 40" fill="none" stroke="rgba(35, 39, 47, 0.25)" strokeWidth="1" />
          </pattern>
        </defs>

        <g transform={`translate(${pan.x}, ${pan.y}) scale(${zoom})`}>
          {/* Background Technical Grid */}
          <rect x="0" y="0" width={SVG_WIDTH} height={SVG_HEIGHT} fill="url(#map-grid)" />

          {/* 1. Indian Subcontinent Geographic Landmass Silhouette */}
          <path
            d={INDIA_COAST_PATH}
            fill="rgba(16, 18, 22, 0.45)"
            stroke="var(--line-subtle)"
            strokeWidth="1.2"
            strokeDasharray="4 4"
            opacity="0.8"
          />

          {/* 2. National Trunk Railway Lines */}
          <g className="trunk-tracks-group">
            {TRUNK_TRACKS.map(([fromCode, toCode], idx) => {
              const p1 = stationPositions.get(fromCode);
              const p2 = stationPositions.get(toCode);
              if (!p1 || !p2) return null;

              return (
                <g key={`track-${fromCode}-${toCode}-${idx}`}>
                  {/* Underlay glow track */}
                  <line
                    x1={p1.x}
                    y1={p1.y}
                    x2={p2.x}
                    y2={p2.y}
                    stroke="var(--track-rail)"
                    strokeWidth="2.5"
                    strokeLinecap="round"
                  />
                  {/* Fine center ballast line */}
                  <line
                    x1={p1.x}
                    y1={p1.y}
                    x2={p2.x}
                    y2={p2.y}
                    stroke="#1C2028"
                    strokeWidth="1"
                    strokeDasharray="3 3"
                  />
                </g>
              );
            })}
          </g>

          {/* 3. Station Nodes (112+ Stations across India) */}
          <g className="stations-layer">
            {Array.from(stationPositions.values()).map(({ x, y, meta }) => {
              const isSelected = selectedStationCode?.toUpperCase() === meta.code.toUpperCase();
              const occupancy = stationOccupancyMap.get(meta.code.toUpperCase()) || 0;
              const isMajor = (meta.platforms || 1) >= 8 || meta.is_junction === 1;
              const isNationalHub = NATIONAL_HUBS.has(meta.code.toUpperCase());
              const showLabel = isSelected || zoom >= 2.4 || (zoom >= 1.4 && isMajor) || isNationalHub;

              return (
                <g
                  key={`stn-${meta.code}`}
                  className="station-node-group"
                  style={{ cursor: 'pointer' }}
                  onClick={(e) => {
                    e.stopPropagation();
                    onSelectStation(meta.code);
                  }}
                  onMouseEnter={(e) => {
                    setHoveredEntity({
                      type: 'station',
                      x: e.clientX,
                      y: e.clientY,
                      title: `${meta.name} (${meta.code})`,
                      subtitle: `${meta.platforms || 2} Platforms &bull; ${meta.is_junction ? 'Junction Hub' : 'Terminal/Station'}`,
                      details: [
                        { label: 'Berthed Trains', val: `${occupancy} units`, color: occupancy > 0 ? 'var(--kiosk-gold)' : undefined },
                        { label: 'Coordinates', val: `${meta.lat.toFixed(2)}°N, ${meta.lon.toFixed(2)}°E` },
                        { label: 'Yard Status', val: occupancy > (meta.platforms || 2) * 0.7 ? 'CONGESTED' : 'CLEAR', color: occupancy > (meta.platforms || 2) * 0.7 ? 'var(--signal-amber)' : 'var(--signal-green)' },
                      ],
                    });
                  }}
                  onMouseLeave={() => setHoveredEntity(null)}
                >
                  {/* Selection Halo */}
                  {isSelected && (
                    <circle
                      cx={x}
                      cy={y}
                      r={14 / Math.sqrt(zoom)}
                      fill="none"
                      stroke="var(--kiosk-gold)"
                      strokeWidth={2 / Math.sqrt(zoom)}
                      strokeDasharray="3 3"
                    />
                  )}

                  {/* Berthed trains indicator halo */}
                  {occupancy > 0 && (
                    <circle
                      cx={x}
                      cy={y}
                      r={isMajor ? 8 / Math.sqrt(zoom) : 6 / Math.sqrt(zoom)}
                      fill="none"
                      stroke="var(--ochre)"
                      strokeWidth={1.5 / Math.sqrt(zoom)}
                      opacity="0.7"
                    />
                  )}

                  {/* Center Station Dot */}
                  <circle
                    cx={x}
                    cy={y}
                    r={isSelected ? 6 / Math.sqrt(zoom) : isMajor ? 4.5 / Math.sqrt(zoom) : 3 / Math.sqrt(zoom)}
                    fill={isSelected ? 'var(--kiosk-gold)' : isMajor ? 'var(--text-primary)' : 'var(--line-strong)'}
                    stroke="var(--bg-night-0)"
                    strokeWidth={1 / Math.sqrt(zoom)}
                  />

                  {/* Station Code Label (Prominent on national hubs, major junctions, or zoom) */}
                  {showLabel && (
                    <text
                      x={x}
                      y={y - (8 / Math.sqrt(zoom))}
                      textAnchor="middle"
                      fill={isSelected ? 'var(--kiosk-gold)' : isNationalHub ? 'var(--kiosk-gold)' : 'var(--text-secondary)'}
                      fontFamily="var(--font-mono)"
                      fontSize={Math.max(7.5, (isNationalHub ? 10 : 8.5) / Math.sqrt(zoom))}
                      fontWeight={isSelected || isNationalHub ? '800' : '600'}
                      letterSpacing="0.5"
                    >
                      {meta.code}
                    </text>
                  )}
                </g>
              );
            })}
          </g>

          {/* 4. Real-Time Moving Trains (1,000+ Trains) */}
          <g className="trains-layer">
            {positions.map((p) => {
              if (!p.lat || !p.lng) return null;
              const [tx, ty] = projectCoords(p.lat, p.lng);
              const color = getTrainColor(p);
              const isSelected = selectedTrainNo === p.train_no;
              const detail = trainDetailMap.get(p.train_no);
              const radius = isSelected ? 7 / Math.sqrt(zoom) : 4 / Math.sqrt(zoom);

              return (
                <g
                  key={`trn-${p.train_no}`}
                  className="train-marker-group"
                  style={{ cursor: 'pointer' }}
                  onClick={(e) => {
                    e.stopPropagation();
                    onSelectTrain(p.train_no);
                  }}
                  onMouseEnter={(e) => {
                    setHoveredEntity({
                      type: 'train',
                      x: e.clientX,
                      y: e.clientY,
                      title: `#${p.train_no} ${detail?.name || 'Corridor Service'}`,
                      subtitle: detail?.class ? detail.class.toUpperCase() : 'PASSENGER EXPRESS',
                      details: [
                        { label: 'Speed', val: `${Math.round(p.speed_kmh)} km/h` },
                        {
                          label: 'Delay',
                          val: p.delay_minutes > 0 ? `+${p.delay_minutes}m` : '0m (On-Time)',
                          color,
                        },
                        { label: 'Signal Aspect', val: p.inferred_signal_aspect || 'GREEN' },
                        { label: 'Location', val: p.current_station_code ? `@ ${p.current_station_code}` : p.next_station_code ? `→ ${p.next_station_code}` : 'Section Line' },
                      ],
                    });
                  }}
                  onMouseLeave={() => setHoveredEntity(null)}
                >
                  {/* Selected Train Radiant Halo */}
                  {isSelected && (
                    <circle
                      cx={tx}
                      cy={ty}
                      r={18 / Math.sqrt(zoom)}
                      fill="none"
                      stroke="var(--kiosk-gold)"
                      strokeWidth={2 / Math.sqrt(zoom)}
                      strokeDasharray="4 2"
                      filter="url(#map-glow)"
                    />
                  )}

                  {/* Active Motion Pulse Ring */}
                  {p.speed_kmh > 15 && (
                    <circle
                      cx={tx}
                      cy={ty}
                      r={radius + 3 / Math.sqrt(zoom)}
                      fill="none"
                      stroke={color}
                      strokeWidth={1 / Math.sqrt(zoom)}
                      opacity="0.5"
                    />
                  )}

                  {/* Train Dot Marker */}
                  <circle
                    cx={tx}
                    cy={ty}
                    r={radius}
                    fill={color}
                    stroke="var(--bg-night-0)"
                    strokeWidth={1.2 / Math.sqrt(zoom)}
                  />

                  {/* Train Number Tag: Focused on selected train or high zoom */}
                  {isSelected && (
                    <g pointerEvents="none">
                      <rect
                        x={tx - 20 / Math.sqrt(zoom)}
                        y={ty + radius + 3 / Math.sqrt(zoom)}
                        width={40 / Math.sqrt(zoom)}
                        height={12 / Math.sqrt(zoom)}
                        rx={2 / Math.sqrt(zoom)}
                        fill="rgba(10, 11, 13, 0.95)"
                        stroke="var(--kiosk-gold)"
                        strokeWidth={0.8 / Math.sqrt(zoom)}
                      />
                      <text
                        x={tx}
                        y={ty + radius + 11.5 / Math.sqrt(zoom)}
                        textAnchor="middle"
                        fill="var(--kiosk-gold)"
                        fontFamily="var(--font-mono)"
                        fontSize={8 / Math.sqrt(zoom)}
                        fontWeight="800"
                      >
                        #{p.train_no}
                      </text>
                    </g>
                  )}
                </g>
              );
            })}
          </g>
        </g>
      </svg>
    </div>
  );
};
export default IndiaMap;
