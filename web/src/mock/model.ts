import { F14Metric, HorizonMAE } from './types';

export interface V3ShootoutRow {
  rowLabel: string;
  splitScope: string;
  nEvents: number;
  champMae: number;
  v3Mae: number;
  deltaMae: number;
  crps49: number;
  cov80Pct: number;
  wilcoxonPVal: number;
  dmStat: number;
  winStatus: 'ACCEPTED' | 'PENDING' | 'TIED';
}

export interface FeatureGroup {
  domain: string;
  count: number;
  description: string;
  features: Array<{
    name: string;
    type: string;
    description: string;
  }>;
}

export interface GateRecord {
  gateId: string;
  title: string;
  status: 'PASSED' | 'PENDING';
  criteria: string;
  auditOutput: string;
}

export const V3_SHOOTOUT_BENCHMARKS: V3ShootoutRow[] = [
  {
    rowLabel: 'OVERALL BENCH_v3 (Fog Core)',
    splitScope: '2025-11-30 → 2026-01-01 (Winter Fog Holdout)',
    nEvents: 42380,
    champMae: 14.82,
    v3Mae: 9.45,
    deltaMae: -5.37,
    crps49: 6.82,
    cov80Pct: 83.1,
    wilcoxonPVal: 0.0001,
    dmStat: 6.42,
    winStatus: 'ACCEPTED',
  },
  {
    rowLabel: 'BENCH_NORMAL (2026 Normal Days)',
    splitScope: '2026-02-01 → 2026-08-31 (Summer/Monsoon Holdout)',
    nEvents: 184290,
    champMae: 8.65,
    v3Mae: 7.12,
    deltaMae: -1.53,
    crps49: 4.91,
    cov80Pct: 81.9,
    wilcoxonPVal: 0.0001,
    dmStat: 5.18,
    winStatus: 'ACCEPTED',
  },
  {
    rowLabel: 'CLASS: Mail / Express (Specialist)',
    splitScope: '190,579 events (High-speed passenger corridors)',
    nEvents: 71200,
    champMae: 11.24,
    v3Mae: 7.89,
    deltaMae: -3.35,
    crps49: 5.44,
    cov80Pct: 82.7,
    wilcoxonPVal: 0.0001,
    dmStat: 5.84,
    winStatus: 'ACCEPTED',
  },
  {
    rowLabel: 'CLASS: Passenger (Specialist)',
    splitScope: '91,132 events (Stopping / feeder operations)',
    nEvents: 34100,
    champMae: 13.91,
    v3Mae: 9.80,
    deltaMae: -4.11,
    crps49: 6.95,
    cov80Pct: 80.8,
    wilcoxonPVal: 0.0001,
    dmStat: 4.92,
    winStatus: 'ACCEPTED',
  },
];

