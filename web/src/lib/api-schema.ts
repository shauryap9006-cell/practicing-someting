/**
 * RailTwin-X Auto-Generated OpenAPI Client Types (F39).
 * Generated from FastAPI OpenAPI 3.1.0 specification.
 * DO NOT EDIT MANUALLY - run `python scripts/generate_openapi_types.py`.
 */

export interface AckInRequest {
  acknowledgment_notes?: string | null;
}

export interface AckNotificationRequest {
  /** Acknowledgment channel (in_app, whatsapp, sms) */
  channel?: string;
  /** Optional ACK remarks */
  notes?: string | null;
}

export interface AuditLogItem {
  id: number;
  ts: string;
  actor_id: string;
  actor_role: string;
  action: string;
  table_name: string;
  record_id: string;
  before_state: string | null;
  after_state: string | null;
  row_hash: string;
  prev_hash: string;
}

export interface AuditQueryResponse {
  total: number;
  limit: number;
  offset: number;
  logs: AuditLogItem[];
}

export interface BackupRecord {
  id: number;
  filename: string;
  backup_ts: string;
  size_bytes: number;
  row_counts_json: string | null;
  status: string;
  checksum_sha256: string;
}

export interface BlockStateUpdate {
  /** CLEAR, OCCUPIED, BLOCKED, CAUTION */
  state: string;
  occupied_by_train?: string | null;
  notes?: string | null;
}

export interface BreathalyzerTestCreate {
  staff_id: string;
  staff_name: string;
  /** loco_pilot, alp, guard, station_master, shunter */
  role?: string;
  train_no?: string | null;
  /** SIGN_ON, SIGN_OFF, SURPRISE_CHECK */
  duty_type?: string;
  /** Alcohol reading in mg/100ml BAC */
  reading_mg_100ml?: number;
  notes?: string | null;
}

export interface ClaimItemRequest {
  claimant_name: string;
  claimant_id_proof: string;
  claimant_phone: string;
}

export interface CleaningLogCreate {
  station_code?: string;
  /** PLATFORM, WAITING_HALL, TOILET, CONCOURSE, FOOT_OVER_BRIDGE */
  area_type?: string;
  platform_number?: number | null;
  score_1_to_5?: number;
  contractor_name?: string | null;
  notes?: string | null;
}

export interface CommercialStallCreate {
  /** e.g. STALL-NDLS-PF1-01 */
  stall_code: string;
  station_code?: string;
  platform_number?: number;
  /** CATERING, TEA_STALL, BOOKSTALL, ATM, PHARMACY, CLOAK_ROOM */
  stall_type?: string;
  vendor_name: string;
  contact_phone?: string | null;
  monthly_rent_inr?: number;
  lease_start_date: string;
  lease_expiry_date: string;
  notes?: string | null;
}

export interface CompleteStepRequest {
  step_index: number;
}

export interface ConfidenceBand {
  /** 10th percentile optimistic delay */
  best_p10_min: number;
  /** 50th percentile median delay */
  likely_p50_min: number;
  /** 90th percentile pessimistic delay */
  worst_p90_min: number;
  best_arrival: string;
  likely_arrival: string;
  worst_arrival: string;
}

export interface CreateUserRequest {
  /** Unique username */
  username: string;
  email?: string | null;
  /** Plaintext password */
  password: string;
  /** Role ID (e.g. station_master, dy_sm, engineer) */
  role_id: string;
  /** Station code assignment */
  station_code?: string;
  /** Full display name */
  full_name: string;
}

export interface CrewAlertItem {
  crew_id: string;
  train_no: string;
  duty_signon_time: string;
  projected_trip_end_time: string;
  duty_cap_hours: number;
  projected_duty_hours: number;
  breach_minutes: number;
  recommended_relief_station: string;
  is_advisory?: boolean;
  message: string;
}

export interface CrewAlertsResponse {
  /** ISO timestamp in IST */
  updated_at: string;
  /** 'live' or 'replay' */
  clock_mode: string;
  total_alerts: number;
  alerts: CrewAlertItem[];
}

export interface CrewSignOnRequest {
  crew_id: string;
  staff_name: string;
  /** loco_pilot, alp, guard */
  role?: string;
  train_no: string;
  station_code?: string;
  duty_hours_limit?: number;
}

