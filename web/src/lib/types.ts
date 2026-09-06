export interface Band {
  p10: number;
  p50: number;
  p90: number;
}

export interface CauseItem {
  code: string;
  label: string;
  minutes: number;
  sharePct: number;
  station?: string;
  evidence?: string;
  category?: string;
}

export interface WhyLateData {
  narrative: string;
  causes: CauseItem[];
  totalMin: number;
  additiveOk: boolean;
  integrityStatus?: string;
  eventsCount?: number;
}

export interface JourneyStop {
  code: string;
  name: string;
  nameHi?: string;
  km: number;
  seq: number;
  schedArr?: string;
  schedDep?: string;
  actualArr?: string;
  actualDep?: string;
  expectedArr?: string;
  expectedDep?: string;
  band?: Band;
  passed: boolean;
  isNextStop?: boolean;
  isSelectedStop?: boolean;
  platform?: string | number | null;
  delayMin?: number;
  statusLamp?: 'clear' | 'caution' | 'restrict';
}

export interface PassengerWaypoint {
  code: string;
  name: string;
  name_hi?: string;
  km: number;
}

export interface PassengerSnapshot {
  train: {
    train_no: string;
    name: string;
    name_hi?: string;
    type: string;
    origin: { code: string; name: string; name_hi?: string };
    destination: { code: string; name: string; name_hi?: string };
    runs_today: boolean;
    run_status: string;
    next_run_note?: string;
    next_run_note_hi?: string;
  };
  pnr_info?: Record<string, unknown> | null;
  next_stop: {
    station_code: string;
    station_name: string;
    station_name_hi?: string;
    distance_km: number;
    km_away: number;
    eta_minutes: number;
    scheduled_time: string;
    expected_time: string;
    platform: string | number | null;
    status: string;
  };
  selected_stop: {
    station_code: string;
    station_name: string;
    station_name_hi?: string;
    is_boarding_stop?: boolean;
    scheduled_arr: string;
    scheduled_dep: string;
    expected_arr: string;
    expected_dep: string;
    time_window?: { min: string; max: string };
    platform: string | number | null;
    status: string;
    actual_arr?: string | null;
    actual_dep?: string | null;
  };
  single_delay: {
    delay_min: number;
    status_lamp: 'green' | 'amber' | 'red';
    label: string;
    label_hi?: string;
    invariant_checked?: boolean;
  };
  position_strip: {
    total_km: number;
    current_km: number;
    progress_pct: number;
    next_stop_summary: string;
    next_stop_summary_hi?: string;
    prev_stop_name?: string;
    prev_stop_name_hi?: string;
    stations: Array<{
      code: string;
      name: string;
      name_hi?: string;
      seq: number;
      distance_km: number;
      passed: boolean;
      is_selected_stop: boolean;
      is_current: boolean;
      is_next_stop: boolean;
      sched_time: string;
      pred_time: string;
    }>;
  };
  live_status: {
    summary: string;
    summary_hi?: string;
    is_halted: boolean;
    halted_station: string | null;
    dwell_time_min: number | null;
    between_stations: string[];
    between_stations_hi?: string[];
    km_covered: number;
    speed_kmh: number;
    speed_from_deltas?: number;
  };
  autopsy: {
    headline: string;
    headline_hi?: string;
    integrity_status: string;
    total_delay_min: number;
    causes: Array<{
      category: string;
      minutes: number;
      lamp: string;
      plain_text: string;
      plain_text_hi?: string;
      evidence_ref?: string;
    }>;
  };
  map_card: {
    polyline: number[][];
    train_marker: {
      lat: number;
      lon: number;
      heading: number;
      km: number;
      speed_kmh: number;
      label: string;
    };
    tsr_zones: Array<{
      order_no: string;
      speed_limit_kmph: number;
      start_km: number;
      end_km: number;
      lat1: number;
      lon1: number;
      lat2: number;
      lon2: number;
      label: string;
      label_hi?: string;
    }>;
    track_verified: boolean;
    displacement_km: number;
  };
  all_stops: Array<{
    station_code: string;
    station_name: string;
    station_name_hi?: string;
    seq: number;
    distance_km: number;
    scheduled_arr: string | null;
    scheduled_dep: string | null;
    predicted_arr: string | null;
    predicted_dep: string | null;
    actual_arr: string | null;
    actual_dep: string | null;
    platform: string | null;
    delay_min: number;
    status: string;
    status_lamp: 'green' | 'amber' | 'red';
    lat?: number;
    lon?: number;
    is_next_stop: boolean;
  }>;
  waypoints: PassengerWaypoint[];
  provenance: {
    as_of: string;
    auto_refresh_sec: number;
    clock_mode: string;
    simulated_clock: string;
  };
}