export const V3_FEATURE_DOMAINS: FeatureGroup[] = [
  {
    domain: '1. Kinematics & Progress',
    count: 5,
    description: 'Real-time velocity, distance coordinates, and exponential horizon projections.',
    features: [
      { name: 'f_curr_delay_min', type: 'float', description: 'Point-in-time observed arrival/departure delay (min)' },
      { name: 'f_rolling_velocity_kmh', type: 'float', description: 'Observed speed over the last 3 traversed sections' },
      { name: 'f_sched_speed_kmh', type: 'float', description: 'Timetabled baseline speed for current block segment' },
      { name: 'f_km_remaining', type: 'float', description: 'Cumulative track kilometers to target station' },
      { name: 'f_exp_decay_ahead', type: 'float', description: 'Spatial decay projection weight ahead of current location' },
    ],
  },
  {
    domain: '2. Spatial Density & Interaction',
    count: 6,
    description: 'Dynamic block occupancy, opposing train headways, and cross-attention signals.',
    features: [
      { name: 'f_trains_ahead_15km', type: 'int', description: 'Preceding active trains within immediate 15 km block buffer' },
      { name: 'f_trains_ahead_45km', type: 'int', description: 'Preceding active trains within extended 45 km corridor' },
      { name: 'f_opposing_headway_min', type: 'float', description: 'Headway to nearest approaching train on adjacent track' },
      { name: 'f_loop_occupancy_ratio', type: 'float', description: 'Percentage of loop tracks occupied at upcoming station' },
      { name: 'f_section_density_km', type: 'float', description: 'Overall train density per kilometer in current block section' },
      { name: 'f_cortex_conflict_score', type: 'float', description: 'Cross-attention interaction score with neighbor trains' },
    ],
  },
  {
    domain: '3. Operational Linkages',
    count: 3,
    description: 'Rake turnaround propagation and active temporary speed restrictions.',
    features: [
      { name: 'f_rake_linked', type: 'binary', description: '1 if train shares rake with an incoming paired journey' },
      { name: 'f_rake_net_delay', type: 'float', description: 'Inbound rake arrival delay minus scheduled turnaround buffer' },
      { name: 'f_rake_buffer_pct', type: 'float', description: 'Percentage of turnaround maintenance buffer consumed' },
    ],
  },
  {
    domain: '4. Micro-Weather & Radiative Fog',
    count: 5,
    description: 'Hourly IST weather observations and dawn radiative fog interaction indicators.',
    features: [
      { name: 'f_temp_c', type: 'float', description: 'Point-in-time station ambient temperature (°C)' },
      { name: 'f_precip_mm', type: 'float', description: 'Hourly precipitation accumulation (mm)' },
      { name: 'f_fog_flag', type: 'binary', description: 'Active fog advisory flag from nearest meteorological station' },
      { name: 'f_visibility_m', type: 'float', description: 'Optical range / visibility distance in meters' },
      { name: 'f_fog_dawn', type: 'float', description: 'Winter dawn radiative fog interaction term (05:00–09:00 IST peak)' },
    ],
  },
  {
    domain: '5. Network Geography & Calendar',
    count: 5,
    description: 'Historical non-rescaled empirical percentiles, speed restrictions, and festival traffic surges.',
    features: [
      { name: 'f_hist_recency_avg', type: 'float', description: 'Exponentially weighted average delay over last 7 runs (min)' },
      { name: 'f_hist_p90', type: 'float', description: 'Empirical 90th percentile delay over last 60 runs (min)' },
      { name: 'f_tsr_count', type: 'int', description: 'Number of active Temporary Speed Restrictions on upcoming path' },
      { name: 'f_tsr_max_slow', type: 'float', description: 'Maximum percentage speed reduction across active TSR work zones' },
      { name: 'f_target_is_terminus', type: 'binary', description: '1 if target station is the final route terminus' },
    ],
  },
];

export const V3_VERIFICATION_GATES: GateRecord[] = [
  {
    gateId: 'G-1',
    title: 'Feature Liveliness & Information Content',
    status: 'PASSED',
    criteria: 'Zero dead features; variance > 0.0 and distinct values >= 2 on all train/val splits.',
    auditOutput: 'All 24 features confirmed active and alive across 434,382 snapshot rows.',
  },
  {
    gateId: 'G-2',
    title: 'Temporal Leakage Isolation',
    status: 'PASSED',
    criteria: 'Strict point-in-time evaluation: event_time <= as_of strictly enforced.',
    auditOutput: '100% temporal isolation confirmed; perturbing future data yields 0 change in features.',
  },
  {
    gateId: 'G-3',
    title: 'Duplicate & Collinearity Elimination',
    status: 'PASSED',
    criteria: 'Spearman rank correlation |rho| < 0.95 across all 276 feature pairs.',
    auditOutput: 'Zero duplicate features; empirical p90 vs recency avg rho = 0.912 < 0.95.',
  },
  {
    gateId: 'G-4',
    title: 'Regime Signatures & Spatial Variance',
    status: 'PASSED',
    criteria: 'Winter fog dawn signature >= 3x higher than summer baseline.',
    auditOutput: 'Winter fog avg = 0.092 vs Summer avg = 0.006 (14.9x regime contrast ratio).',
  },
  {
    gateId: 'G-5',
    title: 'Ingestion Coverage across Domain Registries',
    status: 'PASSED',
    criteria: '100% weather coverage, >=50% rake link coverage across network.',
    auditOutput: '100.0% weather coverage (608/608 days); 4,169 rake links covering 65.6% of snapshots.',
  },
  {
    gateId: 'G-6',
    title: 'Human-in-the-Loop Audit Inspection',
    status: 'PASSED',
    criteria: '20 sampled rows manually verified with human_ack_required = True.',
    auditOutput: 'Audit inspection table logged in artifact manifest.',
  },
  {
    gateId: 'G-7',
    title: 'Cryptographic Freeze (SHA-256)',
    status: 'PASSED',
    criteria: 'Deterministic dataset hash recorded in ml/artifacts_v3/feature_manifest.json.',
    auditOutput: 'Frozen SHA-256: 396d78ddb10811f203c98364e9d6d415529b3e58d23f038d5369bccc043072d5.',
  },
];

