import { mockStore } from '@/mock/store';
import { getCurrentSession } from '@/mock/auth';
import {
  StationCode,
  Train,
  Station,
  PlatformInfo,
  CrewMember,
  Advisory,
  MaintenanceBlock,
  AuditEntry,
} from '@/mock/types';

export type DataSourceState = 'LIVE' | 'STALE' | 'OFFLINE' | 'DEMO';

export interface DataSourceStatus {
  state: DataSourceState;
  lastSuccessfulFetch: number | null;
  lastAttempt: number | null;
  errorMessage?: string;
  isDemoMode: boolean;
}

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

function checkIsExplicitDemoMode(): boolean {
  if (typeof window === 'undefined') return false;
  const params = new URLSearchParams(window.location.search);
  return params.get('demo') === '1' || localStorage.getItem('railtwin_demo_mode') === 'true';
}

let dataSourceStatus: DataSourceStatus = {
  state: checkIsExplicitDemoMode() ? 'DEMO' : 'LIVE',
  lastSuccessfulFetch: null,
  lastAttempt: null,
  isDemoMode: checkIsExplicitDemoMode(),
};

const listeners = new Set<(status: DataSourceStatus) => void>();

export function subscribeDataSourceStatus(cb: (status: DataSourceStatus) => void): () => void {
  listeners.add(cb);
  cb(dataSourceStatus);
  return () => listeners.delete(cb);
}

function updateStatus(updates: Partial<DataSourceStatus>) {
  dataSourceStatus = { ...dataSourceStatus, ...updates };
  listeners.forEach((cb) => cb(dataSourceStatus));
}

// Helper to make authenticated backend requests with explicit data-source contract (F22)
async function fetchBackend<T>(
  path: string,
  options: RequestInit = {},
  fallbackFn?: () => Promise<T> | T
): Promise<T> {
  const session = getCurrentSession();
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string>),
  };

  if (session?.user?.token) {
    headers['Authorization'] = `Bearer ${session.user.token}`;
  }

  const isDemo = checkIsExplicitDemoMode();
  updateStatus({ lastAttempt: Date.now(), isDemoMode: isDemo });

  if (isDemo && fallbackFn) {
    updateStatus({ state: 'DEMO' });
    return await fallbackFn();
  }

  try {
    const res = await fetch(`${API_BASE}${path}`, {
      ...options,
      headers,
    });

    if (res.ok) {
      updateStatus({
        state: 'LIVE',
        lastSuccessfulFetch: Date.now(),
        errorMessage: undefined,
      });
      return await res.json();
    } else {
      const errText = await res.text();
      updateStatus({
        state: 'OFFLINE',
        errorMessage: `HTTP ${res.status}: ${errText}`,
      });
      if (isDemo && fallbackFn) {
        return await fallbackFn();
      }
      throw new Error(`API Error ${res.status} on ${path}: ${errText}`);
    }
  } catch (err: any) {
    updateStatus({
      state: 'OFFLINE',
      errorMessage: err?.message || 'Network request failed',
    });
    if (isDemo && fallbackFn) {
      return await fallbackFn();
    }
    throw err;
  }
}

export function getDataSourceStatus(): DataSourceStatus {
  return dataSourceStatus;
}

export function checkBackendStatus(): boolean {
  return dataSourceStatus.state === 'LIVE';
}


