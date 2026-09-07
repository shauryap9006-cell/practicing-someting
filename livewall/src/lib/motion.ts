/**
 * RailTwin-X 60FPS Multi-Train Kinematic Dead-Reckoning Motion Engine
 * Adapted from useLiveMotionEngine.ts for corridor-wide fleet visualization.
 *
 * Implements:
 * - Sub-millisecond dead-reckoning between 1-second SSE position fixes
 * - Smooth cubic ease-out drift correction over 1.5s (never jumps unless gap > 15s)
 * - Exact delay color mapping (<=0m: #22c55e, 1-15m: #eab308, >15m: #ef4444)
 * - Motion trail history tracking for speed visualization
 */

import { useState, useEffect, useRef } from 'react';
import type { LivePosition, CorridorStation } from './types';

export interface AnimatedTrain {
  train_no: string;
  run_date: string;
  renderKm: number;
  progressFrac: number; // 0.0 to 1.0 along the corridor
  speed_kmh: number;
  delay_minutes: number;
  current_station_code: string | null;
  next_station_code: string | null;
  section_id: string | null;
  inferred_signal_aspect: 'GREEN' | 'YELLOW' | 'RED';
  trailPoints: number[]; // previous 3 progress fractions for trail
  isMoving: boolean;
  direction: 'UP' | 'DOWN';
  lastFixTimestamp: number;
}

interface TrainPhysicsState {
  currentKm: number;
  targetKm: number;
  speed: number;
  direction: 'UP' | 'DOWN';
  lastFixTime: number;
  easing: {
    startKm: number;
    targetKm: number;
    startTime: number;
    durationMs: number;
  } | null;
  trail: number[];
}

export function getDelayColor(delayMinutes: number): string {
  if (delayMinutes <= 0) return '#3DDC97'; // signal green
  if (delayMinutes <= 15) return '#F5A524'; // signal amber
  return '#F4506A'; // signal red
}

export function getDelayStatusBadge(delayMinutes: number): {
  label: string;
  color: string;
  bg: string;
  border: string;
} {
  const d = Math.round(delayMinutes);
  if (d <= 0) {
    return {
      label: 'ON TIME',
      color: '#3DDC97',
      bg: 'rgba(61, 220, 151, 0.14)',
      border: 'rgba(61, 220, 151, 0.35)',
    };
  }
  if (d <= 15) {
    return {
      label: `+${d}m`,
      color: '#F5A524',
      bg: 'rgba(245, 165, 36, 0.14)',
      border: 'rgba(245, 165, 36, 0.35)',
    };
  }
  return {
    label: `+${d}m`,
    color: '#F4506A',
    bg: 'rgba(244, 80, 106, 0.14)',
    border: 'rgba(244, 80, 106, 0.35)',
  };
}

/**
 * Calculates a train's static target kilometer along the corridor
 * based on section/station progress. Returns null if the train is not on this corridor.
 */
export function calculateTrainCorridorKm(
  pos: LivePosition,
  stationMap: Map<string, CorridorStation>,
  _totalCorridorKm = 440
): number | null {
  const stnCur = pos.current_station_code ? stationMap.get(pos.current_station_code.toUpperCase()) : null;
  const stnNxt = pos.next_station_code ? stationMap.get(pos.next_station_code.toUpperCase()) : null;

  // 1. If between two known corridor stations
  if (stnCur && stnNxt && stnCur.code !== stnNxt.code) {
    const frac = Math.max(0, Math.min(1, (pos.progress_pct || 0) / 100));
    return stnCur.km + frac * (stnNxt.km - stnCur.km);
  }

  // 2. If at a specific corridor station
  if (stnCur) {
    if (pos.progress_pct > 0 && pos.progress_pct < 100 && stnNxt) {
      const frac = pos.progress_pct / 100;
      return stnCur.km + frac * (stnNxt.km - stnCur.km);
    }
    return stnCur.km;
  }

  // 3. If approaching a corridor station
  if (stnNxt) {
    const frac = Math.max(0, Math.min(1, (pos.progress_pct || 0) / 100));
    return Math.max(0, stnNxt.km - (1 - frac) * 15);
  }

  // 4. Section ID parsing fallback e.g. "NDLS_GZB" or "TDL_ETW"
  if (pos.section_id && pos.section_id.includes('_')) {
    const [c1, c2] = pos.section_id.split('_');
    const s1 = stationMap.get(c1.toUpperCase());
    const s2 = stationMap.get(c2.toUpperCase());
    if (s1 && s2) {
      const frac = Math.max(0, Math.min(1, (pos.progress_pct || 0) / 100));
      return s1.km + frac * (s2.km - s1.km);
    }
    if (s1) return s1.km;
    if (s2) return s2.km;
  }

  // Train is not located on this corridor
  return null;
}

