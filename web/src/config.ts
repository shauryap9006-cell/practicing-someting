/**
 * RailTwin-X Frontend Configuration & Operational Constants.
 * 
 * Central source of truth for frontend polling intervals, SSE pulse periods,
 * confidence decay thresholds, visual color tokens, and corridor map coordinates.
 * Matches backend defaults from config.py.
 */

export interface StationCoordinate {
  code: string;
  name: string;
  lat: number;
  lng: number;
  distance_km: number;
  is_junction: boolean;
  platforms: number;
}

export interface AttributionColorMap {
  RAKE_INHERIT: string;
  TSR_ACTIVE: string;
  WEATHER_FOG: string;
  WEATHER_RAIN: string;
  PLATFORM_WAIT: string;
  CONGESTION: string;
  UNEXPLAINED: string;
  [key: string]: string;
}

export const BACKEND_DEFAULTS = {
  LIVE_TRACKER_INTERVAL_SECONDS: 1,
  LIVE_STATION_POLL_SECONDS: 30,
  LIVE_POLL_TPM_BUDGET: 100,
  ATTRIBUTION_DELTA_MIN: 5.0,
  ATTRIBUTION_UNEXPLAINED_TOLERANCE_MIN: 0.5,
  WEATHER_CACHE_MINUTES: 15,
  POSITION_CACHE_TTL_SECONDS: 60,
  LIVE_SSE_PULSE_SECONDS: 5,
  CONTEXT_CACHE_TTL_SECONDS: 10,
  CONFIDENCE_TAU_SECONDS: 120.0,
  DEAD_RECKON_MIN_CONFIDENCE: 0.3,
} as const;

export const COLOR_TOKENS = {
  // Status / Severity Tokens
  DANGER: "#EF4444",      // red-500
  WARNING: "#F59E0B",     // amber-500
  SUCCESS: "#10B981",     // emerald-500
  NEUTRAL: "#64748B",     // slate-500
  INFO: "#3B82F6",        // blue-500

  // Pulse & Highlight Glows
  PULSE_HIGHLIGHT: "#38BDF8", // sky-400
  PULSE_PURPLE: "#A855F7",    // purple-500
  PULSE_GREEN: "#22C55E",     // green-500
  PULSE_RED: "#EF4444",       // red-500
  PULSE_AMBER: "#F59E0B",     // amber-500

  // Background / Surface Accents
  SURFACE_DARK: "#0F172A",    // slate-900
  SURFACE_CARD: "#1E293B",    // slate-800
  BORDER_SUBTLE: "#334155",   // slate-700
} as const;

export const ATTRIBUTION_COLORS: AttributionColorMap = {
  RAKE_INHERIT: "#A855F7",    // Purple
  TSR_ACTIVE: "#EF4444",      // Red
  WEATHER_FOG: "#94A3B8",     // Foggy Gray
  WEATHER_RAIN: "#38BDF8",    // Rain Blue
  PLATFORM_WAIT: "#F59E0B",   // Amber
  CONGESTION: "#F97316",      // Orange
  UNEXPLAINED: "#64748B",     // Slate Gray
};

export const CORRIDOR_STATIONS: StationCoordinate[] = [
  { code: "NDLS", name: "New Delhi", lat: 28.6143, lng: 77.2188, distance_km: 0.0, is_junction: true, platforms: 16 },
  { code: "GZB", name: "Ghaziabad Jn", lat: 28.6675, lng: 77.4326, distance_km: 25.6, is_junction: true, platforms: 6 },
  { code: "ALJN", name: "Aligarh Jn", lat: 27.8974, lng: 78.0880, distance_km: 131.0, is_junction: true, platforms: 7 },
  { code: "TDL", name: "Tundla Jn", lat: 27.2046, lng: 78.2410, distance_km: 205.5, is_junction: true, platforms: 5 },
  { code: "ETW", name: "Etawah Jn", lat: 26.7606, lng: 79.0300, distance_km: 297.8, is_junction: true, platforms: 5 },
  { code: "CNB", name: "Kanpur Central", lat: 26.4547, lng: 80.3507, distance_km: 436.5, is_junction: true, platforms: 10 },
  { code: "PRYJ", name: "Prayagraj Jn", lat: 25.4497, lng: 81.8340, distance_km: 633.2, is_junction: true, platforms: 10 },
  { code: "DDU", name: "Pt. Deen Dayal Upadhyaya Jn", lat: 25.2783, lng: 83.1189, distance_km: 785.0, is_junction: true, platforms: 8 },
];

export const CORRIDOR_GEO = {
  MIN_LAT: 25.0,
  MAX_LAT: 29.0,
  MIN_LON: 77.0,
  MAX_LON: 83.5,
  TOTAL_KM: 785.0,
  ORIGIN_CODE: "NDLS",
  TERMINUS_CODE: "DDU",
  STATIONS: CORRIDOR_STATIONS,
} as const;

export const LIVE_CONFIG = {
  // Polling & SSE intervals
  SSE_PULSE_INTERVAL_MS: 5000,
  GLIDE_DURATION_MS: 1000,
  STALE_AGE_THRESHOLD_SECONDS: 60,
  STATION_BOARD_POLL_INTERVAL_MS: 30000,

  // Confidence thresholds
  MIN_CONFIDENCE_THRESHOLD: 0.30,
  CONFIDENCE_TAU_SECONDS: 120.0,
  CONFIDENCE_TIERS: {
    HIGH: 0.70,
    MEDIUM: 0.40,
    LOW: 0.30,
  },

  // Delay Attribution
  ATTRIBUTION_DELTA_MIN: 5.0,
  ATTRIBUTION_UNEXPLAINED_TOLERANCE_MIN: 0.5,

  // Visual Tokens & Maps
  COLORS: COLOR_TOKENS,
  ATTRIBUTION_COLORS,
  CORRIDOR_GEO,
  BACKEND_DEFAULTS,
} as const;

export default LIVE_CONFIG;
