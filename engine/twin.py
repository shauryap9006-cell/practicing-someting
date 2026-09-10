"""engine/twin.py — Pure Math Kinematic Physics Digital Twin Engine (Part 4 Force Model & L1).

Pure mathematical equations of motion with ZERO database dependencies:
1. State vector: km, v, phase (CRUISE, APPROACH, DWELL, DEPART, TSR_ZONE, HELD, FOG).
2. Force model: F_te(v) = min(F_MAX, P / v) capped by adhesion mu * m_loco * g.
3. Resistance: Davis formula R = m_t * (c0 + c1*v + c2*v^2), grade force F_g, curve resistance F_c.
4. Acceleration: a = (F_te - R - F_g - F_c) / (m * (1 + lambda)).
5. Service braking: a_b = 0.50 m/s^2 (NO crawl clamps, NO x1.2 fudges).
6. Target-speed braking law: v_allow = sqrt(v_target^2 + 2 * a_b * d_remaining).
7. Speed clamp: v = min(line_limit, class_max, TSR, v_allow). Removed x1.1 fudge.
8. Calibrated dwell: sched_halt * (1 +- 15%) via local deterministic RNG.
9. Monotonic distance: km is strictly non-decreasing. Sub-stepping at 1.0 s.
"""

from __future__ import annotations

import datetime
import hashlib
import math
import random
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