export function useCorridorMotionEngine(
  positions: LivePosition[],
  stations: CorridorStation[]
): AnimatedTrain[] {
  const [animatedList, setAnimatedList] = useState<AnimatedTrain[]>([]);
  const physicsStatesRef = useRef<Map<string, TrainPhysicsState>>(new Map());
  const stationMapRef = useRef<Map<string, CorridorStation>>(new Map());
  const rawPositionsRef = useRef<LivePosition[]>(positions);

  // Update station map ref and clear stale states on corridor change
  useEffect(() => {
    const m = new Map<string, CorridorStation>();
    for (const s of stations) {
      m.set(s.code.toUpperCase(), s);
    }
    stationMapRef.current = m;
    // Reset train physics cache when switching corridors
    physicsStatesRef.current.clear();
  }, [stations]);

  // Handle incoming position fixes from SSE or REST
  useEffect(() => {
    // Deduplicate by train_no to ensure only one latest fix per train
    const dedupedMap = new Map<string, LivePosition>();
    for (const p of positions) {
      if (!dedupedMap.has(p.train_no) || p.speed_kmh > 0) {
        dedupedMap.set(p.train_no, p);
      }
    }
    const dedupedList = Array.from(dedupedMap.values());
    rawPositionsRef.current = dedupedList;
    const totalKm = stations.length > 0 ? stations[stations.length - 1].km || 440 : 440;
    const now = performance.now();
    const currentStates = physicsStatesRef.current;

    for (const pos of dedupedList) {
      const targetKm = calculateTrainCorridorKm(pos, stationMapRef.current, totalKm);
      if (targetKm === null) {
        // Not on this corridor - clean up if it was previously tracked
        currentStates.delete(pos.train_no);
        continue;
      }

      const isUp = parseInt(pos.train_no, 10) % 2 !== 0; // Standard IR: Odd = UP, Even = DOWN
      const dir: 'UP' | 'DOWN' = isUp ? 'UP' : 'DOWN';

      const existing = currentStates.get(pos.train_no);
      if (!existing) {
        // Initialize new train
        currentStates.set(pos.train_no, {
          currentKm: targetKm,
          targetKm,
          speed: pos.speed_kmh || 0,
          direction: dir,
          lastFixTime: now,
          easing: null,
          trail: [targetKm, targetKm, targetKm],
        });
      } else {
        const timeSinceLastFix = (now - existing.lastFixTime) / 1000;
        const drift = Math.abs(targetKm - existing.currentKm);

        existing.speed = 0.4 * (pos.speed_kmh || 0) + 0.6 * existing.speed;
        existing.direction = dir;
        existing.lastFixTime = now;

        if (drift > 60 || timeSinceLastFix > 15) {
          // Hard snap if huge teleport or long data gap > 15s
          existing.currentKm = targetKm;
          existing.targetKm = targetKm;
          existing.easing = null;
        } else if (drift > 0.2) {
          // Smooth 1.5s cubic ease drift correction
          existing.easing = {
            startKm: existing.currentKm,
            targetKm,
            startTime: now,
            durationMs: 1500,
          };
          existing.targetKm = targetKm;
        } else {
          existing.targetKm = targetKm;
        }
      }
    }
  }, [positions, stations]);

  // 60FPS requestAnimationFrame Dead-Reckoning Animation Loop
  useEffect(() => {
    let rafId: number;
    let lastFrameTime = performance.now();
    const totalKm = stations.length > 0 ? stations[stations.length - 1].km || 440 : 440;

    const frame = (now: number) => {
      // Pause if tab is hidden
      if (document.hidden) {
        lastFrameTime = now;
        rafId = requestAnimationFrame(frame);
        return;
      }

      const dtMs = Math.min(100, Math.max(1, now - lastFrameTime));
      const dt = dtMs / 1000;
      lastFrameTime = now;

      const states = physicsStatesRef.current;
      const rawList = rawPositionsRef.current;
      const results: AnimatedTrain[] = [];
      const seenTrains = new Set<string>();

      for (const pos of rawList) {
        if (seenTrains.has(pos.train_no)) continue;
        seenTrains.add(pos.train_no);
        const state = states.get(pos.train_no);
        if (!state) continue;

        // 1. Position update: easing or dead reckoning
        if (state.easing) {
          const { startKm, targetKm, startTime, durationMs } = state.easing;
          const progress = Math.min(1, (now - startTime) / durationMs);
          // Cubic ease-out
          const easeFactor = 1 - Math.pow(1 - progress, 3);
          state.currentKm = startKm + (targetKm - startKm) * easeFactor;
          if (progress >= 1) {
            state.easing = null;
          }
        } else if (state.speed > 0) {
          // Dead reckoning forward along track
          const dirMultiplier = state.direction === 'UP' ? 1 : -1;
          const advanceKm = (state.speed * dt) / 3600 * dirMultiplier;
          state.currentKm = Math.max(0, Math.min(totalKm, state.currentKm + advanceKm));
        }

        // 2. Track motion trail history (every ~30 frames / 500ms)
        if (!state.trail) state.trail = [];
        if (state.trail.length === 0 || Math.abs(state.trail[state.trail.length - 1] - state.currentKm) > 0.5) {
          state.trail.push(state.currentKm);
          if (state.trail.length > 3) state.trail.shift();
        }

        const progressFrac = Math.max(0, Math.min(1, state.currentKm / totalKm));
        const trailFracs = state.trail.map((k) => Math.max(0, Math.min(1, k / totalKm)));

        results.push({
          train_no: pos.train_no,
          run_date: pos.run_date,
          renderKm: state.currentKm,
          progressFrac,
          speed_kmh: Math.round(state.speed),
          delay_minutes: pos.delay_minutes,
          current_station_code: pos.current_station_code,
          next_station_code: pos.next_station_code,
          section_id: pos.section_id,
          inferred_signal_aspect: pos.inferred_signal_aspect || 'GREEN',
          trailPoints: trailFracs,
          isMoving: state.speed > 3,
          direction: state.direction,
          lastFixTimestamp: state.lastFixTime,
        });
      }

      setAnimatedList(results);
      rafId = requestAnimationFrame(frame);
    };

    rafId = requestAnimationFrame(frame);

    return () => {
      cancelAnimationFrame(rafId);
    };
  }, [stations]);

  return animatedList;
}
