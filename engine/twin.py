"""engine/twin.py — Pure Math Kinematic Physics Digital Twin Engine (F02, F17, F28).

Pure mathematical equations of motion with ZERO database dependencies:
1. State vector: km, v, phase (CRUISE, APPROACH, DWELL, DEPART, TSR_ZONE, HELD, FOG).
2. Acceleration: 0.45 m/s² capped by section limit.
3. Deceleration: 0.65 m/s² targeting station halt or signal block boundary.
4. TSR: strictly clamped to active temporary speed restriction.
5. Signal hold: deceleration to stop and hold when block ahead is occupied.
6. Weather/Fog factor: 15-30% cruise speed reduction under dense fog.
7. Dwell variance: scheduled halt ± N(0, 20%); extended while platform occupied.
8. Structured events: ARRIVAL / DEPARTURE tagged with source: "simulated".
9. Monotonic distance: km is strictly non-decreasing.
10. Multi-scale sub-stepping for numerical stability under high clock acceleration.
"""
from __future__ import annotations

import datetime
import math
import random
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class TwinStop:
    """A scheduled stop along a train route."""
    station_code: str
    seq: int
    km: float
    sched_arr: Optional[str] = None
    sched_dep: Optional[str] = None
    halt_min: float = 2.0
    lat: float = 0.0
    lon: float = 0.0


@dataclass
class TwinTrainState:
    """Full kinematic state of a simulated train."""
    train_no: str
    km: float
    speed_kmh: float
    phase: str  # "CRUISE", "APPROACH", "DWELL", "DEPART", "TSR_ZONE", "HELD", "FOG"
    current_stop_idx: int
    stops: List[TwinStop]
    dwell_remaining_sec: float = 0.0
    held_reason: Optional[str] = None
    source: str = "simulated"
    ema_speed_kmh: float = 0.0

    @property
    def current_stop(self) -> Optional[TwinStop]:
        if 0 <= self.current_stop_idx < len(self.stops):
            return self.stops[self.current_stop_idx]
        return None

    @property
    def next_stop(self) -> Optional[TwinStop]:
        next_idx = self.current_stop_idx + 1
        if 0 <= next_idx < len(self.stops):
            return self.stops[next_idx]
        return None

    @property
    def is_terminated(self) -> bool:
        return self.current_stop_idx >= len(self.stops) - 1 and self.phase == "DWELL"