export interface TrainSnapshot {
  trainNo: string;
  trainName: string;
  origin: { code: string; name: string };
  destination: { code: string; name: string };
  currentDelayMin: number;
  speedKmh: number;
  positionKm: number;
  totalKm: number;
  nextStop: {
    code: string;
    name: string;
    schedArr: string;
    band: Band;
    distanceKm: number;
    kmAway: number;
    etaMin: number;
  };
  stops: JourneyStop[];
  aspect: 'CLEAR' | 'CAUTION' | 'RESTRICT';
  platform?: string | number | null;
  updatedAt: string;
  raw: PassengerSnapshot;
}
export interface LivePosition {
  train_no: string;
  run_date: string;
  lat: number;
  lng: number;
  current_station_code: string;
  next_station_code: string;
  section_id: string;
  speed_kmh: number;
  delay_minutes: number;
  confidence: number;
  progress_pct: number;
  is_dead_reckoned: number;
  source: string;
  last_event_time: string;
  last_gps_fix: string;
  updated_at: string;
  signal_hold_active: boolean;
  signal_hold_duration_min: number;
  inferred_signal_aspect: 'GREEN' | 'YELLOW' | 'RED';
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
  highest_chokepoints: Array<{
    section: string;
    chokepoint: string;
    peak_occupancy: number;
    recommended_action: string;
  }>;
}

export interface ComparatorStation {
  seq: number;
  station_code: string;
  station_name: string;
  distance_km: number;
  delta_km_from_now: number;
  sched_arr: string | null;
  sched_dep: string | null;
  is_passed: boolean;
  is_current: boolean;
  horizon_tag: string;
  actual_delay_min: number;
  b1_frozen_delay_min: number;
  b2_official_delay_min: number;
  p10_delay_min: number;
  p50_delay_min: number;
  p90_delay_min: number;
  cone_spread_min: number;
}

export interface ComparatorData {
  status: string;
  train_no: string;
  train_name: string;
  train_class: string;
  origin: string;
  destination: string;
  run_date: string;
  active_station: {
    seq: number;
    code: string;
    name: string;
    current_delay_min: number;
  };
  simulation_shock_active: boolean;
  active_shocks: Array<{
    id: number;
    event_type: string;
    station: string;
    severity_min: number;
    description: string;
    injected_at: string;
  }>;
  stations: ComparatorStation[];
  cumulative_errors: {
    samples_evaluated: number;
    b1_frozen_mae: number;
    b2_official_mae: number;
    railtwin_p50_mae: number;
    railtwin_vs_official_gain_pct: number;
  };
  why_late?: WhyLateData;
  ledger_receipt: {
    receipt_hash: string;
    chain_verified: boolean;
    status: string;
  };
  proof_points?: Record<string, string>;
  as_of: string;
}
export interface ShootoutItem {
  horizon: string;
  horizon_label: string;
  mae: number;
  baseline_b1_mae: number;
  baseline_b2_mae: number;
  baseline_b3_mae: number;
  improvement_vs_official_pct: number;
  coverage_80_pct: number;
  winkler_score: number;
  verdict: string;
  status_badge: string;
  narrative: string;
}

