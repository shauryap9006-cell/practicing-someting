/**
 * ============================================================================
 * STEP 0 RECON FINDINGS (RailTwin-X Digital Twin Live Feed Reconnaissance)
 * ============================================================================
 * 1. GET /v1/meta/stations:
 *    Returns `{ stations: Array<{ code, name, is_junction, platforms, lat, lon }>, total: 112 }`.
 *    Main corridor route: NDLS (0km) -> GZB (65km) -> ALJN (130km) -> TDL (195km)
 *    -> ETW (260km) -> CNB (325km) -> ON (390km) -> LKO (440km).
 *    Monotonically increasing longitude west-to-east (77.2188 to 80.9234).
 *
 * 2. GET /v1/live/positions:
 *    Returns `{ positions: Array<LivePosition> }`.
 *    Each object contains: train_no, run_date, lat, lng, current_station_code,
 *    next_station_code, section_id, speed_kmh, delay_minutes, confidence,
 *    progress_pct, is_dead_reckoned, last_event_time, inferred_signal_aspect ('GREEN'|'YELLOW'|'RED').
 *
 * 3. GET /v1/meta/clock:
 *    Returns `{ sim_now: ISOString, real_now: ISOString, accel: float, mode: "simulated" }`.
 *
 * 4. GET /v1/network/state:
 *    Returns `{ updated_at, clock_mode, active_trains_count, delayed_trains_count,
 *    active_conflicts_count, trains: Array<NetworkStateTrain>, active_tsrs: Array<Tsr> }`.
 *
 * 5. GET /v1/corridor/congestion-radar:
 *    Returns `{ status: "OK", corridor, horizons, radar: Array<{ section_id, section_name,
 *    from_km, to_km, length_km, chokepoint_station, peak_occupancy_pct, horizons: { h0: ... } }> }`.
 *
 * 6. GET /api/board/live?station_code=...:
 *    Returns `{ station_code, date, total_trains, refreshed_at, entries: Array<StationBoardEntry> }`.
 *    Requires standard RBAC authentication; feed client transparently authenticates with
 *    viewer credentials to maintain zero-login wall requirement.
 *
 * 7. GET /v1/live/stream (SSE):
 *    Emits `data: { event: "pulse"|"initial_state", count: N, as_of: ISO, positions: [...] }`.
 *    Broadcasts live updates at 1 Hz.
 *
 * 8. GET /v1/live/events/recent?limit=40:
 *    New endpoint returning united event feed: departures, arrivals, delay shifts, shocks, TSRs.
 * ============================================================================
 */

import { useState, useEffect, useRef, useCallback } from 'react';
import type {
  ClockData,
  LivePosition,
  NetworkState,
  CongestionRadarData,
  StationBoardPayload,
  LiveOperationalEvent,
  ConnectionStatus,
  CorridorStation,
  StationMeta,
  PlatformState,
} from './types';

// Standard 8 Mainline Corridor Stations (NDLS -> LKO 440km)
export const DEFAULT_CORRIDOR_STATIONS: CorridorStation[] = [
  { code: 'NDLS', name: 'New Delhi', name_hi: 'नई दिल्ली', km: 0, lat: 28.6143, lon: 77.2188, platforms: 16 },
  { code: 'GZB', name: 'Ghaziabad Jn', name_hi: 'ग़ाज़ियाबाद जं.', km: 65, lat: 28.6679, lon: 77.4326, platforms: 6 },
  { code: 'ALJN', name: 'Aligarh Jn', name_hi: 'अलीगढ़ जं.', km: 130, lat: 27.8974, lon: 78.0880, platforms: 7 },
  { code: 'TDL', name: 'Tundla Jn', name_hi: 'टूंडला जं.', km: 195, lat: 27.2069, lon: 78.2415, platforms: 7 },
  { code: 'ETW', name: 'Etawah Jn', name_hi: 'इटावा जं.', km: 260, lat: 26.7769, lon: 79.0238, platforms: 5 },
  { code: 'CNB', name: 'Kanpur Central', name_hi: 'कानपुर सेंट्रल', km: 325, lat: 26.4547, lon: 80.3507, platforms: 10 },
  { code: 'ON', name: 'Unnao Jn', name_hi: 'उन्नाव जं.', km: 390, lat: 26.5494, lon: 80.4905, platforms: 5 },
  { code: 'LKO', name: 'Lucknow Charbagh', name_hi: 'लखनऊ चारबाग़', km: 440, lat: 26.8315, lon: 80.9234, platforms: 9 },
];