export interface DelayAutopsyResponse {
  /** ISO timestamp in IST */
  updated_at: string;
  /** 'live' or 'replay' */
  clock_mode: string;
  train_no: string;
  train_name: string;
  total_predicted_delay_min: number;
  is_exact_accounting?: boolean;
  causes: DelayCauseItem[];
}

export interface DelayCauseItem {
  event_type: string;
  minutes: number;
  cause: string;
  station_code?: string | null;
}

export interface DelayCertificateRequest {
  /** Train number e.g. 12004 */
  train_no: string;
  /** Station code e.g. NDLS */
  station_code: string;
  pnr_no?: string | null;
  /** Passenger full name */
  issued_to_name?: string;
  reason?: string | null;
}

/** Dispatcher acknowledgement payload. */
export interface DispatcherAckRequest {
  decision: string;
  dispatcher_id?: string | null;
  comment?: string | null;
}

export interface DispatcherAckResponse {
  adv_id: string;
  decision: string;
  dispatcher_id: string | null;
  comment: string | null;
  recorded_at: string;
  status?: string;
}

export interface DraftHandoverRequest {
  /** Station code */
  station_code?: string;
  /** Date of shift (YYYY-MM-DD) */
  shift_date: string;
  /** Shift type: morning, afternoon, night */
  shift_type?: string;
  /** Free-text operational remarks from outgoing SM */
  operational_notes?: string | null;
}

export interface EmitNotificationRequest {
  /** Event type code (e.g. PLATFORM_CHANGE, TSR_ACTIVE, CREW_BREACH) */
  event_type: string;
  /** Target roles to receive alert */
  target_roles?: string[];
  /** Severity: info, warning, critical */
  severity?: string;
  /** Brief alert title */
  title: string;
  /** Detailed alert body */
  message: string;
  /** Structured event payload */
  payload?: Record<string, any> | null;
  /** Station code */
  station_code?: string;
}

export interface HTTPValidationError {
  detail?: ValidationError[];
}

export interface HandoffRequest {
  section_id?: string;
  from_station?: string;
  to_station?: string;
  train_no?: string;
  notes?: string | null;
}

export interface HandoverResponse {
  id: number;
  station_code: string;
  shift_date: string;
  shift_type: string;
  outgoing_user_id: string;
  outgoing_user_name?: string | null;
  incoming_user_id?: string | null;
  incoming_user_name?: string | null;
  outgoing_signed_at?: string | null;
  incoming_acked_at?: string | null;
  open_incidents: Record<string, any>[];
  active_srs: Record<string, any>[];
  active_possessions: Record<string, any>[];
  crew_exceptions: Record<string, any>[];
  operational_notes?: string | null;
  status: string;
}

export interface HealthResponse {
  status: string;
  db: string;
  models: string;
  whatsapp?: string;
  clock_mode: string;
  updated_at: string;
}

export interface IncidentReportCreate {
  /** SPAD, DERAILMENT, EQUIPMENT_FAIL, NEAR_MISS, GATE_BURST, OHE_BREAKDOWN, TRESPASSING */
  incident_type: string;
  /** MINOR, MAJOR, CRITICAL */
  severity: string;
  station_code: string;
  location_km?: number | null;
  train_no?: string | null;
  summary: string;
  action_taken?: string | null;
}

export interface IntegrityVerifyResponse {
  is_valid: boolean;
  total_records_checked: number;
  error_detail?: string | null;
}

export interface JourneyStop {
  seq: number;
  station_code: string;
  station_name: string;
  distance_km: number;
  sched_arr: string | null;
  predicted_arr: string | null;
  sched_dep: string | null;
  predicted_dep: string | null;
  delay_min: number;
  /** 'green', 'amber', or 'red' */
  status_color: string;
  band: ConfidenceBand;
}

export interface LCStatusUpdate {
  /** NORMAL, DEFECTIVE, BOOM_DAMAGED, INTERLOCK_FAIL, MAINTENANCE */
  status: string;
  notes?: string | null;
}

export interface LineClearGrantRequest {
  train_no: string;
  notes?: string | null;
}

