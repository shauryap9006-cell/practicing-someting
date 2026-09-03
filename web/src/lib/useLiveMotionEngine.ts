import { useState, useEffect, useRef, useCallback, useMemo } from 'react';
import { api, PassengerSnapshot, PassengerWaypoint } from '@/lib/api';

export type LiveMotionMode = 'moving' | 'approaching' | 'halted' | 'departing';

export interface WaypointCrossingToast {
  id: string;
  waypointCode: string;
  waypointName: string;
  waypointNameHi?: string;
  timeStr: string;
  status: 'on_schedule' | 'delayed';
  delayMin: number;
}

export interface LiveMotionEngineOptions {
  trainNo?: string;
  snapshot?: PassengerSnapshot;
  selectedStopCode?: string;
  isCompleted?: boolean;
  isNotRunningToday?: boolean;
  refetchSnapshot?: () => void;
}

export interface LiveMotionEngineReturn {
  mode: LiveMotionMode;
  modeLabel: string;
  modeLabelHi: string;
  drKm: number;
  odometerKm: string;
  displaySpeed: number;
  speedHistory: number[];
  distToStopKm: number;
  etaCountdown: string;
  isApproachingStop: boolean;
  dwellSecondsRemaining: number;
  lastFixAgeSeconds: number;
  isInterpolating: boolean;
  calibrationNotice: string | null;
  activeCrossingToast: WaypointCrossingToast | null;
  dismissCrossingToast: () => void;
  // Alarm
  alarmEnabled: boolean;
  alarmThresholdMin: number;
  alarmFired: boolean;
  setAlarmThresholdMin: (mins: number) => void;
  toggleAlarm: (enable?: boolean) => Promise<boolean>;
  dismissAlarm: () => void;
}