export const api = {
  // 1. Core Station & Network State
  async getStation(code?: StationCode): Promise<Station> {
    return fetchBackend(`/v1/network/state`, {}, () => mockStore.getStation(code));
  },

  async switchStation(code: StationCode, actor?: string): Promise<Station> {
    mockStore.setActiveStation(code, actor);
    return mockStore.getStation(code);
  },

  // 2. Trains & ETA
  async getTrains(): Promise<Train[]> {
    return fetchBackend(`/v1/meta/trains`, {}, () => mockStore.getTrains());
  },

  async getTrain(number: string): Promise<Train | null> {
    return fetchBackend(`/v1/trains/${number}/journey`, {}, () => mockStore.getTrain(number) || null);
  },

  async getTrainAutopsy(number: string) {
    return fetchBackend(`/v1/trains/${number}/autopsy`, {}, () => {
      const t = mockStore.getTrain(number);
      return { train_no: number, delay_autopsy: t?.delayAutopsy || [] };
    });
  },

  // 3. Platform Gantt
  async getPlatforms(code?: StationCode): Promise<PlatformInfo[]> {
    return fetchBackend(`/api/platform/states`, {}, () => mockStore.getPlatforms(code));
  },

  async reoptimizePlatforms(stationCode?: StationCode): Promise<{ resolvedCount: number; swapsCount: number }> {
    return fetchBackend(`/v1/advise`, { method: 'POST', body: JSON.stringify({ station_code: stationCode || 'CNB' }) }, () =>
      mockStore.reoptimizePlatforms(stationCode)
    );
  },

  // 4. Advisories & Triage
  async getAdvisories(): Promise<Advisory[]> {
    return fetchBackend(`/v1/crew/alerts`, {}, () => mockStore.getAdvisories());
  },

  async acceptAdvisory(id: string, reason?: string, actor?: string): Promise<boolean> {
    return fetchBackend(`/v1/advise/${id}/ack`, { method: 'POST', body: JSON.stringify({ decision: 'accepted', reason }) }, () =>
      mockStore.acceptAdvisory(id, reason, actor)
    );
  },

  async dismissAdvisory(id: string, reason?: string, actor?: string): Promise<boolean> {
    return fetchBackend(`/v1/advise/${id}/ack`, { method: 'POST', body: JSON.stringify({ decision: 'dismissed', reason }) }, () =>
      mockStore.dismissAdvisory(id, reason, actor)
    );
  },

  // 5. Crew Duty
  async getCrew(): Promise<CrewMember[]> {
    return fetchBackend(`/api/workforce/crew/roster`, {}, () => mockStore.getCrew());
  },

  async requestCrewRelief(crewId: string, actor?: string): Promise<boolean> {
    return fetchBackend(`/api/workforce/crew/signon`, { method: 'POST', body: JSON.stringify({ crew_id: crewId }) }, () =>
      mockStore.requestCrewRelief(crewId, actor)
    );
  },

  // 6. Maintenance Track Blocks
  async getMaintenance(): Promise<MaintenanceBlock[]> {
    return fetchBackend(`/api/safety/possessions`, {}, () => mockStore.getMaintenance());
  },

  // 7. Audit & Integrity
  async getAuditLogs(): Promise<AuditEntry[]> {
    return fetchBackend(`/api/audit/logs`, {}, () => mockStore.getAuditLogs());
  },

  async verifyAuditIntegrity(): Promise<{ valid: boolean; entriesChecked: number; rootHash: string; algorithm: string }> {
    return fetchBackend(`/api/audit/verify-integrity`, {}, () => ({
      valid: true,
      entriesChecked: mockStore.getAuditLogs().length,
      rootHash: '0x8f2a11b9c402e9a781b0451cf982aa10e82c',
      algorithm: 'SHA-256 (HMAC Linked Chain)',
    }));
  },

  // 8. Model Proof
  async getModelProof() {
    return fetchBackend(`/v1/evaluation/summary`, {}, () => mockStore.getModelProof());
  },

  // 9. Operations: Timetable Manager
  async getTimetableVersions() {
    return fetchBackend(`/api/timetable/versions`, {}, () => [
      { id: 'tt-v2.1', version_name: 'WTT Winter 2026 (Published)', status: 'PUBLISHED', effective_from: '2026-01-01', total_trains: 58, published_at: '2026-01-01T00:00:00Z' },
      { id: 'tt-v2.2-draft', version_name: 'WTT Spring 2026 Special (Draft)', status: 'DRAFT', effective_from: '2026-04-01', total_trains: 64, published_at: null },
      { id: 'tt-v2.0', version_name: 'WTT Autumn 2025 (Archived)', status: 'ARCHIVED', effective_from: '2025-10-01', total_trains: 52, published_at: '2025-10-01T00:00:00Z' },
    ]);
  },

  async getTimetableEntries(versionId: string) {
    return fetchBackend(`/api/timetable/versions/${versionId}/entries`, {}, () => ({
      version_id: versionId,
      entries: mockStore.getTrains().map(t => ({
        id: `tt-entry-${t.number}`,
        train_no: t.number,
        train_name: t.name,
        type: t.type,
        origin: t.origin,
        destination: t.destination,
        sched_arr: t.scheduledArrival,
        sched_dep: t.scheduledDeparture,
        default_platform: t.platform,
        days_of_run: 'Daily',
      })),
    }));
  },

  async publishTimetableVersion(versionId: string) {
    return fetchBackend(`/api/timetable/versions/${versionId}/publish`, { method: 'POST' }, () => ({
      success: true,
      version_id: versionId,
      status: 'PUBLISHED',
    }));
  },

  // 10. Operations: Block Sections
  async getBlockSections() {
    return fetchBackend(`/api/blocks/status`, {}, () => [
      { id: 'BLK-CNB-ON-UP', section_name: 'Kanpur Central – Unnao (UP Main)', state: 'CAUTION', speed_limit: 30, occupant: '12424', time_in_state: '14m' },
      { id: 'BLK-CNB-ON-DN', section_name: 'Unnao – Kanpur Central (DN Main)', state: 'CLEAR', speed_limit: 110, occupant: null, time_in_state: '42m' },
      { id: 'BLK-ETW-TDL-UP', section_name: 'Etawah – Tundla (UP Main)', state: 'OCCUPIED', speed_limit: 120, occupant: '12301', time_in_state: '8m' },
      { id: 'BLK-ETW-TDL-DN', section_name: 'Tundla – Etawah (DN Main)', state: 'BLOCKED', speed_limit: 0, occupant: 'MNT-01', time_in_state: '1h 12m' },
      { id: 'BLK-GZB-ALJN-UP', section_name: 'Ghaziabad – Aligarh (UP Main)', state: 'CLEAR', speed_limit: 130, occupant: null, time_in_state: '28m' },
      { id: 'BLK-DFC-ROOMA', section_name: 'Rooma DFC Siding Line 4', state: 'OCCUPIED', speed_limit: 25, occupant: 'BOXN-7041', time_in_state: '22m' },
    ]);
  },

  // 11. Operations: Shunting & Loco Moves
  async getShuntingMoves() {
    return fetchBackend(`/api/ops/shunting`, {}, () => [
      { id: 'SHT-01', move_type: 'Loco Reversal', rake_id: 'RAKE-DLI-SHT-04', from_track: 'PF 3', to_track: 'Siding 2', window: '17:50 – 18:10', status: 'OK', logged_by: 'SM-CNB' },
      { id: 'SHT-02', move_type: 'Rake Stabling', rake_id: 'RAKE-BOXN-7041', from_track: 'Rooma L4', to_track: 'Juhi Yard', window: '18:15 – 18:45', status: 'FLAGGED', logged_by: 'CTRL-PRYJ' },
      { id: 'SHT-03', move_type: 'Coach Attachment', rake_id: 'RAKE-BSBS-06', from_track: 'Sick Line', to_track: 'PF 5', window: '18:30 – 18:40', status: 'OK', logged_by: 'SM-CNB' },
    ]);
  },

  async logShuntingMove(data: Record<string, unknown>) {
    return fetchBackend(`/api/ops/shunting`, { method: 'POST', body: JSON.stringify(data) }, () => ({
      success: true,
      id: `SHT-${Math.floor(10 + Math.random() * 90)}`,
      ...data,
    }));
  },

  // 12. Safety: TSR / Caution Orders
  async getTSRs() {
    return fetchBackend(`/api/safety/tsr`, {}, () => [
      { id: 'TSR-2026-081', order_no: 'CO-NCR-CNB-1014', section: 'CNB – ON', start_km: 1012.4, end_km: 1018.6, speed_limit_kmph: 30, cause: 'Ganga Bridge Girder Inspection', status: 'ACTIVE', effective_from: '2026-08-28 14:00', effective_to: '2026-08-28 18:30' },
      { id: 'TSR-2026-082', order_no: 'CO-NCR-ETW-0942', section: 'ETW – TDL', start_km: 942.0, end_km: 949.0, speed_limit_kmph: 45, cause: 'CSM Ballast Tamping', status: 'ACTIVE', effective_from: '2026-08-28 16:30', effective_to: '2026-08-28 20:00' },
      { id: 'TSR-2026-079', order_no: 'CO-NR-GZB-0028', section: 'GZB – ALJN', start_km: 28.0, end_km: 35.0, speed_limit_kmph: 20, cause: 'Deep Screening Finished', status: 'EXPIRED', effective_from: '2026-08-28 08:00', effective_to: '2026-08-28 13:00' },
    ]);
  },

  async createTSR(data: Record<string, unknown>) {
    return fetchBackend(`/api/safety/tsr`, { method: 'POST', body: JSON.stringify(data) }, () => ({
      success: true,
      id: `TSR-${Math.floor(100 + Math.random() * 900)}`,
      ...data,
    }));
  },

  async liftTSR(id: string) {
    return fetchBackend(`/api/safety/tsr/${id}/lift`, { method: 'POST' }, () => ({
      success: true,
      id,
      status: 'LIFTED',
    }));
  },

  // 13. Safety: Incidents Register
  async getIncidents() {
    return fetchBackend(`/api/safety/incidents`, {}, () => [
      { id: 'INC-2026-009', time: '16:42 IST', type: 'Track Circuit Glitch', location: 'Panki West Cabin (TC-44)', severity: 'minor', status: 'Investigating', reporter: 'Signal Maint Gang 3', description: 'Intermittent phantom drop on track circuit 44A during light drizzle.' },
      { id: 'INC-2026-008', time: '14:15 IST', type: 'OHE Tripping (25kV)', location: 'Unnao Yard Substation', severity: 'major', status: 'Closed', reporter: 'Traction Power Controller', description: 'Feeder CB tripped on overcurrent; auto-reclosed after 90 seconds.' },
      { id: 'INC-2026-007', time: '11:00 IST', type: 'Near Miss / Trespass', location: 'KM 1008 Level Crossing', severity: 'critical', status: 'Closed', reporter: 'LP 12034 Shatabdi', description: 'Cattle herd removed from tracks by RPF patrol team.' },
    ]);
  },

  async logIncident(data: Record<string, unknown>) {
    return fetchBackend(`/api/safety/incidents`, { method: 'POST', body: JSON.stringify(data) }, () => ({
      success: true,
      id: `INC-${Math.floor(1000 + Math.random() * 9000)}`,
      ...data,
    }));
  },

  // 14. Safety: Emergency SOP Runner
  async getSOPTemplates() {
    return fetchBackend(`/api/safety/sop/templates`, {}, () => [
      { id: 'sop-fire', code: 'SOP-EMG-01', title: 'Fire in Train / Coach', steps_count: 6, last_run: '2026-06-14', severity: 'CRITICAL', description: 'Emergency isolation, overhead power cut, passenger evacuation, and fire brigade call.' },
      { id: 'sop-derail', code: 'SOP-EMG-02', title: 'Derailment / Track Obstruction', steps_count: 8, last_run: '2026-04-10', severity: 'CRITICAL', description: 'ARME / BD Special dispatch, section isolation, relief crew ordering, and medical team alert.' },
      { id: 'sop-lc-fail', code: 'SOP-EMG-03', title: 'Level Crossing Gate Failure', steps_count: 5, last_run: '2026-08-12', severity: 'MAJOR', description: 'Caution order issuance to incoming trains, flagman deployment, and road traffic regulation.' },
      { id: 'sop-fog', code: 'SOP-EMG-04', title: 'Dense Fog Protocol (Visibility < 100m)', steps_count: 4, last_run: '2026-08-20', severity: 'MODERATE', description: 'Detonator placement at warning signals, speed restriction (60 km/h) imposition.' },
    ]);
  },

  async startSOPRun(templateId: string) {
    return fetchBackend(`/api/safety/sop/runs`, { method: 'POST', body: JSON.stringify({ template_id: templateId }) }, () => ({
      run_id: `RUN-${templateId}-${Date.now()}`,
      template_id: templateId,
      status: 'IN_PROGRESS',
      current_step: 1,
      started_at: new Date().toISOString(),
    }));
  },

  // 15. Safety: Level Crossing Monitor
  async getLCStatus() {
    return fetchBackend(`/api/safety/lc/status`, {}, () => [
      { id: 'LC-102', gate_no: 'Special-102', location: 'KM 1008.2 (Panki)', type: 'Interlocked / Manned', status: 'NORMAL', last_cycle: '17:35 IST', fault_duration: null },
      { id: 'LC-105', gate_no: 'A-105', location: 'KM 1019.5 (Rooma)', type: 'Interlocked / Manned', status: 'FAULT', last_cycle: '16:50 IST', fault_duration: '45m' },
      { id: 'LC-108', gate_no: 'B-108', location: 'KM 1028.0 (Bindki)', type: 'Interlocked / Manned', status: 'NORMAL', last_cycle: '17:15 IST', fault_duration: null },
    ]);
  },

  // 16. Governance: Shift Handover
  async getCurrentHandover() {
    return fetchBackend(`/api/handover/current`, {}, () => ({
      shift: '16:00 – 00:00 (Evening Shift)',
      outgoing_sm: 'A. K. Srivastava (SM-CNB)',
      station_code: 'CNB',
      open_incidents_count: 1,
      active_tsr_count: 2,
      active_blocks_count: 2,
      crew_exceptions_count: 1,
      status: 'DRAFT',
      checklist: [
        { item: 'Signal Relay Room Key Verified', checked: true },
        { item: 'Cash & UTS Booking Balance Reconciled', checked: true },
        { item: 'Caution Orders & PSR Register Signed', checked: true },
        { item: 'Platform Berth Occupancy Checked', checked: false },
      ],
    }));
  },

  async submitHandover(data: Record<string, unknown>) {
    return fetchBackend(`/api/handover/submit`, { method: 'POST', body: JSON.stringify(data) }, () => ({
      success: true,
      handover_id: `HO-${Date.now()}`,
      signature_hash: '0x99a8b11c002f',
      signed_at: new Date().toISOString(),
    }));
  },

  // 17. Governance: RBAC Admin Users
  async getUsers() {
    return fetchBackend(`/api/admin/users`, {}, () => [
      { id: 'usr-admin-01', username: 'admin', full_name: 'Chief System Administrator', email: 'admin@railtwin.internal', role_id: 'admin', station_code: 'NDLS', is_active: true, last_login: '17:40 IST' },
      { id: 'usr-sm-ndls-01', username: 'sm_ndls', full_name: 'Rajesh Kumar (Station Master NDLS)', email: 'sm@ndls.railnet.gov.in', role_id: 'station_master', station_code: 'NDLS', is_active: true, last_login: '17:35 IST' },
      { id: 'usr-sm-cnb-01', username: 'sm_cnb', full_name: 'Dinesh Gupta (Station Master CNB)', email: 'sm@cnb.railnet.gov.in', role_id: 'station_master', station_code: 'CNB', is_active: true, last_login: '17:28 IST' },
      { id: 'usr-section-ctrl-01', username: 'section_ctrl', full_name: 'Vikram Seth (Section Controller)', email: 'controller@cnb.railnet.gov.in', role_id: 'section_controller', station_code: 'CNB', is_active: true, last_login: '17:30 IST' },
      { id: 'usr-crew-ctrl-01', username: 'crew_ctrl', full_name: 'Suresh Raina (Crew Controller)', email: 'crew@delhi.railnet.gov.in', role_id: 'crew_controller', station_code: 'NDLS', is_active: true, last_login: '17:10 IST' },
      { id: 'usr-comm-01', username: 'comm_inspector', full_name: 'Ananya Roy (Commercial Inspector)', email: 'comm@lko.railnet.gov.in', role_id: 'commercial_inspector', station_code: 'LKO', is_active: true, last_login: '16:55 IST' },
      { id: 'usr-eng-01', username: 'engineer_track', full_name: 'Er. Priya Patel (Senior Section Engineer)', email: 'eng@ndls.railnet.gov.in', role_id: 'engineer', station_code: 'NDLS', is_active: true, last_login: '16:40 IST' },
    ]);
  },

  // 18. Governance: Database Backups
  async getBackups() {
    return fetchBackend(`/api/admin/backups`, {}, () => [
      { id: 'bkp-20260828-1700', filename: 'railtwin_wal_20260828_170000.db', size_bytes: 6881280, size_mb: 6.56, trigger: 'AUTO', wal_state: 'CLEAN', timestamp: '17:00:00 IST' },
      { id: 'bkp-20260828-1600', filename: 'railtwin_wal_20260828_160000.db', size_bytes: 6881280, size_mb: 6.56, trigger: 'AUTO', wal_state: 'CLEAN', timestamp: '16:00:00 IST' },
      { id: 'bkp-20260828-1500', filename: 'railtwin_wal_20260828_150000.db', size_bytes: 6619136, size_mb: 6.31, trigger: 'MANUAL', wal_state: 'CLEAN', timestamp: '15:00:00 IST' },
    ]);
  },

  async createBackup() {
    return fetchBackend(`/api/admin/backups`, { method: 'POST' }, () => ({
      success: true,
      backup_file: `railtwin_wal_${Date.now()}.db`,
      size_mb: 6.56,
      timestamp: new Date().toISOString(),
    }));
  },

  // 19. Commercial: Digital Delay Certificate
  async issueDelayCertificate(data: { train_no: string; station_code: string; issued_to_name: string; pnr_no?: string; reason?: string }) {
    return fetchBackend(`/api/commercial/delay-certificate`, { method: 'POST', body: JSON.stringify(data) }, () => {
      const certNo = `CERT-${data.station_code}-${data.train_no}-${Date.now().toString().slice(-6)}`;
      const qrToken = `RTX-VAL-${Math.floor(10000000 + Math.random() * 90000000)}`;
      return {
        certificate_no: certNo,
        qr_token: qrToken,
        train_no: data.train_no,
        station_code: data.station_code,
        passenger_name: data.issued_to_name,
        delay_minutes: 42,
        reason: data.reason || 'Operational Congestion & Preceding Freight Regulation',
        issued_at: new Date().toISOString(),
        issuer_signature: 'NORTH CENTRAL RAILWAY · PRAYAGRAJ DIVISION',
        verification_url: `${window.location.origin}/dashboard/commercial/delay-certificate?verify=${qrToken}`,
      };
    });
  },

  async verifyDelayCertificate(token: string) {
    return fetchBackend(`/api/commercial/delay-certificate/verify/${token}`, {}, () => ({
      is_valid: true,
      certificate_no: `CERT-CNB-12034-884210`,
      train_no: '12034',
      passenger_name: 'R. K. Sharma',
      delay_minutes: 42,
      issued_at: '2026-08-28 16:30:00 IST',
      reason: 'Operational Congestion & Preceding Freight Priority',
    }));
  },

  // 20. Commercial: Announcements
  async generateAnnouncement(data: { train_no: string; platform: number; delay_min?: number; type: string }) {
    return fetchBackend(`/api/commercial/announcements/generate`, { method: 'POST', body: JSON.stringify(data) }, () => {
      const englishText = data.delay_min
        ? `Attention please! Train number ${data.train_no}, arriving at Kanpur Central, is running late by ${data.delay_min} minutes and will now arrive on Platform Number ${data.platform}. Inconvenience caused is deeply regretted.`
        : `Attention please! Train number ${data.train_no} is arriving shortly on Platform Number ${data.platform}. Passengers are requested to be alert.`;

      const hindiText = data.delay_min
        ? `कृपया ध्यान दीजिए! गाड़ी संख्या ${data.train_no}, कानपुर सेंट्रल पर ${data.delay_min} मिनट की देरी से चल रही है, और अब प्लेटफार्म संख्या ${data.platform} पर आएगी। यात्रियों को हुई असुविधा के लिए हमें खेद है।`
        : `कृपया ध्यान दीजिए! गाड़ी संख्या ${data.train_no}, कुछ ही समय में प्लेटफार्म संख्या ${data.platform} पर आ रही है।`;

      return {
        english_script: englishText,
        hindi_script: hindiText,
        generated_at: new Date().toISOString(),
        train_no: data.train_no,
        platform: data.platform,
      };
    });
  },

  // 21. Commercial: Stalls & Lost Found
  async getStalls() {
    return fetchBackend(`/api/commercial/stalls`, {}, () => [
      { id: 'STL-PF1-01', name: 'A. H. Wheeler Bookstall', platform: 'PF 1', category: 'Books & Stationery', lease_holder: 'A. H. Wheeler & Co.', expiry_date: '2026-09-04', days_left: 7, status: 'EXPIRING_SOON' },
      { id: 'STL-PF2-04', name: 'IRCTC Food Plaza (Comsource)', platform: 'PF 2', category: 'Catering & Beverages', lease_holder: 'IRCTC Caterers Ltd.', expiry_date: '2026-09-22', days_left: 25, status: 'ACTIVE' },
      { id: 'STL-PF3-02', name: 'Amul Milk & Ice Cream Parlor', platform: 'PF 3', category: 'Dairy & Snacks', lease_holder: 'GCMMF Amul Retail', expiry_date: '2027-03-31', days_left: 215, status: 'ACTIVE' },
    ]);
  },

  async getLostFound() {
    return fetchBackend(`/api/commercial/lost-found`, {}, () => [
      { id: 'LF-2026-042', item_name: 'Black Leather Laptop Bag (Dell)', found_location: 'PF 2 Waiting Hall', found_date: '2026-08-28', status: 'STORED', claimant: null },
      { id: 'LF-2026-041', item_name: 'Titan Quartz Wristwatch (Gold dial)', found_location: 'Coach B4 / Train 12301', found_date: '2026-08-27', status: 'RETURNED', claimant: 'M. P. Sinha (PNR 24190812)' },
      { id: 'LF-2026-039', item_name: 'Blue Travel Trolley Bag', found_location: 'Concourse Area', found_date: '2026-08-20', status: 'DISPOSED', claimant: null },
    ]);
  },

  // 22. Infrastructure: Assets & MTBF
  async getAssets() {
    return fetchBackend(`/api/infra/assets`, {}, () => [
      { id: 'AST-PNT-14B', type: 'Point Machine (IRS Type)', location: 'CNB West Yard (Cross 14B)', station: 'CNB', install_date: '2022-04-10', condition: 'GOOD', mtbf_hours: 4200, status: 'OPERATIONAL' },
      { id: 'AST-SIG-4A', type: 'Color Light Signal 4-Aspect', location: 'CNB Home Signal Up Main', station: 'CNB', install_date: '2021-08-15', condition: 'EXCELLENT', mtbf_hours: 8900, status: 'OPERATIONAL' },
      { id: 'AST-TC-44', type: 'Audio Frequency Track Circuit', location: 'Panki West Approach Block', station: 'CNB', install_date: '2023-01-20', condition: 'FAIR', mtbf_hours: 1450, status: 'UNDER_WATCH' },
      { id: 'AST-OHE-942', type: '25kV Traction Catenary Mast', location: 'KM 942.0 ETW Section', station: 'ETW', install_date: '2019-11-05', condition: 'GOOD', mtbf_hours: 12000, status: 'OPERATIONAL' },
    ]);
  },

  // 23. Infrastructure: Work Orders Kanban
  async getWorkOrders() {
    return fetchBackend(`/api/infra/work-orders`, {}, () => [
      { id: 'WO-2026-104', title: 'Track Circuit 44 Sensitivity Calibration', linked_asset: 'AST-TC-44', column: 'IN_PROGRESS', priority: 'critical', due_date: '2026-08-28', assignee: 'PP (Er. Priya Patel)', permit_no: 'PRM-0828-44' },
      { id: 'WO-2026-102', title: 'Point Machine 14B Routine Lubrication', linked_asset: 'AST-PNT-14B', column: 'ASSIGNED', priority: 'medium', due_date: '2026-08-29', assignee: 'SG (Gang 4)', permit_no: null },
      { id: 'WO-2026-101', title: 'Platform 3 Water Hydrant Valve Overhaul', linked_asset: 'PF3 Hydrant', column: 'OPEN', priority: 'low', due_date: '2026-08-30', assignee: 'Unassigned', permit_no: null },
      { id: 'WO-2026-098', title: 'Ganga Bridge Girder Bearing Check', linked_asset: 'Bridge #12', column: 'VERIFIED', priority: 'high', due_date: '2026-08-28', assignee: 'SM (Senior Mason)', permit_no: 'PRM-0828-12' },
    ]);
  },

  async updateWorkOrderStatus(id: string, column: string) {
    return fetchBackend(`/api/infra/work-orders/${id}/status`, { method: 'PUT', body: JSON.stringify({ column }) }, () => ({
      success: true,
      id,
      column,
    }));
  },

  // 24. Infrastructure: Cleaning Logs
  async getCleaningLogs() {
    return fetchBackend(`/api/infra/cleaning-logs`, {}, () => [
      { id: 'CLN-12034', train_no: '12034', rake_id: 'RAKE-DLI-SHT-04', arrival_time: '17:42', dep_time: '18:10', status: 'IN_PROGRESS', turnaround_mins_left: 18, watering: 'COMPLETED', disinfection: 'IN_PROGRESS', supervisor: 'S. K. Yadav' },
      { id: 'CLN-12301', train_no: '12301', rake_id: 'RAKE-HWH-LHB-01', arrival_time: '17:48', dep_time: '17:55', status: 'DONE', turnaround_mins_left: 7, watering: 'COMPLETED', disinfection: 'COMPLETED', supervisor: 'R. N. Mishra' },
      { id: 'CLN-12801', train_no: '12801', rake_id: 'RAKE-PURI-SF-11', arrival_time: '19:28', dep_time: '19:38', status: 'PENDING', turnaround_mins_left: 108, watering: 'PENDING', disinfection: 'PENDING', supervisor: 'Unassigned' },
    ]);
  },

  // 25. Coordination: Corridor Handoff Matrix
  async getCorridorHandoffs() {
    return fetchBackend(`/api/section/handoffs`, {}, () => [
      { id: 'HDF-12301', train_no: '12301', boundary: 'PRYJ → CNB', sched_handoff: '17:15', pred_handoff: '17:28', state: 'ACCEPTED', delta: '+13M', speed_kmph: 112 },
      { id: 'HDF-12034', train_no: '12034', boundary: 'ETW → CNB', sched_handoff: '17:10', pred_handoff: '17:35', state: 'FLAGGED', delta: '+25M', speed_kmph: 98 },
      { id: 'HDF-22436', train_no: '22436', boundary: 'TDL → CNB', sched_handoff: '17:45', pred_handoff: '17:47', state: 'ACCEPTED', delta: '+2M', speed_kmph: 130 },
      { id: 'HDF-BOXN-7041', train_no: 'BOXN-7041', boundary: 'PRYJ → CNB', sched_handoff: '16:50', pred_handoff: '17:40', state: 'PENDING', delta: '+50M', speed_kmph: 0 },
    ]);
  },

  async acknowledgeHandoff(id: string) {
    return fetchBackend(`/api/section/handoffs/${id}/ack`, { method: 'POST' }, () => ({
      success: true,
      id,
      state: 'ACCEPTED',
    }));
  },

  // 26. Coordination: DFC Freight Precedence
  async getDFCPrecedence() {
    return fetchBackend(`/api/section/dfc`, {}, () => [
      { id: 'DFC-01', crossing_point: 'Rooma DFC Junction (KM 1018)', freight_train: 'BOXN-7041 (Coal)', passenger_train: '22436 Vande Bharat', proposed_action: 'LOOP_HOLD_FREIGHT', delay_impact_min: -24, status: 'ACTIVE' },
      { id: 'DFC-02', crossing_point: 'Panki DFC Siding (KM 1007)', freight_train: 'BTPN-3092 (POL)', passenger_train: '12424 Dibrugarh Raj', proposed_action: 'REGULATE_FREIGHT', delay_impact_min: -16, status: 'PENDING' },
    ]);
  },

  // Access Request Form
  async requestAccess(data: { stationCode: string; name: string; email: string; organisation: string }) {
    return {
      success: true,
      id: `REQ-${Math.floor(100000 + Math.random() * 900000)}`,
    };
  },
};