export interface LoginRequest {
  /** Username (e.g. sm_ndls, admin) */
  username: string;
  /** Plaintext password */
  password: string;
}

export interface LoginResponse {
  access_token: string;
  token_type?: string;
  user: UserProfile;
}

export interface LostItemCreate {
  /** BAG_LUGGAGE, ELECTRONICS, WALLET_CASH, DOCUMENT_ID, CLOTHING, OTHER */
  item_type?: string;
  /** Item details, color, brand */
  description: string;
  /** e.g. Platform 1 Waiting Hall, Coach B3 Seat 42 */
  found_location: string;
  station_code?: string;
  train_no?: string | null;
  custody_location?: string | null;
}

export interface ModelMeta {
  /** Champion model architecture name */
  name: string;
  /** Pinned model artifact SHA-256 */
  sha256: string;
  /** Model training version */
  version?: string;
}

export interface ModelsMetaResponse {
  /** ISO timestamp in IST */
  updated_at: string;
  /** 'live' or 'replay' */
  clock_mode: string;
  manifest: Record<string, any>;
  metrics: Record<string, any>;
}

export interface NetworkStateResponse {
  /** ISO timestamp in IST */
  updated_at: string;
  /** 'live' or 'replay' */
  clock_mode: string;
  active_trains_count: number;
  delayed_trains_count: number;
  active_conflicts_count: number;
  trains: NetworkTrainState[];
  active_tsrs: Record<string, any>[];
}