// Synthesize pleasant railway two-tone chime via Web Audio API
function playRailwayChime() {
  try {
    const AudioCtx = window.AudioContext || (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext;
    if (!AudioCtx) return;
    const ctx = new AudioCtx();
    const now = ctx.currentTime;

    // Tone 1: 523Hz (C5)
    const osc1 = ctx.createOscillator();
    const gain1 = ctx.createGain();
    osc1.type = 'sine';
    osc1.frequency.setValueAtTime(523.25, now);
    gain1.gain.setValueAtTime(0.2, now);
    gain1.gain.exponentialRampToValueAtTime(0.001, now + 0.35);
    osc1.connect(gain1);
    gain1.connect(ctx.destination);
    osc1.start(now);
    osc1.stop(now + 0.35);

    // Tone 2: 659Hz (E5)
    const osc2 = ctx.createOscillator();
    const gain2 = ctx.createGain();
    osc2.type = 'sine';
    osc2.frequency.setValueAtTime(659.25, now + 0.2);
    gain2.gain.setValueAtTime(0.25, now + 0.2);
    gain2.gain.exponentialRampToValueAtTime(0.001, now + 0.7);
    osc2.connect(gain2);
    gain2.connect(ctx.destination);
    osc2.start(now + 0.2);
    osc2.stop(now + 0.7);
  } catch {
    // AudioContext blocked or not supported; ignore gracefully
  }
}

export function useLiveMotionEngine({
  trainNo,
  snapshot,
  selectedStopCode,
  isCompleted = false,
  isNotRunningToday = false,
  refetchSnapshot,
}: LiveMotionEngineOptions): LiveMotionEngineReturn {
  // Motion State
  const [mode, setMode] = useState<LiveMotionMode>('moving');
  const [drKm, setDrKm] = useState<number>(snapshot ? snapshot.live_status.km_covered : 187.0);
  const [displaySpeed, setDisplaySpeed] = useState<number>(snapshot ? snapshot.live_status.speed_kmh : 112.0);
  const [speedHistory, setSpeedHistory] = useState<number[]>([112, 112, 111, 112, 113, 112]);
  const [dwellSecondsRemaining, setDwellSecondsRemaining] = useState<number>(0);

  // Honesty / Telemetry tracking
  const [lastFixTimestamp, setLastFixTimestamp] = useState<number>(Date.now());
  const [lastFixAgeSeconds, setLastFixAgeSeconds] = useState<number>(0);
  const [calibrationNotice, setCalibrationNotice] = useState<string | null>(null);

  // Waypoint pass toasts
  const [activeCrossingToast, setActiveCrossingToast] = useState<WaypointCrossingToast | null>(null);
  const toastQueueRef = useRef<WaypointCrossingToast[]>([]);
  const crossedWaypointsRef = useRef<Set<string>>(new Set());

  // Alarm settings
  const [alarmEnabled, setAlarmEnabled] = useState<boolean>(() => {
    return localStorage.getItem('rtx_station_alarm_enabled') === 'true';
  });
  const [alarmThresholdMin, setAlarmThresholdMinState] = useState<number>(() => {
    const saved = localStorage.getItem('rtx_station_alarm_minutes');
    return saved ? parseInt(saved, 10) : 10;
  });
  const [alarmFired, setAlarmFired] = useState<boolean>(false);

  // References for 60fps rAF loop
  const drKmRef = useRef<number>(snapshot ? snapshot.live_status.km_covered : 187.0);
  const smoothSpeedRef = useRef<number>(snapshot ? snapshot.live_status.speed_kmh : 112.0);
  const modeRef = useRef<LiveMotionMode>('moving');
  const dwellSRef = useRef<number>(0);
  const nextHaltKmRef = useRef<number>(snapshot?.next_stop?.distance_km || 209.0);
  const nextHaltCodeRef = useRef<string>(snapshot?.next_stop?.station_code || 'TDL');
  const nextHaltNameRef = useRef<string>(snapshot?.next_stop?.station_name || 'Tundla Junction');

  // Easing reference for drift correction
  const easingRef = useRef<{
    startKm: number;
    targetKm: number;
    startTime: number;
    durationMs: number;
  } | null>(null);

  // Keep refs in sync with props
  useEffect(() => {
    if (snapshot?.next_stop) {
      nextHaltKmRef.current = snapshot.next_stop.distance_km;
      nextHaltCodeRef.current = snapshot.next_stop.station_code;
      nextHaltNameRef.current = snapshot.next_stop.station_name;
    }
  }, [snapshot?.next_stop]);

  // Handle server fix ingestion (SSE or REST snapshot)
  const handleServerFix = useCallback(
    (fix: {
      km: number;
      speed: number;
      mode?: LiveMotionMode;
      dwell_s?: number;
      delay_min?: number;
    }) => {
      setLastFixTimestamp(Date.now());
      setLastFixAgeSeconds(0);

      // EMA speed smoothing (alpha = 0.4)
      smoothSpeedRef.current = 0.4 * fix.speed + 0.6 * smoothSpeedRef.current;

      if (fix.dwell_s !== undefined) {
        dwellSRef.current = fix.dwell_s;
        setDwellSecondsRemaining(fix.dwell_s);
      }

      const drift = Math.abs(fix.km - drKmRef.current);

      if (drift < 0.5) {
        // Subtle drift < 500m: smooth 2s ease without jumping
        easingRef.current = {
          startKm: drKmRef.current,
          targetKm: fix.km,
          startTime: performance.now(),
          durationMs: 2000,
        };
      } else {
        // Significant drift >= 500m: honest snap + calibration notice
        drKmRef.current = fix.km;
        setDrKm(fix.km);
        easingRef.current = null;
        setCalibrationNotice(`Position calibrated after signal gap (Δ ${drift.toFixed(1)} km)`);
        setTimeout(() => setCalibrationNotice(null), 5000);
      }

      if (fix.mode) {
        modeRef.current = fix.mode;
        setMode(fix.mode);
      }
    },
    []
  );

  // Connect to SSE stream /v1/passenger/stream?train=...
  useEffect(() => {
    if (!trainNo || isCompleted || isNotRunningToday) return;

    let es: EventSource | null = null;
    try {
      const streamUrl = api.getPassengerStreamUrl(trainNo);
      es = new EventSource(streamUrl);

      es.onmessage = (e) => {
        try {
          const data = JSON.parse(e.data);
          handleServerFix({
            km: data.km,
            speed: data.speed,
            mode: data.mode,
            dwell_s: data.dwell_s,
            delay_min: data.delay_min,
          });
        } catch {
          // parse error; ignore
        }
      };

      es.onerror = () => {
        // EventSource will auto-reconnect
      };
    } catch {
      // EventSource failed to instantiate
    }

    return () => {
      if (es) {
        es.close();
      }
    };
  }, [trainNo, isCompleted, isNotRunningToday, handleServerFix]);

  // Synchronize when snapshot updates from React Query (only if advancing or initial)
  const initialSnapshotIngestedRef = useRef<boolean>(false);
  useEffect(() => {
    if (snapshot) {
      if (!initialSnapshotIngestedRef.current) {
        initialSnapshotIngestedRef.current = true;
        handleServerFix({
          km: snapshot.live_status.km_covered,
          speed: snapshot.live_status.speed_kmh,
          delay_min: snapshot.single_delay.delay_min,
        });
      } else if (snapshot.live_status.km_covered > drKmRef.current) {
        handleServerFix({
          km: snapshot.live_status.km_covered,
          speed: snapshot.live_status.speed_kmh,
          delay_min: snapshot.single_delay.delay_min,
        });
      }
    }
  }, [snapshot, handleServerFix]);

  // Waypoint cross-check logic
  const checkWaypointCrossings = useCallback(
    (currentKm: number) => {
      const waypoints = snapshot?.waypoints;
      if (!waypoints || waypoints.length === 0) return;

      const now = new Date();
      const timeStr = `${String(now.getHours()).padStart(2, '0')}:${String(now.getMinutes()).padStart(2, '0')}`;
      const delayMin = snapshot?.single_delay.delay_min || 0;

      let enqueued = false;
      for (const wp of waypoints) {
        if (currentKm >= wp.km && !crossedWaypointsRef.current.has(wp.code)) {
          crossedWaypointsRef.current.add(wp.code);

          // Only fire toast if train was reasonably close to passing it recently
          if (currentKm - wp.km <= 2.5) {
            const toast: WaypointCrossingToast = {
              id: `${wp.code}-${Date.now()}`,
              waypointCode: wp.code,
              waypointName: wp.name,
              waypointNameHi: wp.name_hi,
              timeStr,
              status: delayMin <= 5 ? 'on_schedule' : 'delayed',
              delayMin,
            };

            // Queue management: max 3 queued
            if (toastQueueRef.current.length < 3) {
              toastQueueRef.current.push(toast);
              enqueued = true;
            }
          }
        }
      }

      if (enqueued) {
        if (!activeCrossingToast && toastQueueRef.current.length > 0) {
          const nextToast = toastQueueRef.current.shift()!;
          setActiveCrossingToast(nextToast);
          setTimeout(() => {
            setActiveCrossingToast((cur) => (cur?.id === nextToast.id ? null : cur));
          }, 4500); // 4.5s auto-dismiss
        }
      }
    },
    [snapshot?.waypoints, snapshot?.single_delay.delay_min, activeCrossingToast]
  );

  // 60FPS requestAnimationFrame Dead Reckoning Loop
  useEffect(() => {
    if (isCompleted || isNotRunningToday) {
      return;
    }

    let rafId: number;
    let lastFrameTime = performance.now();

    const frame = (now: number) => {
      // Battery safety: pause rAF if tab hidden
      if (document.hidden) {
        lastFrameTime = now;
        rafId = requestAnimationFrame(frame);
        return;
      }

      const dtMs = Math.min(100, Math.max(1, now - lastFrameTime));
      const dt = dtMs / 1000;
      lastFrameTime = now;

      // 1. Handle easing if drift correction is in progress
      if (easingRef.current) {
        const { startKm, targetKm, startTime, durationMs } = easingRef.current;
        const progress = Math.min(1, (now - startTime) / durationMs);
        const easeFactor = 1 - Math.pow(1 - progress, 3);
        drKmRef.current = startKm + (targetKm - startKm) * easeFactor;
        if (progress >= 1) {
          easingRef.current = null;
        }
      } else {
        // 2. Dead-reckon based on state machine mode
        const currentMode = modeRef.current;
        const distToHalt = nextHaltKmRef.current - drKmRef.current;

        if (currentMode === 'moving' || currentMode === 'approaching') {
          const ramp = Math.min(1, Math.max(0.1, distToHalt / 2.5));
          const effectiveSpeed =
            distToHalt <= 2.5
              ? smoothSpeedRef.current * ramp
              : smoothSpeedRef.current;

          if (distToHalt <= 2.5 && currentMode === 'moving') {
            modeRef.current = 'approaching';
            setMode('approaching');
          }

          const kmAdvance = (effectiveSpeed * dt) / 3600;
          drKmRef.current = Math.min(drKmRef.current + kmAdvance, nextHaltKmRef.current);

          if (distToHalt <= 0.12) {
            modeRef.current = 'halted';
            setMode('halted');
            dwellSRef.current = 120;
            setDwellSecondsRemaining(120);
          }
        } else if (currentMode === 'halted') {
          dwellSRef.current = Math.max(0, dwellSRef.current - dt);
          setDwellSecondsRemaining(Math.ceil(dwellSRef.current));

          if (dwellSRef.current <= 0) {
            modeRef.current = 'departing';
            setMode('departing');
          }
        } else if (currentMode === 'departing') {
          const effectiveSpeed = Math.min(smoothSpeedRef.current, 45.0);
          drKmRef.current += (effectiveSpeed * dt) / 3600;

          if (drKmRef.current - nextHaltKmRef.current > 1.5) {
            modeRef.current = 'moving';
            setMode('moving');
          }
        }
      }

      // Subtle micro-jitter on speed readout (±0.6 km/h)
      const jitter = (Math.sin(now / 400) + Math.cos(now / 700)) * 0.4;
      const finalSpeed =
        modeRef.current === 'halted'
          ? 0
          : Math.max(0, Math.round((smoothSpeedRef.current + jitter) * 10) / 10);

      setDrKm(drKmRef.current);
      setDisplaySpeed(finalSpeed);

      checkWaypointCrossings(drKmRef.current);

      rafId = requestAnimationFrame(frame);
    };

    rafId = requestAnimationFrame(frame);
    return () => cancelAnimationFrame(rafId);
  }, [isCompleted, isNotRunningToday, checkWaypointCrossings]);

  // 1-Second Tick Layer
  useEffect(() => {
    const timer = setInterval(() => {
      const age = Math.floor((Date.now() - lastFixTimestamp) / 1000);
      setLastFixAgeSeconds(age);

      setSpeedHistory((prev) => {
        const next = [...prev.slice(-29), displaySpeed];
        return next;
      });
    }, 1000);

    return () => clearInterval(timer);
  }, [lastFixTimestamp, displaySpeed]);

  // Tab visibility change handler
  useEffect(() => {
    const handleVisibilityChange = () => {
      if (!document.hidden && refetchSnapshot) {
        refetchSnapshot();
      }
    };
    document.addEventListener('visibilitychange', handleVisibilityChange);
    return () => document.removeEventListener('visibilitychange', handleVisibilityChange);
  }, [refetchSnapshot]);

  // Selected stop calculations
  const targetStop = useMemo(() => {
    if (!snapshot) return null;
    const code = selectedStopCode || snapshot.selected_stop.station_code;
    return snapshot.all_stops.find((s) => s.station_code === code) || snapshot.all_stops[0];
  }, [snapshot, selectedStopCode]);

  const targetStopKm = targetStop?.distance_km ?? 435.0;
  const distToStopKm = Math.max(0, Math.round((targetStopKm - drKm) * 10) / 10);
  const targetExpectedTime = targetStop?.predicted_arr || targetStop?.predicted_dep || snapshot?.selected_stop.expected_arr || '00:00';

  // Live ETA Countdown
  const { etaCountdown, isApproachingStop } = useMemo(() => {
    if (!targetExpectedTime || isCompleted) {
      return { etaCountdown: '00:00:00', isApproachingStop: false };
    }

    const parts = targetExpectedTime.split(':').map((v: string) => parseInt(v, 10));
    const expH = parts[0] || 0;
    const expM = parts[1] || 0;

    const now = new Date();
    const targetDate = new Date();
    targetDate.setHours(expH, expM, 0, 0);

    if (targetDate.getTime() < now.getTime() - 1000 * 60 * 60 * 12) {
      targetDate.setDate(targetDate.getDate() + 1);
    }

    const diffSeconds = Math.max(0, Math.floor((targetDate.getTime() - now.getTime()) / 1000));
    const hours = Math.floor(diffSeconds / 3600);
    const mins = Math.floor((diffSeconds % 3600) / 60);
    const secs = diffSeconds % 60;

    const formatted =
      hours > 0
        ? `${hours}h ${String(mins).padStart(2, '0')}m ${String(secs).padStart(2, '0')}s`
        : `${mins}m ${String(secs).padStart(2, '0')}s`;

    const approaching = diffSeconds <= 15 * 60 || distToStopKm <= 15.0;

    return { etaCountdown: formatted, isApproachingStop: approaching };
  }, [targetExpectedTime, isCompleted, distToStopKm]);

  // Station Alarm Trigger Check
  useEffect(() => {
    if (!alarmEnabled || alarmFired || isCompleted) return;

    const parts = targetExpectedTime.split(':').map((v: string) => parseInt(v, 10));
    const expH = parts[0] || 0;
    const expM = parts[1] || 0;

    const now = new Date();
    const targetDate = new Date();
    targetDate.setHours(expH, expM, 0, 0);
    const remainingMins = Math.max(0, Math.floor((targetDate.getTime() - now.getTime()) / 60000));

    if (remainingMins <= alarmThresholdMin || distToStopKm <= 10.0) {
      setAlarmFired(true);
      playRailwayChime();

      if ('Notification' in window && Notification.permission === 'granted') {
        new Notification(`Arriving at ${targetStop?.station_name || 'your station'}!`, {
          body: `Train ${trainNo || ''} is approximately ${remainingMins} minutes away. Please prepare to alight.`,
          icon: '/favicon.ico',
        });
      }
    }
  }, [alarmEnabled, alarmFired, isCompleted, targetStop, targetExpectedTime, alarmThresholdMin, distToStopKm, trainNo]);

  const toggleAlarm = useCallback(async (enable?: boolean) => {
    const shouldEnable = enable !== undefined ? enable : !alarmEnabled;
    if (shouldEnable) {
      if ('Notification' in window && Notification.permission === 'default') {
        try {
          await Notification.requestPermission();
        } catch {
          // ignore
        }
      }
      localStorage.setItem('rtx_station_alarm_enabled', 'true');
      setAlarmEnabled(true);
      setAlarmFired(false);
      playRailwayChime();
      return true;
    } else {
      localStorage.setItem('rtx_station_alarm_enabled', 'false');
      setAlarmEnabled(false);
      setAlarmFired(false);
      return false;
    }
  }, [alarmEnabled]);

  const setAlarmThresholdMin = useCallback((mins: number) => {
    setAlarmThresholdMinState(mins);
    localStorage.setItem('rtx_station_alarm_minutes', String(mins));
  }, []);

  const dismissAlarm = useCallback(() => {
    setAlarmFired(false);
  }, []);

  const dismissCrossingToast = useCallback(() => {
    setActiveCrossingToast(null);
  }, []);

  const { modeLabel, modeLabelHi } = useMemo(() => {
    switch (mode) {
      case 'approaching':
        return {
          modeLabel: `Slowing for ${nextHaltNameRef.current}`,
          modeLabelHi: `${nextHaltNameRef.current} के लिए गति धीमी`,
        };
      case 'halted':
        return {
          modeLabel: `Halted at ${nextHaltCodeRef.current} · departs in ${Math.floor(dwellSecondsRemaining / 60)}:${String(dwellSecondsRemaining % 60).padStart(2, '0')}`,
          modeLabelHi: `${nextHaltCodeRef.current} पर रुकी है · प्रस्थान ${Math.floor(dwellSecondsRemaining / 60)}:${String(dwellSecondsRemaining % 60).padStart(2, '0')} में`,
        };
      case 'departing':
        return {
          modeLabel: `Departed ${nextHaltCodeRef.current} · accelerating`,
          modeLabelHi: `${nextHaltCodeRef.current} से प्रस्थान · गति बढ़ रही है`,
        };
      case 'moving':
      default:
        return {
          modeLabel: `Cruising at ${Math.round(displaySpeed)} km/h`,
          modeLabelHi: `${Math.round(displaySpeed)} किमी/घंटा पर गतिमान`,
        };
    }
  }, [mode, displaySpeed, dwellSecondsRemaining]);

  return {
    mode,
    modeLabel,
    modeLabelHi,
    drKm: Math.round(drKm * 100) / 100,
    odometerKm: `KM ${drKm.toFixed(1)}`,
    displaySpeed,
    speedHistory,
    distToStopKm,
    etaCountdown,
    isApproachingStop,
    dwellSecondsRemaining,
    lastFixAgeSeconds,
    isInterpolating: lastFixAgeSeconds > 4,
    calibrationNotice,
    activeCrossingToast,
    dismissCrossingToast,
    alarmEnabled,
    alarmThresholdMin,
    alarmFired,
    setAlarmThresholdMin,
    toggleAlarm,
    dismissAlarm,
  };
}