export interface HorizonCard {
  horizon: string;
  mae: number;
  coverage_pct: number;
  samples: number;
  crps?: number;
}

export interface ModelPerformanceData {
  status: string;
  schema_version?: string;
  canonical_mae: number;
  overall_mae: number;
  overall_coverage_80: number;
  overall_winkler_score: number;
  overall_crps: number;
  total_test_samples: number;
  horizon_cards: HorizonCard[];
  proof_table: Array<Record<string, string | number>>;
  metrics_by_horizon?: Record<string, Record<string, number>>;
  rolling_origin_cv?: unknown;
  audit_note?: string;
  summary?: {
    total_evaluated_samples: number;
    mean_crps: number;
    overall_coverage_80_pct: number;
    total_models: number;
  };
  shootout?: ShootoutItem[];
}

export interface LedgerScoreboard {
  status: string;
  scoreboard: {
    total_served_predictions: number;
    verified_arrivals_count: number;
    empirical_80pct_coverage: number;
    target_coverage_pct: number;
    mean_absolute_error_min: number;
    mean_winkler_score: number;
    chain_integrity_verified: boolean;
    total_blocks_verified: number;
    chain_tip_hash: string;
    as_of: string;
  };
}

export interface LedgerVerificationResult {
  status: string;
  chain_integrity_verified: boolean;
  total_blocks_verified: number;
  broken_at_block_id: number | null;
}

export interface RakeTurnaround {
  incoming_train: string;
  incoming_name: string;
  outgoing_train: string;
  outgoing_name: string;
  turnaround_station: string;
  scheduled_turnaround_min: number;
  incoming_delay_min: number;
  remaining_buffer_min: number;
  buffer_deficit_min: number;
  projected_outgoing_delay_min: number;
  status: string;
}

export interface CascadeRippleData {
  status: string;
  target_station: string;
  run_date: string;
  summary: {
    total_rake_links_monitored: number;
    at_risk_turnarounds: number;
    total_passenger_connections_monitored: number;
    active_hold_advisories: number;
    total_net_tax_hours_saved: number;
  };
  rake_turnarounds: RakeTurnaround[];
  top_hold_advisories: Array<{
    from_train: string;
    to_train: string;
    pax_count: number;
    hold_decision: string;
    buffer_min: number;
  }>;
  as_of: string;
}

export interface TimeMachineStage {
  stage: string;
  label: string;
  checkpoint_station: {
    code: string;
    name: string;
    seq: number;
    distance_from_origin_km: number;
    remaining_km: number;
    recorded_delay_min: number;
  };
  ntes_prediction?: string;
  ntes_delay_min?: number;
  ntes_status?: string;
  railtwin_p50?: string;
  railtwin_p50_delay_min?: number;
  railtwin_range?: string;
  cone_width?: string;
  receipt_hash?: string;
  full_receipt_hash?: string;
  ledger_state?: string;
  actual_arrival?: string;
  actual_delay_min?: number;
  total_blocks_verified?: number;
}

export interface TimeMachineData {
  status: string;
  train_no: string;
  run_date: string;
  destination: {
    code: string;
    name: string;
    distance_km: number;
    sched_arr: string;
  };
  snapshots: {
    t6: TimeMachineStage;
    t3: TimeMachineStage;
    t1: TimeMachineStage;
    truth: TimeMachineStage;
  };
  as_of: string;
}

export interface PopularTrain {
  train_no: string;
  name: string;
  name_hi?: string;
  type: string;
  route_short: string;
  next_departure: string;
  status_lamp: 'green' | 'amber' | 'red';
  runs_today: boolean;
  delay_min: number;
}

export interface SearchResult {
  train_no: string;
  name: string;
  name_hi?: string;
  type?: string;
  origin?: { code: string; name: string };
  destination?: { code: string; name: string };
  route_short?: string;
  last_delay?: number;
  delay_min?: number;
}
