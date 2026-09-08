import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import type {
  CauseItem,
  WhyLateData,
  PassengerSnapshot,
  LivePosition,
  NetworkState,
  CongestionRadarData,
  ComparatorData,
  ModelPerformanceData,
  LedgerScoreboard,
  LedgerVerificationResult,
  CascadeRippleData,
  TimeMachineData,
  PopularTrain,
  SearchResult,
  PassengerWaypoint,
} from './types';

export type {
  CauseItem,
  WhyLateData,
  PassengerSnapshot,
  LivePosition,
  NetworkState,
  CongestionRadarData,
  ComparatorData,
  ModelPerformanceData,
  LedgerScoreboard,
  LedgerVerificationResult,
  CascadeRippleData,
  TimeMachineData,
  PopularTrain,
  SearchResult,
  PassengerWaypoint,
};

// -----------------------------------------------------------------------
// CONNECTION STORE (LIVE / STALE / OFFLINE)
// -----------------------------------------------------------------------
export type ConnectionStatus = 'LIVE' | 'STALE' | 'OFFLINE';

export interface ConnectionInfo {
  status: ConnectionStatus;
  lastSuccess: number | null;
  errorMessage: string | null;
  since: number;
}

type ConnectionListener = (info: ConnectionInfo) => void;
const listeners = new Set<ConnectionListener>();

let currentConnection: ConnectionInfo = {
  status: 'LIVE',
  lastSuccess: Date.now(),
  errorMessage: null,
  since: Date.now(),
};

function updateConnection(next: Partial<ConnectionInfo>): void {
  currentConnection = { ...currentConnection, ...next };
  listeners.forEach((fn) => fn(currentConnection));
}

const ConnectionContext = createContext<ConnectionInfo>(currentConnection);

export function ConnectionProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<ConnectionInfo>(currentConnection);

  useEffect(() => {
    const listener: ConnectionListener = (info: ConnectionInfo) => setState(info);
    listeners.add(listener);
    const interval = setInterval(() => {
      if (currentConnection.status === 'LIVE' && currentConnection.lastSuccess) {
        const age = Date.now() - currentConnection.lastSuccess;
        if (age > 15000) {
          updateConnection({ status: 'STALE' });
        }
      }
    }, 3000);

    return () => {
      listeners.delete(listener);
      clearInterval(interval);
    };
  }, []);

  return React.createElement(ConnectionContext.Provider, { value: state }, children);
}

export function useConnectionState(): ConnectionInfo {
  return useContext(ConnectionContext);
}

// -----------------------------------------------------------------------
// TODO (SEC-004): Web app should detect user.must_change_password from /api/auth/login or /api/auth/me
// and redirect/prompt to the password change screen before allowing further dashboard actions.
// -----------------------------------------------------------------------
// CORE HONEST FETCH CLIENT - NO MOCKS, NO FALLBACKS
// -----------------------------------------------------------------------
async function fetchJson<T>(path: string, options?: RequestInit): Promise<T> {
  try {
    const res = await fetch(path, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options?.headers,
      },
    });

    if (!res.ok) {
      const message = 'HTTP error ' + res.status + ': ' + res.statusText;
      updateConnection({
        status: 'OFFLINE',
        errorMessage: message,
        since: Date.now(),
      });
      throw new Error(message);
    }

    const data = (await res.json()) as T;
    updateConnection({
      status: 'LIVE',
      lastSuccess: Date.now(),
      errorMessage: null,
    });
    return data;
  } catch (err) {
    const msg = err instanceof Error ? err.message : 'Network fetch failed';
    updateConnection({
      status: 'OFFLINE',
      errorMessage: msg,
      since: Date.now(),
    });
    throw err;
  }
}

// -----------------------------------------------------------------------
// NORMALIZATION HELPERS
// -----------------------------------------------------------------------
export function normalizeWhyLate(raw: {
  narrative?: string;
  causes?: Array<{ cause_code?: string; event_type?: string; attributed_min?: number; minutes?: number; percentage?: number; plain_text?: string; evidence_ref?: string; category?: string }>;
  cause_breakdown?: Array<{ cause_code?: string; event_type?: string; attributed_min?: number; minutes?: number; percentage?: number; plain_text?: string; evidence_ref?: string; category?: string }>;
  total_delay_minutes?: number;
  total_delay_min?: number;
  is_exact_accounting?: boolean;
  integrity_status?: string;
  events_count?: number;
}): WhyLateData {
  const rawList = raw.causes && raw.causes.length > 0 ? raw.causes : raw.cause_breakdown ?? [];
  const totalMin = raw.total_delay_minutes ?? raw.total_delay_min ?? 0;

  const causes: CauseItem[] = rawList.map((c) => {
    const minutes = c.attributed_min ?? c.minutes ?? 0;
    const code = c.cause_code ?? c.event_type ?? c.category ?? 'OTHER';
    const sharePct = typeof c.percentage === 'number' ? c.percentage : (totalMin > 0 ? Math.round((Math.abs(minutes) / totalMin) * 100) : 0);
    return {
      code,
      label: c.plain_text ?? code.replace(/_/g, ' '),
      minutes,
      sharePct,
      evidence: c.evidence_ref,
      category: c.category,
    };
  });

  const sumMin = causes.reduce((acc, item) => acc + item.minutes, 0);
  const additiveOk = raw.is_exact_accounting ?? (Math.abs(sumMin - totalMin) < 0.5);

  return {
    narrative: raw.narrative ?? ('Running ' + Math.round(totalMin) + ' min late across active corridor sections.'),
    causes,
    totalMin,
    additiveOk,
    integrityStatus: raw.integrity_status,
    eventsCount: raw.events_count,
  };
}