export interface NetworkTrainState {
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

export interface NotificationItem {
  id: number;
  event_type: string;
  target_role: string | null;
  severity: string;
  title: string;
  message: string;
  payload_json: string | null;
  state: string;
  created_at: string;
  escalated_at?: string | null;
  acked_at?: string | null;
  acked_by?: string | null;
}

export interface PlanChangesetRequest {
  /** Station code */
  station_code?: string;
  /** YYYY-MM-DD */
  plan_date: string;
  mutations: PlanItemMutation[];
}

export interface PlanItemMutation {
  train_no: string;
  /** reassign_platform, retimed, cancel */
  action: string;
  target_platform?: number | null;
  new_arr?: string | null;
  new_dep?: string | null;
  reason?: string | null;
}

export interface PlatformAssignRequest {
  /** Station code */
  station_code?: string;
  train_no: string;
  /** YYYY-MM-DD */
  run_date: string;
  platform: number;
  /** HH:MM */
  assigned_arr: string;
  /** HH:MM */
  assigned_dep: string;
  /** Lock assignment against AI re-optimization */
  is_locked?: boolean;
}

export interface PlatformBlockRequest {
  /** Station code */
  station_code?: string;
  /** Platform number */
  platform: number;
  /** BLOCKED_MAINT, OUT_OF_SERVICE, FREE */
  state?: string;
  reason?: string | null;
}

export interface PlatformGanttBlock {
  train_no: string;
  train_name?: string;
  train_class?: string;
  platform: number;
  start_time: string;
  end_time: string;
  dwell_min?: number;
  is_conflicted?: boolean;
}

export interface PlatformGanttConflict {
  platform: number;
  train_1: string;
  train_2: string;
  overlap_start: string;
  overlap_end: string;
  overlap_duration_min: number;
}

export interface PlatformLockRequest {
  is_locked?: boolean;
}

export interface PositionMeta {
  /** Bayesian posterior mode sequence position */
  mode_seq: number;
  /** Estimated current station/block code */
  station_code: string;
  /** Posterior probability confidence score [0.0 - 1.0] */
  confidence: number;
  /** 'last_event', 'dead_reckoning', 'human_confirmed', or 'explicit_query' */
  basis: string;
  /** 'station_events', 'ad_events', or 'manual' */
  source: string;
  /** Seconds elapsed since last confirmed telemetry event */
  age_seconds: number;
  posterior_probs?: Record<string, number> | null;
}

export interface PossessionRequest {
  /** BLOCK_SECTION, PLATFORM, OHE_LINE, YARD_TRACK */
  possession_type: string;
  /** e.g. BLK-NDLS-GZB or PF-NDLS-1 */
  element_id: string;
  station_code: string;
  start_time: string;
  end_time: string;
  /** P_WAY, OHE_TRACTION, S_AND_T, BRIDGE_WORK, GENERAL */
  work_type?: string;
  requesting_dept: string;
  notes?: string | null;
}

export interface PredictionDriver {
  /** Feature name attributing delay delta */
  feature: string;
  /** Impact in minutes (positive increases delay, negative decreases) */
  contribution_min: number;
  /** 'increases_delay', 'decreases_delay', or 'neutral' */
  direction: string;
}

export interface RakeBpcCreate {
  rake_id: string;
  train_no?: string | null;
  bpc_number: string;
  bpc_issue_date: string;
  bpc_valid_until: string;
  /** PREMIUM, CC_INTENSIVE, END_TO_END, SPECIAL */
  bpc_type?: string;
  brake_power_percent?: number;
  air_brake_pressure_kg?: number;
  coach_count?: number;
  notes?: string | null;
}

export interface ReoptimizeRequest {
  target_date?: string | null;
}

export interface ReoptimizeResponse {
  /** ISO timestamp in IST */
  updated_at: string;
  /** 'live' or 'replay' */
  clock_mode: string;
  station_code: string;
  conflicts_before: number;
  conflicts_after: number;
  resolved_conflicts: number;
  swaps_performed: Record<string, any>[];
  execution_time_seconds: number;
  blocks: PlatformGanttBlock[];
}

export interface ResolveWorkOrderRequest {
  resolution_notes: string;
}

export interface SetInRequest {
  /** Station code */
  station_code?: string;
  /** Actual platform occupied */
  platform: number;
  /** ISO timestamp or HH:MM (defaults to now) */
  actual_ts?: string | null;
  predicted_ts?: string | null;
}

export interface SetOutRequest {
  /** Station code */
  station_code?: string;
  /** Platform departed from */
  platform: number;
  /** ISO timestamp or HH:MM (defaults to now) */
  actual_ts?: string | null;
}

export interface ShiftAssignmentCreate {
  staff_id: string;
  staff_name: string;
  role_id: string;
  station_code?: string;
  shift_date: string;
  /** morning, afternoon, night */
  shift_type?: string;
}

export interface ShuntingMoveCreate {
  /** Station code */
  station_code?: string;
  /** loco_attach, loco_detach, rake_release, yard_shunt, empty_haul */
  move_type?: string;
  /** Locomotive identifier e.g. WAP7-30214 */
  loco_id: string;
  /** Rake identifier */
  rake_id?: string | null;
  /** Starting track or platform e.g. PF1, Yard-Line-4 */
  from_track: string;
  /** Destination track or platform e.g. Siding-2, PF3 */
  to_track: string;
  /** Scheduled start HH:MM */
  start_time: string;
  /** Scheduled completion HH:MM */
  end_time: string;
  notes?: string | null;
}

export interface ShuntingStatusUpdate {
  /** REQUESTED, APPROVED, IN_PROGRESS, COMPLETED, CANCELLED */
  status: string;
  notes?: string | null;
}

export interface SignOutRequest {
  operational_notes?: string | null;
}

export interface SpeedRestrictionCreate {
  /** From station code */
  from_code: string;
  /** To station code */
  to_code: string;
  start_km?: number;
  end_km?: number;
  /** Restricted speed in km/h */
  speed_limit_kmph: number;
  /** Reason e.g. Track renewal, deep screening */
  cause: string;
  /** TEMPORARY or PERMANENT */
  permanent_or_temp?: string;
  /** ISO date or timestamp */
  effective_from: string;
  effective_to?: string | null;
}

export interface StartSOPRequest {
  template_id: string;
  station_code: string;
}

export interface StationAssetCreate {
  /** e.g. SIG-NDLS-01 or TN-NDLS-22 */
  asset_tag: string;
  /** TURNOUT, SIGNAL, OHE_SECTION, TRACK_CIRCUIT, POINT_MACHINE, CCTV, PA_SPEAKER */
  asset_type?: string;
  station_code?: string;
  platform_or_track?: string;
  last_serviced_date: string;
  next_service_due: string;
  notes?: string | null;
}

export interface StationGanttResponse {
  /** ISO timestamp in IST */
  updated_at: string;
  /** 'live' or 'replay' */
  clock_mode: string;
  station_code: string;
  station_name: string;
  total_platforms: number;
  conflicts_count: number;
  blocks: PlatformGanttBlock[];
  conflicts: PlatformGanttConflict[];
}

export interface TimetableEntryCreate {
  version_id: string;
  train_no: string;
  train_name: string;
  /** express, passenger, freight, emu, special */
  train_type?: string;
  /** UP or DOWN */
  direction?: string;
  station_code: string;
  stop_seq: number;
  sched_arr?: string | null;
  sched_dep?: string | null;
  halt_min?: number;
  platform_default?: number;
  days_of_run?: string;
}

export interface TimetableEntryUpdate {
  train_name?: string | null;
  train_type?: string | null;
  direction?: string | null;
  sched_arr?: string | null;
  sched_dep?: string | null;
  halt_min?: number | null;
  platform_default?: number | null;
  days_of_run?: string | null;
  is_cancelled?: boolean | null;
  cancellation_reason?: string | null;
}

export interface TimetableVersionCreate {
  /** e.g. WTT 2026 Monsoon Edition v1 */
  version_name: string;
  /** YYYY-MM-DD */
  effective_from: string;
  /** YYYY-MM-DD */
  effective_to?: string | null;
  description?: string | null;
}

export interface TrainEtaResponse {
  /** ISO timestamp in IST */
  updated_at: string;
  /** 'live' or 'replay' */
  clock_mode: string;
  train_no: string;
  train_name: string;
  target_station: string;
  sched_arr: string | null;
  predicted_arr: string;
  predicted_delay_min: number;
  confidence_band: ConfidenceBand;
  /** 'Tier2_LightGBM_CQR', 'Tier2_PyTorch_GRU_Champion', or 'Tier1_HistLookup' */
  tier_used: string;
  model?: ModelMeta | null;
  position?: PositionMeta | null;
  /** Corridor feature store version */
  feature_version?: string;
  /** Point-in-time ISO timestamp when features were sampled */
  as_of_ts: string;
  /** Freshness of underlying event feed */
  data_freshness_seconds?: number;
  /** Top-3 feature attribution delay drivers */
  drivers?: PredictionDriver[];
  model_provenance?: Record<string, any> | null;
}

export interface TrainJourneyResponse {
  /** ISO timestamp in IST */
  updated_at: string;
  /** 'live' or 'replay' */
  clock_mode: string;
  train_no: string;
  train_name: string;
  train_class: string;
  current_station: string;
  current_delay_min: number;
  timeline: JourneyStop[];
}

export interface UpdateUserRequest {
  email?: string | null;
  role_id?: string | null;
  station_code?: string | null;
  full_name?: string | null;
  is_active?: boolean | null;
  new_password?: string | null;
}

export interface UserDetailResponse {
  id: string;
  username: string;
  email: string | null;
  role_id: string;
  role_name: string;
  station_code: string;
  full_name: string;
  is_active: boolean;
  created_at: string;
}

export interface UserProfile {
  id: string;
  username: string;
  email?: string | null;
  role_id: string;
  role_name: string;
  station_code: string;
  full_name: string;
  permissions_json?: string | null;
}

export interface ValidationError {
  loc: string | number[];
  msg: string;
  type: string;
  input?: any;
  ctx?: Record<string, any>;
}

export interface WhatIfRequest {
  train_no: string;
  station_code: string;
  injected_delay_min: number;
  active_tsrs?: Record<string, number> | null;
}

export interface WhatIfResponse {
  /** ISO timestamp in IST */
  updated_at: string;
  /** 'live' or 'replay' */
  clock_mode: string;
  run_id: string;
  scenario: Record<string, any>;
  affected_trains_count: number;
  affected_trains: Record<string, any>[];
  ledger_events: Record<string, any>[];
}

export interface WhatsAppWebhookResponse {
  ok: boolean;
  event?: string | null;
  action?: string | null;
  adv_id?: string | null;
  sender?: string | null;
}

export interface WorkOrderCreate {
  asset_tag: string;
  station_code?: string;
  issue_description: string;
  /** LOW, MEDIUM, HIGH, URGENT */
  priority?: string;
  assigned_to?: string | null;
}
