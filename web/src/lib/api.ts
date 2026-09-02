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
  DelayAutopsyItem,
} from '@/mock/types';

export interface DelayCauseItem {
  event_type: string;
  minutes: number;
  cause: string;
  station_code?: string | null;
  evidence?: Record<string, any> | null;
  evidence_pointer?: string | null;
}

export interface DelayAutopsyResponse {
  train_no: string;
  train_name: string;
  total_predicted_delay_min: number;
  is_exact_accounting: boolean;
  causes: DelayCauseItem[];
  narrative?: string;
  integrity_status?: 'VERIFIED' | 'WARNING';
  integrity_checks?: {
    additivity_pass?: boolean;
    evidence_resolvable?: boolean;
    clock_consistent?: boolean;
  };
  as_of_ts?: string;
  updated_at?: string;
  clock_mode?: string;
}

export type DataSourceState = 'LIVE' | 'STALE' | 'OFFLINE' | 'DEMO';

export interface DataSourceStatus {
  state: DataSourceState;
  lastSuccessfulFetch: number | null;
  lastAttempt: number | null;
  errorMessage?: string;
  isDemoMode: boolean;
}

const API_BASE = import.meta.env.VITE_API_URL || '';

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
      if (fallbackFn) {
        return await fallbackFn();
      }
      throw new Error(`API Error ${res.status} on ${path}: ${errText}`);
    }
  } catch (err: any) {
    updateStatus({
      state: 'OFFLINE',
      errorMessage: err?.message || 'Network request failed',
    });
    if (fallbackFn) {
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
    return fetchBackend<any>(`/v1/network/state`, {}, () => mockStore.getTrains()).then((res) => {
      const trainList = Array.isArray(res) ? res : (res?.trains || []);
      if (!trainList || trainList.length === 0) {
        return mockStore.getTrains();
      }
      return trainList.map((t: any) => {
        const delayMin = t.current_delay_min ?? t.delay_min ?? 0;
        const status: 'on_time' | 'delayed' | 'critical' =
          delayMin > 20 ? 'critical' : delayMin > 5 ? 'delayed' : 'on_time';

        const p50Minutes = 18 * 60 + delayMin;
        const formatClock = (mins: number) => {
          const h = Math.floor((mins % (24 * 60)) / 60).toString().padStart(2, '0');
          const m = (mins % 60).toString().padStart(2, '0');
          return `${h}:${m}`;
        };

        const p10 = formatClock(Math.max(0, p50Minutes - 5));
        const p50 = formatClock(p50Minutes);
        const p90 = formatClock(p50Minutes + 12);

        return {
          number: t.train_no || t.number,
          name: t.train_name || t.name || 'Express',
          type: (t.train_class || t.type || 'Superfast') as any,
          origin: t.last_passed_station || t.origin || 'NDLS',
          destination: t.destination || 'DDU',
          currentStation: t.last_passed_station || t.currentStation || 'NDLS',
          nextStation: t.next_station || t.nextStation || 'CNB',
          routePosition: t.routePosition || `${t.last_passed_station || 'NDLS'} → ${t.next_station || 'CNB'}`,
          scheduledArrival: t.scheduledArrival || '18:00',
          scheduledDeparture: t.scheduledDeparture || '18:05',
          predictedArrival: t.predictedArrival || p50,
          predictedDeparture: t.predictedDeparture || formatClock(p50Minutes + 5),
          etaBand: t.etaBand || { p10, p50, p90, spreadMinutes: 17 },
          delayMinutes: delayMin,
          platform: t.platform || (parseInt(t.train_no || '1', 10) % 8) + 1 || 1,
          assignedPlatform: t.assignedPlatform || (parseInt(t.train_no || '1', 10) % 8) + 1 || 1,
          speedKmph: t.speedKmph || (t.status_color === 'red' ? 45 : t.status_color === 'amber' ? 75 : 110),
          priority: t.priority || 1,
          rakeId: t.rakeId || `RAKE-${t.train_no || t.number}`,
          status,
          regimeWeights: t.regimeWeights || {
            clearTrack: t.status_color === 'green' ? 0.85 : 0.4,
            congestion: t.status_color === 'amber' ? 0.5 : 0.1,
            winterFog: t.status_color === 'red' ? 0.5 : 0.05,
          },
          journey: t.journey || [],
          delayAutopsy: t.delayAutopsy || [],
          updatedAt: new Date().toISOString(),
        };
      });
    });
  },

  async getTrain(number: string): Promise<Train | null> {
    const fallbackTrain = mockStore.getTrain(number);

    return fetchBackend<any>(`/v1/trains/${number}/journey`, {}, () => fallbackTrain).then(async (res) => {
      if (!res || (!res.train_no && !res.number)) {
        return fallbackTrain || null;
      }

      // If it's already a full Train instance from mockStore
      if (res.etaBand && res.number) {
        return res as Train;
      }

      let autopsy: DelayAutopsyItem[] = [];
      try {
        const autoRes = await api.getTrainAutopsy(number);
        if (autoRes && Array.isArray(autoRes.causes) && autoRes.causes.length > 0) {
          const total = autoRes.total_predicted_delay_min || 1;
          autopsy = autoRes.causes.map((c: any) => ({
            cause: c.event_type || c.cause,
            minutes: c.minutes,
            category: (c.event_type === 'TSR' ? 'Speed Restriction' : c.event_type === 'CROSSING_HOLD' ? 'Precedence' : 'Signaling') as any,
            description: c.cause || `Attributed delay event: ${c.event_type} at ${c.station_code || 'Section'}`,
            percentage: Math.round((c.minutes / Math.max(1, total)) * 100),
          }));
        }
      } catch {
        // fallback to mock autopsy
      }

      const delayMin = res.current_delay_min ?? res.delayMinutes ?? 0;
      const status: 'on_time' | 'delayed' | 'critical' =
        delayMin > 20 ? 'critical' : delayMin > 5 ? 'delayed' : 'on_time';

      return {
        number: res.train_no || res.number || number,
        name: res.train_name || res.name || 'Express',
        type: (res.train_class?.toUpperCase() || res.type || 'EXPRESS') as any,
        origin: res.origin || 'NDLS',
        destination: res.destination || 'DDU',
        scheduledArrival: res.scheduledArrival || '18:00',
        predictedArrival: res.predictedArrival || '18:15',
        scheduledDeparture: res.scheduledDeparture || '18:05',
        predictedDeparture: res.predictedDeparture || '18:20',
        delayMinutes: delayMin,
        status,
        platform: res.platform || (parseInt(number, 10) % 8) + 1 || 1,
        assignedPlatform: res.assignedPlatform || (parseInt(number, 10) % 8) + 1 || 1,
        speedKmph: res.speedKmph || 85,
        currentStation: res.current_station || res.currentStation || 'En Route',
        nextStation: res.next_station || res.nextStation || 'CNB',
        routePosition: res.routePosition || `${res.current_station || 'En Route'} (In Corridor)`,
        priority: res.priority || 1,
        rakeId: res.rakeId || `RAKE-${number}`,
        etaBand: res.etaBand || { p10: '18:10', p50: '18:15', p90: '18:25', spreadMinutes: 15 },
        journey: Array.isArray(res.timeline)
          ? res.timeline.map((stop: any) => ({
              seq: stop.seq,
              stationCode: stop.station_code,
              stationName: stop.station_name,
              distanceKm: stop.distance_km,
              schedArrival: stop.sched_arr || '--:--',
              schedDeparture: stop.sched_dep || '--:--',
              predArrival: stop.predicted_arr || '--:--',
              predDeparture: stop.predicted_dep || '--:--',
              actualArrival: stop.status_color === 'green' ? stop.sched_arr : undefined,
              actualDeparture: stop.status_color === 'green' ? stop.sched_dep : undefined,
              delayMinutes: stop.delay_min || 0,
              status: stop.status_color === 'green' ? 'passed' : stop.status_color === 'amber' ? 'current' : 'upcoming',
            }))
          : res.journey || [],
        delayAutopsy: autopsy.length > 0 ? autopsy : (fallbackTrain?.delayAutopsy || []),
        updatedAt: new Date().toISOString(),
      };
    });
  },

  async getTrainAutopsy(id: string): Promise<DelayAutopsyResponse> {
    const mockTrain = mockStore.getTrain(id);
    const mockDelay = mockTrain?.delayMinutes || 18;

    const defaultCauses: DelayCauseItem[] = [
      {
        event_type: 'INHERITED',
        minutes: Math.max(5, Math.round(mockDelay * 0.45)),
        cause: 'Incoming rake turnaround deficit from previous service leg',
        station_code: 'NDLS',
      },
      {
        event_type: 'TSR',
        minutes: Math.max(3, Math.round(mockDelay * 0.35)),
        cause: '45 km/h engineering speed restriction between TDL–ETW',
        station_code: 'ETW',
      },
      {
        event_type: 'CONGESTION',
        minutes: Math.max(2, Math.round(mockDelay * 0.25)),
        cause: 'Junction headway spacing behind freight precedence',
        station_code: 'CNB',
      },
      {
        event_type: 'RECOVERY',
        minutes: -3,
        cause: 'Loco pilot recovered 3m on clear high-speed block section',
        station_code: 'PRYJ',
      },
    ];

    return fetchBackend<DelayAutopsyResponse>(
      `/v1/trains/${id}/autopsy`,
      {},
      () => ({
        train_no: id,
        train_name: mockTrain?.name || 'Express',
        total_predicted_delay_min: mockDelay,
        is_exact_accounting: true,
        causes: defaultCauses,
      })
    ).then(res => {
      if (!res || !res.causes || res.causes.length === 0) {
        return {
          train_no: id,
          train_name: mockTrain?.name || 'Express',
          total_predicted_delay_min: mockDelay,
          is_exact_accounting: true,
          causes: defaultCauses,
        };
      }
      return res;
    });
  },

  // 3. Platform Gantt
  async getPlatforms(code?: StationCode): Promise<PlatformInfo[]> {
    return fetchBackend(`/api/platform/states`, {}, () => mockStore.getPlatforms(code));
  },

  async reoptimizePlatforms(stationCode?: StationCode): Promise<{ resolvedCount: number; swapsCount: number }> {
    return fetchBackend(`/api/platform/reoptimize`, { method: 'POST', body: JSON.stringify({ station_code: stationCode || 'CNB' }) }, () =>
      mockStore.reoptimizePlatforms(stationCode)
    );
  },

  async rollbackPlatforms(stationCode?: StationCode): Promise<boolean> {
    return fetchBackend(`/api/platform/rollback`, { method: 'POST', body: JSON.stringify({ station_code: stationCode || 'CNB' }) }, () =>
      true
    );
  },

  // 4. Advisories & Triage
  async getAdvisories(): Promise<Advisory[]> {
    try {
      const [crewRes, secRes] = await Promise.allSettled([
        fetchBackend<any>(`/v1/crew/alerts`, {}, () => ({ alerts: [] })),
        fetchBackend<any[]>(`/api/section/advisories/generate`, {}, () => []),
      ]);

      const advisories: Advisory[] = [];

      // 1. Crew Duty Breach Alerts
      if (crewRes.status === 'fulfilled' && crewRes.value?.alerts && Array.isArray(crewRes.value.alerts)) {
        crewRes.value.alerts.forEach((alert: any) => {
          advisories.push({
            id: `adv-crew-${alert.crew_id}-${alert.train_no}`,
            code: 'CREW-LIMIT',
            priority: alert.breach_minutes > 60 ? 'danger' : 'warn',
            title: `Crew Duty Breach Alert — Train ${alert.train_no}`,
            trainNo: alert.train_no,
            trainName: `Crew ${alert.crew_id}`,
            stationCode: (alert.recommended_relief_station || 'CNB') as StationCode,
            rationale: alert.message || `Projected duty ${alert.projected_duty_hours}h exceeds cap (+${alert.breach_minutes}m breach).`,
            recommendedAction: `Dispatch standby crew at ${alert.recommended_relief_station || 'CNB'} before departure.`,
            simulatedImpact: {
              delaySavingsMinutes: Math.max(10, alert.breach_minutes),
              conflictResolved: true,
              cascadePreventedCount: 1,
            },
            status: 'pending',
            humanAckRequired: true,
            createdAt: new Date().toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' }),
            expiresAt: alert.projected_trip_end_time || '--:--',
          });
        });
      }

      // 2. Precedence / Overtake Advisories
      if (secRes.status === 'fulfilled' && Array.isArray(secRes.value)) {
        secRes.value.forEach((adv: any) => {
          advisories.push({
            id: `adv-prec-${adv.id || adv.train_no}`,
            code: adv.advisory_type === 'OVERTAKE' ? 'HOLD_AT_LOOP' : 'STOP_TRAIN',
            priority: (adv.priority_score || 0) >= 9 ? 'danger' : 'warn',
            title: adv.advisory_type === 'OVERTAKE'
              ? `Precedence Overtake: Train ${adv.overtaking_train_no} over ${adv.train_no}`
              : `Speed Regulation: Train ${adv.train_no}`,
            trainNo: adv.train_no,
            trainName: adv.train_name || 'Express',
            stationCode: (adv.recommended_station || 'GZB') as StationCode,
            platform: adv.recommended_loop_line ? parseInt(adv.recommended_loop_line, 10) || 1 : undefined,
            suggestedPlatform: adv.recommended_loop_line ? parseInt(adv.recommended_loop_line, 10) || 1 : undefined,
            rationale: adv.details || `Regulate Train ${adv.train_no} for corridor optimization.`,
            recommendedAction: adv.advisory_type === 'OVERTAKE'
              ? `Loop train ${adv.train_no} on ${adv.recommended_station} Loop ${adv.recommended_loop_line} to clear high-speed path.`
              : `Regulate train ${adv.train_no} speed at ${adv.recommended_station}.`,
            simulatedImpact: {
              delaySavingsMinutes: Math.round((adv.priority_score || 8) * 2.5),
              conflictResolved: true,
              cascadePreventedCount: 2,
            },
            status: adv.status?.toLowerCase() === 'executed' ? 'accepted' : 'pending',
            humanAckRequired: true,
            createdAt: adv.created_at || '12:00',
            expiresAt: '18:00',
          });
        });
      }

      return advisories;
    } catch {
      return [];
    }
  },

  async acceptAdvisory(id: string, reason?: string, actor?: string): Promise<boolean> {
    return fetchBackend(
      `/v1/advise/${id}/ack`,
      {
        method: 'POST',
        body: JSON.stringify({
          decision: 'accepted',
          comment: reason || 'Accepted per dispatcher recommendation',
          dispatcher_id: actor || 'DISP-01',
        }),
      },
      () => true
    );
  },

  async dismissAdvisory(id: string, reason?: string, actor?: string): Promise<boolean> {
    return fetchBackend(
      `/v1/advise/${id}/ack`,
      {
        method: 'POST',
        body: JSON.stringify({
          decision: 'rejected',
          comment: reason || 'Dismissed under dispatcher discretion',
          dispatcher_id: actor || 'DISP-01',
        }),
      },
      () => true
    );
  },

  // 5. Crew Duty
  async getCrew(): Promise<CrewMember[]> {
    try {
      const res = await fetchBackend<any>(`/api/workforce/crew/roster`, {}, () => mockStore.getCrew());
      if (Array.isArray(res)) return res;
      if (res && Array.isArray(res.roster)) return res.roster;
      if (res && Array.isArray(res.items)) return res.items;
      return mockStore.getCrew();
    } catch {
      return mockStore.getCrew();
    }
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

  // 11. Safety: TSR / Caution Orders
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

  // 12. Safety: Incidents Register
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

  // 13. Coordination: Corridor Handoff Matrix
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

  // 14. Coordination: DFC Freight Precedence
  async getDFCPrecedence() {
    return fetchBackend(`/api/section/dfc`, {}, () => [
      { id: 'DFC-01', crossing_point: 'Rooma DFC Junction (KM 1018)', freight_train: 'BOXN-7041 (Coal)', passenger_train: '22436 Vande Bharat', proposed_action: 'LOOP_HOLD_FREIGHT', delay_impact_min: -24, status: 'ACTIVE' },
      { id: 'DFC-02', crossing_point: 'Panki DFC Siding (KM 1007)', freight_train: 'BTPN-3092 (POL)', passenger_train: '12424 Dibrugarh Raj', proposed_action: 'REGULATE_FREIGHT', delay_impact_min: -16, status: 'PENDING' },
    ]);
  },

  // 15. Access Request Form
  async requestAccess(data: { stationCode: string; name: string; email: string; organisation: string }) {
    return {
      success: true,
      id: `REQ-${Math.floor(100000 + Math.random() * 900000)}`,
    };
  },
};