export const F14_PROOF_METRICS: F14Metric[] = [
  {
    metric: '1-Hour Horizon MAE (Arrival Error)',
    baseline1: '24.6 min',
    baseline2: '18.1 min',
    railtwin: '7.1 min (v3 MoE)',
    improvement: '-60.8% vs NTES (-71.1% vs Static)',
    targetAchieved: true,
  },
  {
    metric: '±10-Minute Hit Rate @ 1-Hour Horizon',
    baseline1: '41.2%',
    baseline2: '58.6%',
    railtwin: '86.2%',
    improvement: '+27.6% absolute gain over NTES',
    targetAchieved: true,
  },
  {
    metric: 'Non-Crossing Quantile Monotonicity',
    baseline1: '0.0% (unsupported)',
    baseline2: '0.0% (unsupported)',
    railtwin: '100.0%',
    improvement: '0 <= q05 <= q10 <= q50 <= q90 by construction',
    targetAchieved: true,
  },
  {
    metric: 'Conformal 80% Coverage (q10 to q90)',
    baseline1: '36.4% (overconfident)',
    baseline2: '61.2% (uncalibrated)',
    railtwin: '82.7%',
    improvement: 'Calibrated within target 75%–85% window',
    targetAchieved: true,
  },
  {
    metric: 'Epistemic Uncertainty Spread (Deep Ensemble)',
    baseline1: 'N/A (single estimate)',
    baseline2: 'N/A (single estimate)',
    railtwin: '±1.8 min',
    improvement: 'Tri-seed variance alerts on novel disruptions',
    targetAchieved: true,
  },
  {
    metric: 'Platform Conflict Detection Lead Time',
    baseline1: '0 min (reactive on arrival)',
    baseline2: '12 min (linear projection)',
    railtwin: '42.5 min',
    improvement: '+30.5 min earlier notice',
    targetAchieved: true,
  },
];

export const HORIZON_MAE_DATA: HorizonMAE[] = [
  { horizon: '15 min', baseline1: 8.2, baseline2: 5.8, railtwin: 2.1 },
  { horizon: '30 min', baseline1: 14.5, baseline2: 10.4, railtwin: 4.2 },
  { horizon: '60 min', baseline1: 24.6, baseline2: 18.1, railtwin: 7.1 },
  { horizon: '120 min', baseline1: 42.1, baseline2: 32.5, railtwin: 12.3 },
  { horizon: '240 min', baseline1: 76.4, baseline2: 58.2, railtwin: 21.6 },
];

export const METHODOLOGY_NOTES = [
  {
    title: 'Point-in-Time Temporal Split Integrity',
    description: 'Models trained on strict chronological splits and verified with zero future data leakage across 434,382 actual station arrival snapshots on the NDLS–CNB–DDU trunk route.',
  },
  {
    title: '24-Feature Unified Feature Store',
    description: 'Incorporates dynamic spatial density, opposing headways, upstream rake turnaround buffer consumption, hourly IST micro-weather, and active speed restrictions.',
  },
  {
    title: 'Regime Mixture-of-Experts (MoE)',
    description: 'Three monotone quantile experts dynamically gated across clear track, network congestion, and dawn radiative fog regimes with mathematically proven non-crossing quantile guarantees.',
  },
];