class TwinEngine:
    """Pure mathematical kinematic simulation engine."""

    def __init__(
        self,
        accel_mps2: float = 0.45,
        brake_mps2: float = 0.65,
        default_max_speed_kmh: float = 130.0,
        fog_reduction_pct: float = 0.20,
        chronic_bias_min: float = 0.0,
    ):
        self.accel_mps2 = accel_mps2
        self.brake_mps2 = brake_mps2
        self.accel_kmh_per_sec = accel_mps2 * 3.6  # 1.62 km/h/s
        self.brake_kmh_per_sec = brake_mps2 * 3.6  # 2.34 km/h/s
        self.default_max_speed_kmh = default_max_speed_kmh
        self.fog_reduction_pct = fog_reduction_pct
        self.chronic_bias_min = chronic_bias_min

    def compute_stopping_distance_km(self, current_speed_kmh: float) -> float:
        """Calculates stopping distance in km from current speed at brake_mps2."""
        if current_speed_kmh <= 0.0:
            return 0.0
        v_mps = current_speed_kmh / 3.6
        d_m = (v_mps ** 2) / (2.0 * self.brake_mps2)
        return d_m / 1000.0

    def create_train_state(
        self,
        train_no: str,
        stops: List[Dict[str, Any]],
        start_km: Optional[float] = None,
        start_speed_kmh: float = 0.0,
        start_phase: str = "DWELL",
    ) -> TwinTrainState:
        """Initializes a TwinTrainState from route stop specifications."""
        parsed_stops = [
            TwinStop(
                station_code=str(s.get("station_code", "")).upper(),
                seq=int(s.get("seq", i + 1)),
                km=float(s.get("km", s.get("distance_km", 0.0))),
                sched_arr=s.get("sched_arr"),
                sched_dep=s.get("sched_dep"),
                halt_min=float(s.get("halt_min", 2.0)),
                lat=float(s.get("lat", 0.0)),
                lon=float(s.get("lon", 0.0)),
            )
            for i, s in enumerate(stops)
        ]
        parsed_stops.sort(key=lambda s: s.seq)

        init_km = start_km if start_km is not None else (parsed_stops[0].km if parsed_stops else 0.0)
        init_idx = 0
        if start_km is not None and parsed_stops:
            for idx, stp in enumerate(parsed_stops):
                if stp.km > start_km:
                    init_idx = idx
                    break
            else:
                init_idx = len(parsed_stops) - 1

        return TwinTrainState(
            train_no=str(train_no),
            km=init_km,
            speed_kmh=start_speed_kmh,
            ema_speed_kmh=start_speed_kmh,
            phase=start_phase,
            current_stop_idx=init_idx,
            stops=parsed_stops,
            dwell_remaining_sec=float(parsed_stops[init_idx].halt_min * 60.0) if parsed_stops else 120.0,
            source="simulated",
        )

    def advance(
        self,
        state: TwinTrainState,
        dt_seconds: float,
        sim_time_iso: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> Tuple[TwinTrainState, List[Dict[str, Any]]]:
        """Advances train kinematics by dt_seconds, breaking into sub-steps for stability."""
        if dt_seconds <= 0.0:
            return state, []

        all_events: List[Dict[str, Any]] = []
        remaining = dt_seconds
        step_sz = 1.0  # 1-second sub-steps for physical accuracy

        while remaining > 0.0:
            sub_dt = min(step_sz, remaining)
            state, evs = self._advance_single_step(
                state, sub_dt, sim_time_iso=sim_time_iso, context=context
            )
            if evs:
                all_events.extend(evs)
            remaining -= sub_dt
            if state.is_terminated:
                break

        return state, all_events

    def _advance_single_step(
        self,
        state: TwinTrainState,
        dt_seconds: float,
        sim_time_iso: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> Tuple[TwinTrainState, List[Dict[str, Any]]]:
        """Single sub-step physics simulation."""
        if dt_seconds <= 0.0:
            return state, []

        ctx = context or {}
        active_tsr_kmh = ctx.get("active_tsr_kmh")
        fog_active = bool(ctx.get("fog_active", False))
        block_occupied = bool(ctx.get("block_occupied", False))
        signal_aspect = str(ctx.get("signal_aspect", "GREEN")).upper()
        platform_occupied = bool(ctx.get("platform_occupied", False))

        events: List[Dict[str, Any]] = []

        # Terminal state check
        if state.is_terminated:
            state.speed_kmh = 0.0
            state.ema_speed_kmh = 0.0
            state.phase = "DWELL"
            return state, events

        # Phase 1: DWELL handling
        if state.phase == "DWELL":
            state.speed_kmh = 0.0
            state.ema_speed_kmh = 0.0
            if platform_occupied:
                state.held_reason = "PLATFORM_OCCUPIED"
                return state, events

            state.dwell_remaining_sec -= dt_seconds
            if state.dwell_remaining_sec <= 0.0:
                # Depart station
                cur_stop = state.current_stop
                station_code = cur_stop.station_code if cur_stop else "STN"
                events.append({
                    "event_type": "DEPARTURE",
                    "train_no": state.train_no,
                    "station_code": station_code,
                    "seq": cur_stop.seq if cur_stop else 1,
                    "km": state.km,
                    "timestamp": sim_time_iso,
                    "sched_arr": cur_stop.sched_arr if cur_stop else None,
                    "sched_dep": cur_stop.sched_dep if cur_stop else None,
                    "delay_dep_min": 0.0,
                    "source": "simulated",
                })
                state.phase = "DEPART"
                state.held_reason = None
                # Move target to next stop
                if state.current_stop_idx < len(state.stops) - 1:
                    state.current_stop_idx += 1
            return state, events

        # Signal hold handling
        if signal_aspect == "RED" or block_occupied:
            if state.speed_kmh > 0.0:
                brake_delta = self.brake_kmh_per_sec * dt_seconds
                state.speed_kmh = max(0.0, state.speed_kmh - brake_delta)
                v_avg_mps = state.speed_kmh / 3.6
                dist_km = (v_avg_mps * dt_seconds) / 1000.0
                state.km += dist_km
            state.phase = "HELD"
            state.held_reason = "SIGNAL_HOLD"
            self._update_ema(state)
            return state, events

        # Determine target speed limit
        target_speed = self.default_max_speed_kmh
        current_phase = "CRUISE"

        # Permanent section speed limit (Bug #2 fix): cruise speed must never
        # exceed the block section's own permanent max_speed_kmph, independent
        # of any temporary TSR applied below.
        section_max_speed_kmh = ctx.get("section_max_speed_kmh")
        if section_max_speed_kmh is not None and float(section_max_speed_kmh) < target_speed:
            target_speed = float(section_max_speed_kmh)

        if fog_active:
            target_speed *= (1.0 - self.fog_reduction_pct)
            current_phase = "FOG"

        if active_tsr_kmh is not None and active_tsr_kmh < target_speed:
            target_speed = float(active_tsr_kmh)
            current_phase = "TSR_ZONE"

        # Check distance to target stop
        next_halt = state.current_stop
        target_km = next_halt.km if next_halt else (state.stops[-1].km if state.stops else state.km)
        dist_to_stop_km = target_km - state.km
        stop_dist_km = self.compute_stopping_distance_km(state.speed_kmh)

        if dist_to_stop_km <= 0.05:
            # Train arrived at station!
            state.km = target_km
            state.speed_kmh = 0.0
            state.ema_speed_kmh = 0.0
            state.phase = "DWELL"
            # Random calibrated dwell duration: sched_halt * (1 ± 15%)
            sched_halt = next_halt.halt_min if next_halt else 2.0
            noise = random.gauss(0.0, 0.15)
            actual_halt_sec = max(60.0, sched_halt * 60.0 * (1.0 + noise))
            state.dwell_remaining_sec = actual_halt_sec

            # Calculate actual arrival delay
            delay_min = 0.0
            if sim_time_iso and next_halt and next_halt.sched_arr and ":" in next_halt.sched_arr:
                try:
                    dt = datetime.datetime.fromisoformat(sim_time_iso)
                    sh, sm = [int(x) for x in next_halt.sched_arr.split(":")[:2]]
                    sched_dt = datetime.datetime(dt.year, dt.month, dt.day, sh, sm, tzinfo=dt.tzinfo)
                    delay_min = max(0.0, (dt - sched_dt).total_seconds() / 60.0)
                except Exception:
                    pass

            events.append({
                "event_type": "ARRIVAL",
                "train_no": state.train_no,
                "station_code": next_halt.station_code if next_halt else "STN",
                "seq": next_halt.seq if next_halt else 1,
                "km": target_km,
                "timestamp": sim_time_iso,
                "sched_arr": next_halt.sched_arr if next_halt else None,
                "sched_dep": next_halt.sched_dep if next_halt else None,
                "delay_arr_min": round(delay_min, 1),
                "source": "simulated",
            })
            return state, events

        # If inside stopping distance, enter APPROACH and brake
        if dist_to_stop_km <= stop_dist_km * 1.2:
            current_phase = "APPROACH"
            brake_delta = self.brake_kmh_per_sec * dt_seconds
            state.speed_kmh = max(10.0, state.speed_kmh - brake_delta)
        elif state.speed_kmh < target_speed:
            # Accelerate
            accel_delta = self.accel_kmh_per_sec * dt_seconds
            state.speed_kmh = min(target_speed, state.speed_kmh + accel_delta)
            if state.speed_kmh < target_speed * 0.9:
                current_phase = "DEPART"
        elif state.speed_kmh > target_speed:
            # Decelerate to target speed limit
            brake_delta = self.brake_kmh_per_sec * dt_seconds
            state.speed_kmh = max(target_speed, state.speed_kmh - brake_delta)

        # Enforce speed bounds: [0, section_max * 1.1]
        max_allowed = self.default_max_speed_kmh * 1.1
        state.speed_kmh = max(0.0, min(max_allowed, state.speed_kmh))

        # Kinematic distance step with guaranteed monotonicity
        v_mps = state.speed_kmh / 3.6
        step_km = (v_mps * dt_seconds) / 1000.0
        state.km = max(state.km, min(target_km, state.km + step_km))
        state.phase = current_phase
        state.held_reason = None
        self._update_ema(state)

        return state, events

    def _update_ema(self, state: TwinTrainState) -> None:
        """Updates 3-tick Exponential Moving Average of speed."""
        if state.speed_kmh <= 0.0:
            state.ema_speed_kmh = 0.0
        else:
            alpha = 0.5  # 3-tick EMA smoothing factor (2 / (3 + 1))
            state.ema_speed_kmh = round(alpha * state.speed_kmh + (1.0 - alpha) * state.ema_speed_kmh, 1)