// -----------------------------------------------------------------------
// ENDPOINT LIBRARY (All relative paths, proxied)
// -----------------------------------------------------------------------
export async function getSnapshot(trainNo: string, stopCode?: string): Promise<PassengerSnapshot> {
  const params = new URLSearchParams({ train: trainNo.trim() });
  if (stopCode) params.set('stop', stopCode.trim());
  return fetchJson<PassengerSnapshot>('/v1/passenger/snapshot?' + params.toString());
}

export async function getPopularTrains(): Promise<PopularTrain[]> {
  return fetchJson<PopularTrain[]>('/v1/passenger/popular');
}

export async function searchTrains(q: string): Promise<SearchResult[]> {
  const clean = q.trim().toLowerCase();
  if (!clean) return [];
  try {
    return await fetchJson<SearchResult[]>('/v1/passenger/search?q=' + encodeURIComponent(clean));
  } catch {
    const pop = await getPopularTrains();
    return pop
      .filter((t) => t.train_no.includes(clean) || t.name.toLowerCase().includes(clean))
      .map((t) => ({
        train_no: t.train_no,
        name: t.name,
        name_hi: t.name_hi,
        type: t.type,
        route_short: t.route_short,
        last_delay: t.delay_min,
      }));
  }
}

export async function getWhyLate(trainNo: string): Promise<WhyLateData> {
  const raw = await fetchJson<Record<string, unknown>>('/v1/trains/' + encodeURIComponent(trainNo.trim()) + '/why-late');
  return normalizeWhyLate(raw as Parameters<typeof normalizeWhyLate>[0]);
}

export async function getLivePositions(): Promise<LivePosition[]> {
  const res = await fetchJson<{ positions: LivePosition[] } | LivePosition[]>('/v1/live/positions');
  if (Array.isArray(res)) return res;
  return res.positions ?? [];
}
export async function getNetworkState(): Promise<NetworkState> {
  return fetchJson<NetworkState>('/v1/network/state');
}

export async function getCongestionRadar(): Promise<CongestionRadarData> {
  return fetchJson<CongestionRadarData>('/v1/corridor/congestion-radar');
}

export async function getComparator(trainNo: string): Promise<ComparatorData> {
  return fetchJson<ComparatorData>('/v1/demo/comparator?train_no=' + encodeURIComponent(trainNo.trim()));
}

export async function injectShock(payload: {
  event_type: string;
  severity_min: number;
  station?: string;
  description?: string;
}): Promise<{ status: string; message: string }> {
  return fetchJson<{ status: string; message: string }>('/v1/demo/inject-event', {
    method: 'POST',
    body: JSON.stringify({
      event_type: payload.event_type,
      severity_min: payload.severity_min,
      station: payload.station ?? 'CNB',
      description: payload.description,
    }),
  });
}

export async function resetShocks(): Promise<{ status: string; message: string }> {
  return fetchJson<{ status: string; message: string }>('/v1/demo/reset-events', {
    method: 'POST',
  });
}

export async function getTimeMachine(trainNo: string, dest?: string): Promise<TimeMachineData> {
  return fetchJson<TimeMachineData>('/v1/demo/time-machine?train_no=' + encodeURIComponent(trainNo.trim()) + '&dest=' + encodeURIComponent(dest ?? 'CNB'));
}

export async function getModelPerformance(): Promise<ModelPerformanceData> {
  return fetchJson<ModelPerformanceData>('/v1/model/performance');
}

export async function getLedgerScoreboard(): Promise<LedgerScoreboard> {
  return fetchJson<LedgerScoreboard>('/v1/ledger/scoreboard');
}

export async function verifyLedger(): Promise<LedgerVerificationResult> {
  return fetchJson<LedgerVerificationResult>('/v1/ledger/verify');
}

export async function getCascadeRipple(stationCode = 'CNB'): Promise<CascadeRippleData> {
  return fetchJson<CascadeRippleData>('/v1/cascade/ripple?station_code=' + encodeURIComponent(stationCode));
}

export function getPassengerStreamUrl(trainNo: string): string {
  return `/v1/passenger/stream?train=${encodeURIComponent(trainNo)}`;
}

export const api = {
  getPassengerStreamUrl: (trainNo: string) => getPassengerStreamUrl(trainNo),
  passenger: {
    snapshot: (trainNo: string, stopCode?: string) => getSnapshot(trainNo, stopCode),
    popular: () => getPopularTrains(),
    search: (q: string) => searchTrains(q),
    streamUrl: (trainNo: string) => getPassengerStreamUrl(trainNo),
  },
  trains: {
    whyLate: (trainNo: string) => getWhyLate(trainNo),
  },
  live: {
    positions: () => getLivePositions(),
  },
  demo: {
    comparator: (trainNo: string) => getComparator(trainNo),
    injectEvent: (payload: { event_type: string; severity_min: number; station?: string; description?: string }) => injectShock(payload),
    resetEvents: () => resetShocks(),
    timeMachine: (trainNo: string, dest?: string) => getTimeMachine(trainNo, dest),
  },
  model: {
    performance: () => getModelPerformance(),
  },
  ledger: {
    scoreboard: () => getLedgerScoreboard(),
    verify: () => verifyLedger(),
  },
  cascade: {
    ripple: (station?: string) => getCascadeRipple(station),
  },
  corridor: {
    congestionRadar: () => getCongestionRadar(),
    networkState: () => getNetworkState(),
  },
};