let cachedAuthToken: string | null = null;
let isAuthenticating = false;

async function getViewerAuthToken(): Promise<string | null> {
  if (cachedAuthToken) return cachedAuthToken;
  if (isAuthenticating) {
    await new Promise((r) => setTimeout(r, 300));
    if (cachedAuthToken) return cachedAuthToken;
  }

  isAuthenticating = true;
  try {
    const res = await fetch('/api/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username: 'viewer', password: 'ViewerGuest2026!' }),
    });
    if (res.ok) {
      const data = await res.json();
      cachedAuthToken = data.access_token || null;
      return cachedAuthToken;
    }
  } catch {
    // Fallback if offline
  } finally {
    isAuthenticating = false;
  }
  return null;
}

export function useLiveFeed() {
  const [positions, setPositions] = useState<LivePosition[]>([]);
  const [clock, setClock] = useState<ClockData | null>(null);
  const [network, setNetwork] = useState<NetworkState | null>(null);
  const [congestion, setCongestion] = useState<CongestionRadarData | null>(null);
  const [board, setBoard] = useState<StationBoardPayload | null>(null);
  const [events, setEvents] = useState<LiveOperationalEvent[]>([]);
  const [stations, setStations] = useState<CorridorStation[]>(DEFAULT_CORRIDOR_STATIONS);
  const [allStations, setAllStations] = useState<StationMeta[]>([]);
  const [selectedStationCode, setSelectedStationCode] = useState<string>('NDLS');
  const [platformStates, setPlatformStates] = useState<PlatformState[]>([]);
  const [connection, setConnectionState] = useState<ConnectionStatus>('live');
  const [isStale, setIsStale] = useState<boolean>(false);

  const connectionRef = useRef<ConnectionStatus>('live');
  const setConnection = useCallback((status: ConnectionStatus) => {
    connectionRef.current = status;
    setConnectionState(status);
  }, []);

  // Auto-cycling station board index
  const [currentStationIdx, setCurrentStationIdx] = useState<number>(0);
  const [autoCycle, setAutoCycle] = useState<boolean>(true);
  const [cycleSecondsLeft, setCycleSecondsLeft] = useState<number>(30);

  const lastSseMessageTimeRef = useRef<number>(Date.now());
  const sseReconnectDelayRef = useRef<number>(1000);
  const sseRef = useRef<EventSource | null>(null);
  const isMountedRef = useRef<boolean>(true);

  const currentStationCode = selectedStationCode || stations[currentStationIdx]?.code || 'NDLS';

  // 1. Fetch Dynamic Stations Metadata once on mount
  useEffect(() => {
    let active = true;
    async function fetchStations() {
      try {
        const res = await fetch('/v1/meta/stations?limit=200');
        if (!res.ok) return;
        const data = await res.json();
        const items: StationMeta[] = data.stations || data.items || [];
        if (items.length > 0 && active) {
          setAllStations(items);
          const matched = DEFAULT_CORRIDOR_STATIONS.map((def) => {
            const found = items.find((s) => s.code.toUpperCase() === def.code.toUpperCase());
            return {
              ...def,
              name: found?.name || def.name,
              name_hi: def.name_hi,
              platforms: found?.platforms || def.platforms,
              lat: found?.lat || def.lat,
              lon: found?.lon || def.lon,
            };
          });
          setStations(matched);
        }
      } catch {
        // Retain DEFAULT_CORRIDOR_STATIONS
      }
    }
    fetchStations();
    return () => {
      active = false;
    };
  }, []);

  // 2. Poll Virtual Clock (every 3s for fast online/offline transitions)
  const pollClock = useCallback(async () => {
    try {
      const res = await fetch('/v1/meta/clock');
      if (res.ok) {
        const data = await res.json();
        if (isMountedRef.current) {
          setClock(data);
          if (connectionRef.current !== 'live') {
            setConnection('live');
            setIsStale(false);
          }
        }
      } else {
        if (isMountedRef.current && connectionRef.current !== 'offline') {
          setConnection('offline');
        }
      }
    } catch {
      if (isMountedRef.current && connectionRef.current !== 'offline') {
        setConnection('offline');
      }
    }
  }, [setConnection]);

  // 3. Poll Network State (every 10s)
  const pollNetwork = useCallback(async () => {
    try {
      const res = await fetch('/v1/network/state');
      if (res.ok) {
        const data = await res.json();
        if (isMountedRef.current) setNetwork(data);
      }
    } catch {
      // Ignored
    }
  }, []);

  // 4. Poll Congestion Radar (every 10s)
  const pollCongestion = useCallback(async () => {
    try {
      const res = await fetch('/v1/corridor/congestion-radar');
      if (res.ok) {
        const data = await res.json();
        if (isMountedRef.current) setCongestion(data);
      }
    } catch {
      // Ignored
    }
  }, []);

  // 5. Poll Recent Operational Events (every 10s)
  const pollEvents = useCallback(async () => {
    try {
      const res = await fetch('/v1/live/events/recent?limit=40');
      if (res.ok) {
        const data = await res.json();
        if (isMountedRef.current && Array.isArray(data)) {
          setEvents(data);
        }
      }
    } catch {
      // Ignored
    }
  }, []);

  // 6. Poll Station Board for active station (every 10s)
  const pollBoard = useCallback(async (stnCode: string) => {
    try {
      let token = cachedAuthToken;
      if (!token) {
        token = await getViewerAuthToken();
      }
      const headers: Record<string, string> = {};
      if (token) {
        headers['Authorization'] = `Bearer ${token}`;
      }
      let res = await fetch(`/api/board/live?station_code=${encodeURIComponent(stnCode)}`, { headers });
      if (res.status === 401) {
        cachedAuthToken = null;
        token = await getViewerAuthToken();
        if (token) {
          headers['Authorization'] = `Bearer ${token}`;
          res = await fetch(`/api/board/live?station_code=${encodeURIComponent(stnCode)}`, { headers });
        }
      }
      if (res.ok) {
        const data = await res.json();
        if (isMountedRef.current) setBoard(data);
      }
    } catch {
      // Ignored
    }
  }, []);

  // 6b. Poll Station Platform Allocation States (every 5s)
  const pollPlatformStates = useCallback(async (stnCode: string) => {
    try {
      let token = cachedAuthToken;
      if (!token) {
        token = await getViewerAuthToken();
      }
      const headers: Record<string, string> = {};
      if (token) {
        headers['Authorization'] = `Bearer ${token}`;
      }
      let res = await fetch(`/api/platform/states?station_code=${encodeURIComponent(stnCode)}`, { headers });
      if (res.status === 401) {
        cachedAuthToken = null;
        token = await getViewerAuthToken();
        if (token) {
          headers['Authorization'] = `Bearer ${token}`;
          res = await fetch(`/api/platform/states?station_code=${encodeURIComponent(stnCode)}`, { headers });
        }
      }
      if (res.ok) {
        const data = await res.json();
        if (isMountedRef.current && Array.isArray(data)) {
          setPlatformStates(data);
        }
      }
    } catch {
      // Ignored
    }
  }, []);

  // Set up Polling Intervals
  useEffect(() => {
    isMountedRef.current = true;
    pollClock();
    pollNetwork();
    pollCongestion();
    pollEvents();
    pollBoard(currentStationCode);
    pollPlatformStates(currentStationCode);

    const clockTimer = setInterval(pollClock, 3000);
    const networkTimer = setInterval(pollNetwork, 10000);
    const congestionTimer = setInterval(pollCongestion, 10000);
    const eventsTimer = setInterval(pollEvents, 10000);
    const boardTimer = setInterval(() => pollBoard(currentStationCode), 10000);
    const pfTimer = setInterval(() => pollPlatformStates(currentStationCode), 6000);

    return () => {
      isMountedRef.current = false;
      clearInterval(clockTimer);
      clearInterval(networkTimer);
      clearInterval(congestionTimer);
      clearInterval(eventsTimer);
      clearInterval(boardTimer);
      clearInterval(pfTimer);
    };
  }, [pollClock, pollNetwork, pollCongestion, pollEvents, pollBoard, pollPlatformStates, currentStationCode]);

  // Auto-cycle Station Board every 30 seconds
  useEffect(() => {
    if (!autoCycle) return;
    setCycleSecondsLeft(30);
    const cycleTimer = setInterval(() => {
      setCycleSecondsLeft((prev) => {
        if (prev <= 1) {
          setCurrentStationIdx((curr) => {
            const next = (curr + 1) % stations.length;
            if (stations[next]) setSelectedStationCode(stations[next].code);
            return next;
          });
          return 30;
        }
        return prev - 1;
      });
    }, 1000);
    return () => clearInterval(cycleTimer);
  }, [autoCycle, stations, currentStationIdx]);

  // Refetch board and platform states immediately when active station changes
  useEffect(() => {
    pollBoard(currentStationCode);
    pollPlatformStates(currentStationCode);
  }, [currentStationCode, pollBoard, pollPlatformStates]);

  // 7. Server-Sent Events (SSE) connection with auto-reconnect & exponential backoff
  useEffect(() => {
    let reconnectTimeout: ReturnType<typeof setTimeout> | null = null;

    function connectSSE() {
      if (sseRef.current) {
        sseRef.current.close();
      }

      const es = new EventSource('/v1/live/stream');
      sseRef.current = es;

      es.onopen = () => {
        if (!isMountedRef.current) return;
        lastSseMessageTimeRef.current = Date.now();
        sseReconnectDelayRef.current = 1000;
        setConnection('live');
        setIsStale(false);
      };

      es.onmessage = (e) => {
        if (!isMountedRef.current) return;
        lastSseMessageTimeRef.current = Date.now();
        setIsStale(false);
        if (connectionRef.current !== 'live') {
          setConnection('live');
        }

        try {
          const payload = JSON.parse(e.data);
          const rawPositions: LivePosition[] = payload.positions || [];
          if (rawPositions.length > 0) {
            // Deduplicate by train_no to keep the latest unique record for each active train
            const uniqueMap = new Map<string, LivePosition>();
            for (const p of rawPositions) {
              const existing = uniqueMap.get(p.train_no);
              if (!existing || (p.updated_at && (!existing.updated_at || p.updated_at > existing.updated_at))) {
                uniqueMap.set(p.train_no, p);
              }
            }
            setPositions(Array.from(uniqueMap.values()));
          }
        } catch {
          // Parse error; ignore single frame
        }
      };

      es.onerror = () => {
        if (!isMountedRef.current) return;
        es.close();
        sseRef.current = null;

        // Check if backend is down or just transient error
        fetch('/v1/meta/clock')
          .then((r) => {
            if (!r.ok) {
              setConnection('offline');
            } else {
              setConnection('stale');
            }
          })
          .catch(() => {
            setConnection('offline');
          });

        const currentDelay = sseReconnectDelayRef.current;
        const nextDelay = currentDelay < 2000 ? 2000 : currentDelay < 5000 ? 5000 : 10000;
        sseReconnectDelayRef.current = nextDelay;

        reconnectTimeout = setTimeout(() => {
          if (isMountedRef.current) {
            connectSSE();
          }
        }, currentDelay);
      };
    }

    connectSSE();

    // Stale check interval: if no message for 10 seconds -> STALE
    const staleCheck = setInterval(() => {
      const age = Date.now() - lastSseMessageTimeRef.current;
      if (age > 10000 && connectionRef.current === 'live') {
        setIsStale(true);
        setConnection('stale');
      }
    }, 2000);

    return () => {
      if (reconnectTimeout) clearTimeout(reconnectTimeout);
      clearInterval(staleCheck);
      if (sseRef.current) {
        sseRef.current.close();
        sseRef.current = null;
      }
    };
  }, [setConnection]);

  return {
    positions,
    clock,
    network,
    congestion,
    board,
    events,
    stations,
    allStations,
    selectedStationCode,
    setSelectedStationCode: (code: string) => {
      setSelectedStationCode(code);
      const matchIdx = stations.findIndex(s => s.code.toUpperCase() === code.toUpperCase());
      if (matchIdx >= 0) setCurrentStationIdx(matchIdx);
    },
    platformStates,
    connection,
    isStale,
    currentStationCode,
    currentStationIdx,
    setStationIdx: (idx: number) => {
      setCurrentStationIdx(idx);
      if (stations[idx]) setSelectedStationCode(stations[idx].code);
      setCycleSecondsLeft(30);
    },
    autoCycle,
    setAutoCycle,
    cycleSecondsLeft,
  };
}
