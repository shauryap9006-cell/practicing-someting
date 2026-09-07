export type ConnectionStatus = 'live' | 'stale' | 'offline';

export interface ClockData {
  sim_now: string;
  real_now: string;
  accel: number;
  mode: string;
}

export interface StationMeta {
  code: string;
  name: string;
  name_hi?: string;
  is_junction?: number;
  platforms: number;
  lat: number;
  lon: number;
  km?: number;
}

export interface LivePosition {
  train_no: string;
  run_date: string;
  lat: number;
  lng: number;
  current_station_code: string | null;
  next_station_code: string | null;
  section_id: string | null;
  speed_kmh: number;
  delay_minutes: number;
  confidence: number;
  progress_pct: number;
  is_dead_reckoned: number | boolean;
  source: string;
  last_event_time: string;
  last_gps_fix: string;
  updated_at: string;
  signal_hold_active: boolean;
  signal_hold_duration_min: number;
  inferred_signal_aspect: 'GREEN' | 'YELLOW' | 'RED';
  km?: number;
}

export interface NetworkStateTrain {
  train_no: string;
  train_name: string;
  train_class: string;
  priority: number;
  last_passed_station: string;
  next_station: string;
  current_delay_min: number;
  status_color: string;
  hops_remaining: number;
  destination: string;
  predicted_dest_delay_min: number;
}

export interface NetworkState {
  updated_at: string;
  clock_mode: string;
  active_trains_count: number;
  delayed_trains_count: number;
  active_conflicts_count: number;
  trains: NetworkStateTrain[];
  active_tsrs: Array<{
    from_code: string;
    to_code: string;
    speed_limit_kmph: number;
    cause: string;
  }>;
}

export interface CongestionHorizonCell {
  horizon: string;
  active_trains: number;
  capacity: number;
  occupancy_pct: number;
  congestion_level: string;
  total_delay_min: number;
}

export interface CongestionRadarSection {
  section_id: string;
  section_name: string;
  from_km: number;
  to_km: number;
  length_km: number;
  chokepoint_station: string;
  peak_occupancy_pct: number;
  horizons: Record<string, CongestionHorizonCell>;
}

export interface CongestionRadarData {
  status: string;
  corridor: string;
  as_of: string;
  horizons: string[];
  sections_count: number;
  active_monitored_trains: number;
  radar: CongestionRadarSection[];
  highest_chokepoints?: Array<{
    section: string;
    chokepoint: string;
    peak_occupancy: number;
    recommended_action: string;
  }>;
}

export interface StationBoardEntry {
  train_no: string;
  train_name: string;
  train_type: string;
  direction: string;
  sched_arr: string | null;
  sched_dep: string | null;
  exp_arr: string | null;
  exp_dep: string | null;
  delay_min: number;
  platform: number | string;
  status: string;
  status_color: string;
  is_cancelled: boolean;
  has_setin: boolean;
  has_setout: boolean;
  cqr_interval?: [number, number];
}

export interface StationBoardPayload {
  station_code: string;
  date: string;
  total_trains: number;
  refreshed_at: string;
  entries: StationBoardEntry[];
}

export interface LiveOperationalEvent {
  ts: string;
  type: 'departure' | 'arrival' | 'delay_shift' | 'alert' | 'tsr' | 'shock';
  train_no: string | null;
  train_name: string | null;
  station_code: string | null;
  delay_min: number | null;
  detail: string;
}

export interface CorridorStation extends StationMeta {
  km: number;
}

export interface PlatformState {
  station_code: string;
  platform: number;
  state: 'FREE' | 'OCCUPIED' | 'BLOCKED_MAINT' | 'OUT_OF_SERVICE';
  occupied_by_train: string | null;
  since?: string;
  reason?: string | null;
  updated_by?: string;
}

export interface RailwayCorridor {
  id: string;
  name: string;
  region: string;
  stationCodes: string[];
}