# Rolling Stock Class Parameters (Part 4 Spec)
TRAIN_CLASSES: Dict[str, Dict[str, Any]] = {
    "premium": {
        "F_MAX": 300_000.0,
        "P": 4.74e6,
        "m_t": 1200.0,
        "m_loco": 123_000.0,
        "vmax": 130.0,
        "c0": 2.4,
        "c1": 0.022,
        "c2": 0.00082,
        "lambda_rot": 0.08,
    },
    "mail/exp": {
        "F_MAX": 260_000.0,
        "P": 4.20e6,
        "m_t": 1100.0,
        "m_loco": 123_000.0,
        "vmax": 110.0,
        "c0": 2.4,
        "c1": 0.022,
        "c2": 0.00082,
        "lambda_rot": 0.08,
    },
    "passenger": {
        "F_MAX": 200_000.0,
        "P": 3.00e6,
        "m_t": 900.0,
        "m_loco": 113_000.0,
        "vmax": 100.0,
        "c0": 2.4,
        "c1": 0.022,
        "c2": 0.00082,
        "lambda_rot": 0.07,
    },
    "freight": {
        "F_MAX": 400_000.0,
        "P": 4.74e6,
        "m_t": 4000.0,
        "m_loco": 123_000.0,
        "vmax": 75.0,
        "c0": 3.0,
        "c1": 0.025,
        "c2": 0.00050,
        "lambda_rot": 0.10,
    },
    "EMU": {
        "F_MAX": 240_000.0,
        "P": 3.60e6,
        "m_t": 720.0,
        "m_loco": 360_000.0,
        "vmax": 110.0,
        "c0": 2.4,
        "c1": 0.022,
        "c2": 0.00082,
        "lambda_rot": 0.05,
    },
}


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
    rng: Optional[random.Random] = None
    train_class: str = "premium"
    adhesion_mu: float = 0.35

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
    """Physics digital twin engine modeling real longitudinal train dynamics."""

    def __init__(
        self,
        accel_mps2: float = 0.45,  # Preserved for backward-compat
        brake_mps2: float = 0.50,  # Service braking rate (Part 4)
        default_max_speed_kmh: float = 130.0,
        fog_reduction_pct: float = 0.20,
        chronic_bias_min: float = 0.0,
        seed: Optional[int] = None,
    ):
        self.service_brake_mps2 = 0.50  # Strict Part 4 service braking rate
        self.brake_mps2 = brake_mps2
        self.default_max_speed_kmh = default_max_speed_kmh
        self.fog_reduction_pct = fog_reduction_pct
        self.chronic_bias_min = chronic_bias_min
        self.seed = seed if seed is not None else 42
        self.rng = random.Random(self.seed)

    def compute_stopping_distance_km(self, current_speed_kmh: float) -> float:
        """Calculates stopping distance in km using service braking a_b = 0.50 m/s^2."""
        if current_speed_kmh <= 0.0:
            return 0.0
        v_mps = current_speed_kmh / 3.6
        d_m = (v_mps**2) / (2.0 * self.service_brake_mps2)
        return d_m / 1000.0

    def get_class_params(self, train_class: str) -> Dict[str, Any]:
        """Returns standard rolling stock parameters for train class."""
        norm_class = train_class.lower()
        if norm_class in TRAIN_CLASSES:
            return TRAIN_CLASSES[norm_class]
        if "freight" in norm_class:
            return TRAIN_CLASSES["freight"]
        if "emu" in norm_class or "memu" in norm_class:
            return TRAIN_CLASSES["EMU"]
        if "pass" in norm_class:
            return TRAIN_CLASSES["passenger"]
        return TRAIN_CLASSES["premium"]

    def compute_acceleration(
        self,
        params: Dict[str, Any],
        v_mps: float,
        mu: float = 0.35,
        gradient_per_mille: float = 0.0,
        curve_radius_m: Optional[float] = None,
    ) -> float:
        """Computes instantaneous acceleration a = (F_te - R - F_g - F_c) / (m * (1+lambda))."""
        F_MAX = params["F_MAX"]
        P = params["P"]
        m_t = params["m_t"]
        m_loco = params["m_loco"]
        c0 = params["c0"]
        c1 = params["c1"]
        c2 = params["c2"]
        lambda_rot = params["lambda_rot"]

        # Tractive effort with power curve P / v
        comfort_ramp = min(1.0, 0.45 + 0.55 * (v_mps / 8.0))
        F_te = min(F_MAX, P / max(0.1, v_mps)) * comfort_ramp

        # Adhesion cap: F_te <= mu * m_loco * g
        F_adhesion = mu * m_loco * 9.81
        F_te = min(F_te, F_adhesion)

        # Train resistance (Davis equation per tonne)
        v_kmh = v_mps * 3.6
        R = m_t * (c0 + c1 * v_kmh + c2 * (v_kmh**2))

        # Grade force: F_g = m * g * (i / 1000)
        F_g = (m_t * 1000.0) * 9.81 * (gradient_per_mille / 1000.0)

        # Curve resistance: F_c = m_t * 9.81 * (700 / R_curve)
        F_c = 0.0
        if curve_radius_m is not None and not math.isinf(curve_radius_m) and curve_radius_m > 0:
            F_c = m_t * 9.81 * (700.0 / curve_radius_m)

        m_eff = (m_t * 1000.0) * (1.0 + lambda_rot)
        return (F_te - R - F_g - F_c) / m_eff

    def create_train_state(
        self,
        train_no: str,
        stops: List[Dict[str, Any]],
        start_km: Optional[float] = None,
        start_speed_kmh: float = 0.0,
        start_phase: str = "DWELL",
        seed: Optional[int] = None,
        train_class: Optional[str] = None,
        adhesion_mu: float = 0.35,
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

        init_km = (
            start_km if start_km is not None else (parsed_stops[0].km if parsed_stops else 0.0)
        )
        init_idx = 0
        if start_km is not None and parsed_stops:
            for idx, stp in enumerate(parsed_stops):
                if stp.km > start_km:
                    init_idx = idx
                    break
            else:
                init_idx = len(parsed_stops) - 1

        effective_seed = seed if seed is not None else self.seed
        train_seed = int(
            hashlib.sha256(f"{effective_seed}_{train_no}".encode("utf-8")).hexdigest()[:8], 16
        )
        train_rng = random.Random(train_seed)

        # Detect class if not explicitly passed
        resolved_class = train_class or "premium"
        if train_class is None:
            if train_no.startswith("120") or train_no.startswith("123") or train_no.startswith("124"):
                resolved_class = "premium"
            elif train_no.startswith("54") or train_no.startswith("6"):
                resolved_class = "passenger"
            elif "freight" in train_no.lower() or train_no.startswith("F_"):
                resolved_class = "freight"

        return TwinTrainState(
            train_no=str(train_no),
            km=init_km,
            speed_kmh=start_speed_kmh,
            ema_speed_kmh=start_speed_kmh,
            phase=start_phase,
            current_stop_idx=init_idx,
            stops=parsed_stops,
            dwell_remaining_sec=float(parsed_stops[init_idx].halt_min * 60.0)
            if parsed_stops
            else 120.0,
            source="simulated",
            rng=train_rng,
            train_class=resolved_class,
            adhesion_mu=adhesion_mu,
        )

    def advance(
        self,
        state: TwinTrainState,
        dt_seconds: float,
        sim_time_iso: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> Tuple[TwinTrainState, List[Dict[str, Any]]]:
        """Advances train kinematics by dt_seconds, breaking into 1.0 s sub-steps."""
        if dt_seconds <= 0.0:
            return state, []

        all_events: List[Dict[str, Any]] = []
        remaining = dt_seconds
        step_sz = 1.0

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
        """Single 1.0 s sub-step physics simulation using force model & target-speed braking."""
        if dt_seconds <= 0.0:
            return state, []

        ctx = context or {}
        active_tsr_kmh = ctx.get("active_tsr_kmh")
        fog_active = bool(ctx.get("fog_active", False))
        block_occupied = bool(ctx.get("block_occupied", False))
        signal_aspect = str(ctx.get("signal_aspect", "GREEN")).upper()
        platform_occupied = bool(ctx.get("platform_occupied", False))
        gradient_per_mille = float(ctx.get("gradient_per_mille", 0.0))
        curve_radius_m = ctx.get("curve_radius_m")
        section_max_speed_kmh = ctx.get("section_max_speed_kmh")

        events: List[Dict[str, Any]] = []

        # Terminal state check
        if state.is_terminated:
            state.speed_kmh = 0.0
            state.ema_speed_kmh = 0.0
            state.phase = "DWELL"
            return state, events

        # Phase 1: DWELL & LOOP_HELD handling
        if state.phase in ("LOOP_HELD", "HELD_LOOP"):
            state.speed_kmh = 0.0
            state.ema_speed_kmh = 0.0
            state.held_reason = "LOOP_HOLD"
            return state, events

        if state.phase == "DWELL":
            state.speed_kmh = 0.0
            state.ema_speed_kmh = 0.0
            if platform_occupied:
                state.held_reason = "PLATFORM_OCCUPIED"
                return state, events

            state.dwell_remaining_sec -= dt_seconds
            if state.dwell_remaining_sec <= 0.0:
                cur_stop = state.current_stop
                station_code = cur_stop.station_code if cur_stop else "STN"
                events.append(
                    {
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
                    }
                )
                state.phase = "DEPART"
                state.held_reason = None
                if state.current_stop_idx < len(state.stops) - 1:
                    state.current_stop_idx += 1
            return state, events

        params = self.get_class_params(state.train_class)
        class_vmax = float(params["vmax"])
        a_b = self.service_brake_mps2  # 0.50 m/s^2

        # 1. Line and Class Limits
        line_speed = self.default_max_speed_kmh
        if section_max_speed_kmh is not None and float(section_max_speed_kmh) < line_speed:
            line_speed = float(section_max_speed_kmh)

        v_cap_kmh = min(line_speed, class_vmax)
        if active_tsr_kmh is not None and float(active_tsr_kmh) < v_cap_kmh:
            v_cap_kmh = float(active_tsr_kmh)
        if fog_active:
            v_cap_kmh *= 1.0 - self.fog_reduction_pct

        v_cap_mps = v_cap_kmh / 3.6
        v_curr_mps = state.speed_kmh / 3.6

        # 2. Target-Speed Braking Law: v_allow = sqrt(v_target^2 + 2 * a_b * d_remaining)
        next_halt = state.current_stop
        target_km = next_halt.km if next_halt else (state.stops[-1].km if state.stops else state.km)
        d_platform_m = max(0.0, (target_km - state.km) * 1000.0)

        # Target A: Platform stop (v_target = 0.0)
        v_allow_platform_mps = math.sqrt(2.0 * a_b * d_platform_m)

        # Target B: Signal stop (v_target = 0.0 at RED or occupied block)
        v_allow_signal_mps = float("inf")
        if signal_aspect == "RED" or block_occupied:
            sig_dist_m = ctx.get("signal_distance_m")
            if sig_dist_m is not None:
                d_sig = float(sig_dist_m)
                d_eff = max(0.0, d_sig - 400.0) + 5.0 * v_curr_mps
                v_allow_signal_mps = math.sqrt(2.0 * a_b * d_eff)
            else:
                v_allow_signal_mps = 0.0
        elif signal_aspect == "YELLOW":
            sig_dist_m = float(ctx.get("signal_distance_m", 1000.0))
            v_allow_signal_mps = math.sqrt((30.0 / 3.6)**2 + 2.0 * a_b * sig_dist_m)
        elif signal_aspect == "DOUBLE_YELLOW":
            sig_dist_m = float(ctx.get("signal_distance_m", 2000.0))
            v_allow_signal_mps = math.sqrt((60.0 / 3.6)**2 + 2.0 * a_b * sig_dist_m)

        # Governed permissible speed
        v_allow_mps = min(v_allow_platform_mps, v_allow_signal_mps)
        v_allow_kmh = v_allow_mps * 3.6

        # Speed clamp: v <= min(line, class, TSR, v_allow). NO x1.1 fudge.
        v_target_mps = min(v_cap_mps, v_allow_mps)
        v_target_kmh = v_target_mps * 3.6

        # Check Station Arrival marker (within +-20m)
        if d_platform_m <= 20.0 and state.speed_kmh <= 15.0:
            state.km = target_km
            state.speed_kmh = 0.0
            state.ema_speed_kmh = 0.0
            state.phase = "DWELL"

            sched_halt = next_halt.halt_min if next_halt else 2.0
            dwell_rng = state.rng or self.rng
            noise = dwell_rng.gauss(0.0, 0.15)
            actual_halt_sec = max(60.0, sched_halt * 60.0 * (1.0 + noise))
            state.dwell_remaining_sec = actual_halt_sec

            delay_min = 0.0
            if sim_time_iso and next_halt and next_halt.sched_arr and ":" in next_halt.sched_arr:
                try:
                    dt = datetime.datetime.fromisoformat(sim_time_iso)
                    sh, sm = [int(x) for x in next_halt.sched_arr.split(":")[:2]]
                    sched_dt = datetime.datetime(
                        dt.year, dt.month, dt.day, sh, sm, tzinfo=dt.tzinfo
                    )
                    delay_min = max(0.0, (dt - sched_dt).total_seconds() / 60.0)
                except Exception:
                    pass

            events.append(
                {
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
                }
            )
            return state, events

        # Kinetic Update: Force Acceleration or Service Braking
        if v_curr_mps < v_target_mps:
            # Tractive effort acceleration
            a_net = self.compute_acceleration(
                params=params,
                v_mps=v_curr_mps,
                mu=state.adhesion_mu,
                gradient_per_mille=gradient_per_mille,
                curve_radius_m=curve_radius_m,
            )
            v_next_mps = min(v_target_mps, v_curr_mps + a_net * dt_seconds)
            state.speed_kmh = max(0.0, v_next_mps * 3.6)
            state.phase = "DEPART" if state.speed_kmh < v_cap_kmh * 0.9 else "CRUISE"
        elif v_curr_mps > v_target_mps:
            # Monotone service braking (NO crawl clamps, NO x1.2 fudges)
            v_next_mps = max(v_target_mps, v_curr_mps - a_b * dt_seconds)
            state.speed_kmh = max(0.0, v_next_mps * 3.6)
            if signal_aspect == "RED" or block_occupied:
                state.phase = "HELD" if state.speed_kmh <= 0.5 else "APPROACH"
            else:
                state.phase = "APPROACH" if v_allow_kmh < v_cap_kmh else "CRUISE"
        else:
            if (signal_aspect == "RED" or block_occupied) and state.speed_kmh <= 0.5:
                state.phase = "HELD"
            else:
                state.phase = "CRUISE"

        if active_tsr_kmh is not None and state.speed_kmh >= float(active_tsr_kmh) - 1.0:
            state.phase = "TSR_ZONE"
        if fog_active:
            state.phase = "FOG"

        # Advance distance with guaranteed monotonicity
        v_step_mps = state.speed_kmh / 3.6
        step_km = (v_step_mps * dt_seconds) / 1000.0
        state.km = max(state.km, min(target_km, state.km + step_km))
        state.held_reason = "SIGNAL_HOLD" if state.phase == "HELD" else None
        self._update_ema(state)

        return state, events

    def _update_ema(self, state: TwinTrainState) -> None:
        """Updates 3-tick Exponential Moving Average of speed."""
        if state.speed_kmh <= 0.0:
            state.ema_speed_kmh = 0.0
        else:
            alpha = 0.5
            state.ema_speed_kmh = round(
                alpha * state.speed_kmh + (1.0 - alpha) * state.ema_speed_kmh, 1
            )
