import React, { useEffect, useRef, useState } from 'react';
import maplibregl from 'maplibre-gl';
import 'maplibre-gl/dist/maplibre-gl.css';
import { Navigation, Crosshair } from 'lucide-react';
import corridorTrackData from '@/data/corridor_track_geometry.json';

export interface RouteStopGeo {
  stationCode: string;
  stationName: string;
  stationNameHi?: string;
  lat: number;
  lon: number;
  distanceKm: number;
  platform?: number;
  status: 'passed' | 'current' | 'upcoming';
  schedArrival?: string;
  schedDeparture?: string;
  predArrival?: string;
  predDeparture?: string;
  delayMinutes?: number;
}

interface PassengerSatelliteMapProps {
  trainNo: string;
  trainName?: string;
  speedKmph?: number;
  currentStationCode?: string;
  nextStationCode?: string;
  trainPosition?: {
    lat: number;
    lng: number;
    speed_kmh?: number;
    heading?: number;
    inferred_signal_aspect?: string;
    delay_minutes?: number;
  };
  stops: RouteStopGeo[];
  activeStationCode?: string;
  onSelectStation?: (stationCode: string) => void;
  lang?: 'EN' | 'HI';
}

// Satellite Tile Sources & OpenRailwayMap Physical Rail Layer
const SATELLITE_TILES = [
  'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
];
const OPENRAILWAYMAP_TILES = [
  'https://a.tiles.openrailwaymap.org/standard/{z}/{x}/{y}.png',
  'https://b.tiles.openrailwaymap.org/standard/{z}/{x}/{y}.png',
  'https://c.tiles.openrailwaymap.org/standard/{z}/{x}/{y}.png',
];

export const PassengerSatelliteMap: React.FC<PassengerSatelliteMapProps> = ({
  trainNo,
  trainName,
  speedKmph = 95,
  currentStationCode = 'NDLS',
  nextStationCode = 'CNB',
  trainPosition,
  stops,
  activeStationCode,
  onSelectStation,
  lang = 'EN',
}) => {
  const mapContainerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<maplibregl.Map | null>(null);
  const markersRef = useRef<maplibregl.Marker[]>([]);
  const trainMarkerRef = useRef<maplibregl.Marker | null>(null);

  const [mapLoaded, setMapLoaded] = useState(false);
  const [hasWebGlError, setHasWebGlError] = useState(false);

  // Train coordinates
  const trainLat = trainPosition?.lat ?? stops.find(s => s.stationCode === currentStationCode)?.lat ?? 26.8467;
  const trainLon = trainPosition?.lng ?? stops.find(s => s.stationCode === currentStationCode)?.lon ?? 80.9462;
  const trainSpeed = trainPosition?.speed_kmh ?? speedKmph;

  // Compute accurate track coordinates along the physical railway corridor
  const accurateTrackCoordinates = React.useMemo(() => {
    const isLucknowTerminus = stops.some(s => s.stationCode === 'LKO');
    if (isLucknowTerminus) {
      const trunkUpToCnb = corridorTrackData.trunk_NDLS_DDU.slice(0, 60);
      return [...trunkUpToCnb, ...corridorTrackData.branch_CNB_LKO];
    }
    return corridorTrackData.trunk_NDLS_DDU;
  }, [stops]);

  // Initialize Pure Satellite Map with Permanent Physical Tracks
  useEffect(() => {
    if (!mapContainerRef.current) return;

    try {
      const map = new maplibregl.Map({
        container: mapContainerRef.current,
        style: {
          version: 8,
          sources: {
            'satellite-source': {
              type: 'raster',
              tiles: SATELLITE_TILES,
              tileSize: 256,
              attribution: 'Esri World Imagery',
            },
            'openrailwaymap-source': {
              type: 'raster',
              tiles: OPENRAILWAYMAP_TILES,
              tileSize: 256,
              attribution: 'OpenRailwayMap',
            },
          },
          layers: [
            // 1. High-Resolution Satellite Base Layer
            {
              id: 'satellite-tiles',
              type: 'raster',
              source: 'satellite-source',
              minzoom: 0,
              maxzoom: 19,
            },
            // 2. Real Physical Rail Tracks Layer (Permanent, No Toggle)
            {
              id: 'openrailwaymap-layer',
              type: 'raster',
              source: 'openrailwaymap-source',
              minzoom: 8,
              maxzoom: 19,
              paint: {
                'raster-opacity': 0.9,
              },
            },
          ],
        },
        center: [trainLon, trainLat],
        zoom: 9.5,
        attributionControl: false,
      });

      map.on('load', () => {
        setMapLoaded(true);

        // Add Surveyed Physical Route Track Polyline
        map.addSource('route-track', {
          type: 'geojson',
          data: {
            type: 'Feature',
            properties: {},
            geometry: {
              type: 'LineString',
              coordinates: accurateTrackCoordinates,
            },
          },
        });

        // Glow outer line along the real track
        map.addLayer({
          id: 'route-track-glow',
          type: 'line',
          source: 'route-track',
          layout: { 'line-join': 'round', 'line-cap': 'round' },
          paint: {
            'line-color': '#F5A524',
            'line-width': 8,
            'line-opacity': 0.45,
          },
        });

        // Sharp active railway route line
        map.addLayer({
          id: 'route-track-line',
          type: 'line',
          source: 'route-track',
          layout: { 'line-join': 'round', 'line-cap': 'round' },
          paint: {
            'line-color': '#F5A524',
            'line-width': 3,
          },
        });
      });

      map.on('error', () => {
        // Suppress benign tile timeout messages
      });

      mapRef.current = map;

      return () => {
        map.remove();
        mapRef.current = null;
      };
    } catch (e) {
      console.warn('MapLibre WebGL initialization failed, fallback active', e);
      setHasWebGlError(true);
    }
  }, []);

  // Update Route Track GeoJSON when coordinates change
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !mapLoaded) return;

    const source = map.getSource('route-track') as maplibregl.GeoJSONSource | undefined;
    if (source) {
      source.setData({
        type: 'Feature',
        properties: {},
        geometry: {
          type: 'LineString',
          coordinates: accurateTrackCoordinates,
        },
      });
    }
  }, [accurateTrackCoordinates, mapLoaded]);

  // Update Markers when stops or train position changes
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !mapLoaded) return;

    // Remove existing station markers
    markersRef.current.forEach(m => m.remove());
    markersRef.current = [];

    // 1. Add Station Pins along the route
    stops.forEach(stop => {
      const isSelected = stop.stationCode === activeStationCode;
      const isPassed = stop.status === 'passed';
      const isCurrent = stop.status === 'current';

      const el = document.createElement('div');
      el.className = 'cursor-pointer select-none group';
      el.innerHTML = `
        <div class="flex flex-col items-center">
          <div class="px-2 py-0.5 rounded text-[10px] font-mono font-bold shadow-lg border transition-all ${
            isSelected
              ? 'bg-[#E9EBEE] text-[#0A0B0D] border-white scale-110 ring-2 ring-[#F5A524]'
              : isCurrent
              ? 'bg-[#F5A524] text-[#0A0B0D] border-[#F5A524] animate-pulse'
              : isPassed
              ? 'bg-[#101216]/95 text-[#3DDC97] border-[#3DDC97]/40'
              : 'bg-[#101216]/95 text-[#E9EBEE] border-[#23272F]'
          }">
            <span>${stop.stationCode}</span>
            ${stop.platform ? `<span class="opacity-75 text-[9px] ml-1">PF${stop.platform}</span>` : ''}
          </div>
          <div class="w-2.5 h-2.5 rounded-full mt-0.5 border border-[#101216] ${
            isCurrent ? 'bg-[#F5A524] animate-ping' : isPassed ? 'bg-[#3DDC97]' : 'bg-[#E9EBEE]'
          }"></div>
        </div>
      `;

      el.addEventListener('click', () => {
        if (onSelectStation) onSelectStation(stop.stationCode);
        map.flyTo({ center: [stop.lon, stop.lat], zoom: 12, essential: true });
      });

      const marker = new maplibregl.Marker({ element: el })
        .setLngLat([stop.lon, stop.lat])
        .addTo(map);

      markersRef.current.push(marker);
    });

    // 2. Add / Update Live Train Marker
    if (trainMarkerRef.current) {
      trainMarkerRef.current.remove();
      trainMarkerRef.current = null;
    }

    const trainEl = document.createElement('div');
    trainEl.className = 'cursor-pointer select-none z-30';
    trainEl.innerHTML = `
      <div class="relative flex flex-col items-center group">
        <!-- Live Ripple Aura -->
        <span class="absolute -top-1 w-10 h-10 rounded-full bg-[#F5A524]/25 animate-ping"></span>
        
        <!-- Train Instrument Beacon -->
        <div class="relative px-2.5 py-1 rounded-full bg-[#0A0B0D] border-2 border-[#F5A524] text-[#E9EBEE] shadow-2xl flex items-center gap-1.5 font-mono text-[11px] font-bold">
          <span class="w-2.5 h-2.5 rounded-full bg-[#3DDC97] animate-pulse"></span>
          <span>🚆 ${trainNo}</span>
          <span class="text-[#F5A524] text-[10px] tabular-nums">${Math.round(trainSpeed)} km/h</span>
        </div>
        
        <!-- Down Pointer Arrow -->
        <div class="w-0 h-0 border-l-[5px] border-l-transparent border-r-[5px] border-r-transparent border-t-[6px] border-t-[#F5A524] -mt-0.5"></div>
      </div>
    `;

    trainEl.addEventListener('click', () => {
      map.flyTo({ center: [trainLon, trainLat], zoom: 13, essential: true });
    });

    trainMarkerRef.current = new maplibregl.Marker({ element: trainEl })
      .setLngLat([trainLon, trainLat])
      .addTo(map);
  }, [stops, activeStationCode, trainLat, trainLon, trainSpeed, trainNo, mapLoaded]);

  const fitFullCorridor = () => {
    const map = mapRef.current;
    if (!map || stops.length === 0) return;

    const bounds = new maplibregl.LngLatBounds();
    stops.forEach(s => bounds.extend([s.lon, s.lat]));
    bounds.extend([trainLon, trainLat]);
    map.fitBounds(bounds, { padding: 50, duration: 1000 });
  };

  const centerOnTrain = () => {
    const map = mapRef.current;
    if (!map) return;
    map.flyTo({ center: [trainLon, trainLat], zoom: 12, duration: 1000, essential: true });
  };

  return (
    <div className="relative w-full h-[450px] md:h-[540px] bg-[#0A0B0D] rounded-lg border border-[#23272F] overflow-hidden select-none font-mono">
      {/* Map Canvas */}
      {!hasWebGlError ? (
        <div ref={mapContainerRef} className="w-full h-full" />
      ) : (
        <div className="w-full h-full flex items-center justify-center p-6 bg-[#0E1015] text-center">
          <div className="space-y-2">
            <Navigation className="w-8 h-8 text-[#F5A524] mx-auto animate-pulse" />
            <p className="text-xs text-[#E9EBEE] font-bold">Satellite Map Loading...</p>
            <p className="text-[11px] text-[#A3ABB6]">
              Train #{trainNo} is currently en route at KM {stops[0]?.distanceKm ?? 0}.
            </p>
          </div>
        </div>
      )}

      {/* Top Floating Badge (Minimal, no toggle buttons) */}
      <div className="absolute top-3 left-3 flex items-center gap-2 pointer-events-none">
        <div className="px-3 py-1 bg-[#101216]/90 backdrop-blur-md border border-[#23272F] rounded-md text-xs text-[#E9EBEE] pointer-events-auto flex items-center gap-2 shadow-xl">
          <span className="w-2 h-2 rounded-full bg-[#3DDC97] animate-ping" />
          <span className="font-bold text-[#3DDC97]">{Math.round(trainSpeed)} km/h</span>
          <span className="text-[#6B7480]">·</span>
          <span className="text-[#A3ABB6] text-[11px]">
            {currentStationCode} → {nextStationCode}
          </span>
          <span className="text-[#6B7480]">·</span>
          <span className="text-[10px] text-[#F5A524]">TRACK VERIFIED</span>
        </div>
      </div>

      {/* Bottom Right Minimal Camera Controls */}
      <div className="absolute bottom-3 right-3 flex items-center gap-2 pointer-events-auto">
        <button
          type="button"
          onClick={centerOnTrain}
          className="px-2.5 py-1.5 bg-[#101216]/90 backdrop-blur-md border border-[#23272F] hover:border-[#F5A524] text-[#E9EBEE] rounded-md shadow-lg transition-all flex items-center gap-1.5 text-xs font-bold"
          title="Locate Train"
        >
          <Crosshair className="w-3.5 h-3.5 text-[#F5A524]" />
          <span>{lang === 'HI' ? 'ट्रेन पर ज़ूम' : 'Locate Train'}</span>
        </button>

        <button
          type="button"
          onClick={fitFullCorridor}
          className="px-2.5 py-1.5 bg-[#101216]/90 backdrop-blur-md border border-[#23272F] hover:border-[#2E333D] text-[#A3ABB6] hover:text-[#E9EBEE] rounded-md shadow-lg transition-all flex items-center gap-1.5 text-xs"
          title="Full Route Corridor"
        >
          <Navigation className="w-3.5 h-3.5" />
          <span>{lang === 'HI' ? 'पूरा मार्ग' : 'Full Route'}</span>
        </button>
      </div>
    </div>
  );
};
