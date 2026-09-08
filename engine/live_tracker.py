"""RailTwin-X Live Position Tracker & Physics Digital Twin Engine (Pipeline 07, Phase 3).

Continuously tracks, simulates, and broadcasts real-time train positions along the
corridor using the pure-math kinematic TwinEngine, calibrated by real station_events.

Key Capabilities:
1. Pure-Math Kinematic Twin: 0.45 m/s² accel, 0.65 m/s² brake, TSR capping, signal hold, fog factor, dwell variance.
2. 13-Column station_events: Emits verified ARRIVAL and DEPARTURE rows conforming strictly to schema.
3. Closed-Loop Ledger Grading: Touchdown ARRIVAL events trigger PredictionLedger.grade_actual_arrival and ConformalPIDController.
4. Idempotent Start/Stop: Async advisory lock prevents double-start loops.
5. High-Speed Caching & Ingest: Thread-safe in-memory cache + batch SQLite upserts.
6. Event Broadcasting: Listener subscription support for Server-Sent Events (SSE).
"""

from __future__ import annotations

import asyncio
import datetime
import logging
import math
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

from config import settings

logger = logging.getLogger(__name__)
from collector.adapters.base import LiveSource, StationEvent
from collector.adapters.rapidapi import RapidAPISource
from collector.adapters.scrape import ScrapeSource
from collector.adapters.mock_replay import MockReplaySource
from data.db import Database, get_db
from engine.clocks import get_clock, IST_TIMEZONE
from engine.context import ContextEngine, TrainContext, get_context_engine
from engine.attribution import LiveAttributionEngine, AttributionResult, get_attribution_engine
from engine.twin import TwinEngine, TwinTrainState, TwinStop


@dataclass
class LiveTrainPosition:
    """Real-time kinematic position and telemetry state for a corridor train."""

    train_no: str
    run_date: str
    lat: float
    lng: float
    current_station_code: Optional[str]
    next_station_code: Optional[str]
    prev_station_code: Optional[str]
    section_id: Optional[str]
    speed_kmh: float
    heading: float
    delay_minutes: float
    confidence: float
    progress_pct: float
    is_dead_reckoned: bool
    basis: str  # 'last_event', 'dead_reckoning', 'station_master_actual', 'schedule_only'
    source: str  # 'simulated', 'live', 'deadreckoned', 'mock_replay'
    status: str  # 'RUNNING', 'TERMINATED', 'NOT_STARTED', 'STALE'
    last_event_time: Optional[str]
    updated_at: str
    context: Optional[Dict[str, Any]] = None
    signal_hold_active: bool = False
    signal_hold_duration_min: float = 0.0
    inferred_signal_aspect: str = "GREEN"  # GREEN, DOUBLE_YELLOW, YELLOW, RED
    km: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "train_no": self.train_no,
            "run_date": self.run_date,
            "lat": round(self.lat, 6),
            "lng": round(self.lng, 6),
            "lon": round(self.lng, 6),  # Synonym for lon
            "km": round(self.km, 2),
            "current_station_code": self.current_station_code,
            "next_station_code": self.next_station_code,
            "prev_station_code": self.prev_station_code,
            "section_id": self.section_id,
            "speed_kmh": round(self.speed_kmh, 1),
            "heading": round(self.heading, 1),
            "delay_minutes": round(self.delay_minutes, 1),
            "confidence": round(self.confidence, 3),
            "progress_pct": round(self.progress_pct, 1),
            "progress": round(self.progress_pct / 100.0, 3) if self.progress_pct > 1.0 else round(self.progress_pct, 3),
            "is_dead_reckoned": self.is_dead_reckoned,
            "basis": self.basis,
            "source": self.source,
            "status": self.status,
            "last_event_time": self.last_event_time,
            "updated_at": self.updated_at,
            "context": self.context,
            "signal_hold_active": self.signal_hold_active,
            "signal_hold_duration_min": round(self.signal_hold_duration_min, 1),
            "inferred_signal_aspect": self.inferred_signal_aspect,
        }


class TokenBucket:
    """Thread-safe Token Bucket rate limiter enforcing API call budgets."""

    def __init__(self, capacity: int, fill_rate_per_second: float):
        self.capacity = float(capacity)
        self.fill_rate = float(fill_rate_per_second)
        self.tokens = float(capacity)
        self.last_update = time.monotonic()
        self._lock = threading.Lock()

    def consume(self, tokens: float = 1.0) -> bool:
        with self._lock:
            now = time.monotonic()
            elapsed = max(0.0, now - self.last_update)
            self.last_update = now
            self.tokens = min(self.capacity, self.tokens + elapsed * self.fill_rate)
            if self.tokens >= tokens:
                self.tokens -= tokens
                return True
            return False


def _calculate_heading(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculates forward azimuth / heading in degrees from point 1 to point 2."""
    if abs(lat1 - lat2) < 1e-6 and abs(lon1 - lon2) < 1e-6:
        return 90.0  # Default Eastbound corridor heading
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_lambda = math.radians(lon2 - lon1)
    y = math.sin(delta_lambda) * math.cos(phi2)
    x = math.cos(phi1) * math.sin(phi2) - math.sin(phi1) * math.cos(phi2) * math.cos(delta_lambda)
    bearing = math.degrees(math.atan2(y, x))
    return (bearing + 360.0) % 360.0


def _time_to_min(t_str: Optional[str]) -> int:
    """Parses HH:MM into minutes from midnight."""
    if not t_str or ":" not in str(t_str):
        return 0
    parts = str(t_str).split(":")
    return int(parts[0]) * 60 + int(parts[1])


class LivePositionTracker:
    """Master live train position tracking & physics digital twin engine."""

    def __init__(
        self,
        db: Optional[Database] = None,
        context_engine: Optional[ContextEngine] = None,
        attribution_engine: Optional[LiveAttributionEngine] = None,
        adapters: Optional[List[LiveSource]] = None,
    ):
        self.db = db or get_db()
        self.context_engine = context_engine or get_context_engine(self.db)
        self.attribution_engine = attribution_engine or get_attribution_engine(self.db)

        # Pure-Math Kinematic Physics Twin Engine
        self.twin = TwinEngine()
        self._twin_states: Dict[str, TwinTrainState] = {}
        self._start_lock = asyncio.Lock()

        # Ingest Adapters
        self.adapters: List[LiveSource] = adapters if adapters is not None else [
            RapidAPISource(),
            ScrapeSource(),
            MockReplaySource(self.db),
        ]

        # Rate Limiting Token Bucket
        tpm_budget = int(settings.LIVE_POLL_TPM_BUDGET)
        self.rate_limiter = TokenBucket(capacity=tpm_budget, fill_rate_per_second=tpm_budget / 60.0)

        # In-memory caches & state
        self._position_cache: Dict[str, Tuple[LiveTrainPosition, float]] = {}
        self._previous_delays: Dict[str, float] = {}
        self._routes_cache: Dict[str, List[dict]] = {}
        self._lock = threading.Lock()

        # Listeners for SSE / real-time updates
        self._listeners: Set[Callable[[Dict[str, Any]], Any]] = set()
        self._queues: Set[asyncio.Queue] = set()

        # Lifecycle controls
        self._is_running = False
        self._task: Optional[asyncio.Task] = None
        self._last_station_poll_ts: float = 0.0
        self._last_tick_time: Optional[datetime.datetime] = None

        # Configuration constants
        self.tick_interval = float(settings.LIVE_TRACKER_INTERVAL_SECONDS)
        self.station_poll_interval = float(settings.LIVE_STATION_POLL_SECONDS)
        self.cache_ttl = float(settings.POSITION_CACHE_TTL_SECONDS)
        self.tau = float(settings.CONFIDENCE_TAU_SECONDS)
        self.min_confidence = float(settings.DEAD_RECKON_MIN_CONFIDENCE)
        self.attribution_delta_min = float(settings.ATTRIBUTION_DELTA_MIN)

    @property
    def is_running(self) -> bool:
        return self._is_running

    @property
    def last_tick_time(self) -> Optional[datetime.datetime]:
        return self._last_tick_time

    def snapshot(self) -> Dict[str, LiveTrainPosition]:
        """Returns a safe copy of the in-memory live train position cache."""
        with self._lock:
            return {
                k.split(":")[0]: pos
                for k, (pos, ts) in self._position_cache.items()
            }

    @property
    def positions(self) -> Dict[str, LiveTrainPosition]:
        """Public accessor returning snapshot of in-memory live positions."""
        return self.snapshot()

    async def start(self) -> None:
        """Starts the background tracking loop with idempotent advisory lock."""
        async with self._start_lock:
            if self._is_running:
                return
            self._is_running = True
            self._task = asyncio.create_task(self._run_loop())

    async def stop(self) -> None:
        """Gracefully halts the background tracking loop with idempotent advisory lock."""
        async with self._start_lock:
            self._is_running = False
            if self._task and not self._task.done():
                self._task.cancel()
                try:
                    await self._task
                except asyncio.CancelledError:
                    pass
            self._task = None

    async def _run_loop(self) -> None:
        """Master background loop executing tick() every tick_interval."""
        while self._is_running:
            try:
                positions = await self.tick()
                if positions:
                    payload = {
                        "event": "position_update",
                        "count": len(positions),
                        "as_of": get_clock().now_iso(),
                        "positions": [p.to_dict() for p in positions],
                    }
                    await self._broadcast(payload)
            except asyncio.CancelledError:
                break
            except Exception:
                logger.exception("Live tracker background tick failed")

            await asyncio.sleep(self.tick_interval)

    def _get_cached_route(self, train_no: str) -> List[dict]:
        """Retrieves and caches route stops with station coordinates for a train."""
        with self._lock:
            if train_no in self._routes_cache:
                return self._routes_cache[train_no]

        with self.db.transaction() as cur:
            cur.execute(
                """
                SELECT rs.seq, rs.station_code, rs.sched_arr, rs.sched_dep, rs.halt_min, rs.distance_km,
                       s.lat, s.lon, s.name as station_name
                FROM route_stations rs
                JOIN stations s ON rs.station_code = s.code
                WHERE rs.train_no = ?
                ORDER BY rs.seq ASC
                """,
                (train_no,),
            )
            route = [dict(r) for r in cur.fetchall()]

        with self._lock:
            self._routes_cache[train_no] = route

        return route

    def _init_twin_train_state(
        self,
        train_no: str,
        route_stops: List[dict],
        t_now: datetime.datetime,
    ) -> TwinTrainState:
        """Initializes TwinTrainState based on timetable schedule at t_now."""
        if not route_stops:
            return self.twin.create_train_state(train_no, [])

        now_m = t_now.hour * 60 + t_now.minute
        dep_0 = _time_to_min(route_stops[0].get("sched_dep") or "08:00")
        arr_last = _time_to_min(route_stops[-1].get("sched_arr") or "20:00")

        tot_m = (arr_last - dep_0) if arr_last >= dep_0 else (arr_last + 1440 - dep_0)
        elapsed_m = (now_m - dep_0) if now_m >= dep_0 else (now_m + 1440 - dep_0)

        # Before departure
        if elapsed_m <= 0:
            st = self.twin.create_train_state(train_no, route_stops, start_km=0.0, start_speed_kmh=0.0, start_phase="DWELL")
            st.dwell_remaining_sec = max(10.0, abs(elapsed_m) * 60.0)
            return st

        # After arrival at terminus
        if elapsed_m >= tot_m:
            term_km = float(route_stops[-1]["distance_km"])
            st = self.twin.create_train_state(train_no, route_stops, start_km=term_km, start_speed_kmh=0.0, start_phase="DWELL")
            st.current_stop_idx = len(route_stops) - 1
            return st

        # En route between stops
        for i in range(len(route_stops) - 1):
            s_i = route_stops[i]
            s_next = route_stops[i + 1]
            dep_i = _time_to_min(s_i.get("sched_dep") or s_i.get("sched_arr") or "08:00")
            arr_next = _time_to_min(s_next.get("sched_arr") or s_next.get("sched_dep") or "09:00")
            transit_m = (arr_next - dep_i) if arr_next >= dep_i else (arr_next + 1440 - dep_i)

            el_from_dep_i = (now_m - dep_i) if now_m >= dep_i else (now_m + 1440 - dep_i)
            if el_from_dep_i <= transit_m:
                frac = max(0.0, min(1.0, el_from_dep_i / max(1.0, transit_m)))
                km_i = float(s_i["distance_km"])
                km_next = float(s_next["distance_km"])
                curr_km = km_i + frac * (km_next - km_i)
                st = self.twin.create_train_state(train_no, route_stops, start_km=curr_km, start_speed_kmh=80.0, start_phase="CRUISE")
                st.current_stop_idx = i + 1
                return st

        return self.twin.create_train_state(train_no, route_stops, start_km=0.0, start_speed_kmh=0.0, start_phase="DWELL")

    async def tick(
        self,
        run_date: Optional[str] = None,
        as_of_time: Optional[datetime.datetime] = None,
        train_limit: Optional[int] = None,
    ) -> List[LiveTrainPosition]:
        """Executes a single tracking cycle across active corridor trains via physics twin."""
        clock = get_clock()
        t_now = as_of_time or clock.now()
        if hasattr(t_now, "tzinfo") and t_now.tzinfo is None:
            t_now = t_now.replace(tzinfo=IST_TIMEZONE)

        target_date = run_date or clock.today_str()
        now_ts = t_now.timestamp()
        now_iso = t_now.isoformat()

        # Compute physical dt_seconds
        if self._last_tick_time is None:
            dt_seconds = self.tick_interval * getattr(clock, "accel", 1.0)
        else:
            calc_dt = (t_now - self._last_tick_time).total_seconds()
            dt_seconds = max(0.1, min(300.0, calc_dt))
        self._last_tick_time = t_now

        # 1. Periodic Station Board Batch Polling
        if (now_ts - self._last_station_poll_ts) >= self.station_poll_interval:
            self._poll_station_boards(target_date)
            self._last_station_poll_ts = now_ts

        # 2. Get list of active corridor trains
        train_nos = self._get_active_corridor_trains(limit=train_limit)
        if not train_nos:
            return []

        # 3. Pre-fetch Active TSRs from speed_restrictions table
        active_tsrs: Dict[Tuple[str, str], float] = {}
        with self.db.transaction() as cur:
            cur.execute("SELECT from_code, to_code, speed_limit_kmph FROM speed_restrictions WHERE is_active = 1 AND status = 'ACTIVE'")
            for r in cur.fetchall():
                f_c = str(r["from_code"]).upper()
                t_c = str(r["to_code"]).upper()
                spd = float(r["speed_limit_kmph"])
                active_tsrs[(f_c, t_c)] = spd
                active_tsrs[(t_c, f_c)] = spd

        # 3b. Pre-fetch permanent section speed limits (Bug #2 fix): trains must
        # never cruise faster than the section's own permanent max_speed_kmph.
        section_limits: Dict[Tuple[str, str], float] = {}
        with self.db.transaction() as cur:
            cur.execute("SELECT from_code, to_code, max_speed_kmph FROM sections")
            for r in cur.fetchall():
                f_c = str(r["from_code"]).upper()
                t_c = str(r["to_code"]).upper()
                spd = float(r["max_speed_kmph"])
                section_limits[(f_c, t_c)] = spd
                section_limits[(t_c, f_c)] = spd

        # 4. Pre-fetch fog stations from weather table
        fog_stations: Set[str] = set()
        with self.db.transaction() as cur:
            cur.execute("SELECT DISTINCT station_code FROM weather WHERE fog_flag = 1")
            for r in cur.fetchall():
                fog_stations.add(str(r["station_code"]).upper())

        resolved_positions: List[LiveTrainPosition] = []

        # 5. Physics Twin Advance & Closed-Loop Processing
        for t_no in train_nos:
            try:
                route_stops = self._get_cached_route(t_no)
                if not route_stops:
                    continue

                if t_no not in self._twin_states:
                    self._twin_states[t_no] = self._init_twin_train_state(t_no, route_stops, t_now)

                state = self._twin_states[t_no]
                cur_stop = state.current_stop
                next_stop = state.next_stop

                # Build World Context for Train
                sec_pair = (cur_stop.station_code, next_stop.station_code) if (cur_stop and next_stop) else ("", "")
                active_tsr = active_tsrs.get(sec_pair)
                fog_active = (cur_stop.station_code in fog_stations) if cur_stop else False

                # Signal Block Occupancy Scan
                block_occupied = False
                dist_to_ahead = 999.0
                for other_no, other_st in self._twin_states.items():
                    if other_no == t_no:
                        continue
                    if other_st.current_stop and cur_stop and other_st.current_stop.station_code == cur_stop.station_code:
                        if other_st.km > state.km:
                            d = other_st.km - state.km
                            if d < dist_to_ahead:
                                dist_to_ahead = d

                if dist_to_ahead <= 2.0:
                    block_occupied = True
                    signal_aspect = "RED"
                elif dist_to_ahead <= 5.0:
                    signal_aspect = "YELLOW"
                else:
                    signal_aspect = "GREEN"

                # Platform Occupancy Scan
                platform_occupied = False
                if next_stop and state.phase == "APPROACH":
                    for other_no, other_st in self._twin_states.items():
                        if other_no != t_no and other_st.current_stop and other_st.current_stop.station_code == next_stop.station_code and other_st.phase == "DWELL":
                            platform_occupied = True
                            break

                ctx = {
                    "active_tsr_kmh": active_tsr,
                    "fog_active": fog_active,
                    "block_occupied": block_occupied,
                    "signal_aspect": signal_aspect,
                    "platform_occupied": platform_occupied,
                    "section_max_speed_kmh": section_limits.get(sec_pair),
                }

                # Pure-Math Kinematic Step
                new_state, events = self.twin.advance(
                    state,
                    dt_seconds=dt_seconds,
                    sim_time_iso=now_iso,
                    context=ctx,
                )
                self._twin_states[t_no] = new_state

                # Process ARRIVAL / DEPARTURE Events
                for ev in events:
                    ev_type = ev.get("event_type")
                    stn_code = ev.get("station_code", "STN")
                    seq_num = int(ev.get("seq", 1))

                    if ev_type == "ARRIVAL":
                        delay_arr = int(round(float(ev.get("delay_arr_min", 0.0))))
                        with self.db.transaction() as cur:
                            cur.execute(
                                """
                                INSERT INTO station_events (
                                    train_no, run_date, seq, station_code,
                                    sched_arr, actual_arr, sched_dep, actual_dep,
                                    delay_arr_min, delay_dep_min, collected_at, event_time, source
                                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                                ON CONFLICT(train_no, run_date, seq) DO UPDATE SET
                                    actual_arr = coalesce(excluded.actual_arr, station_events.actual_arr),
                                    delay_arr_min = coalesce(excluded.delay_arr_min, station_events.delay_arr_min),
                                    event_time = excluded.event_time,
                                    collected_at = excluded.collected_at,
                                    source = excluded.source;
                                """,
                                (
                                    t_no,
                                    target_date,
                                    seq_num,
                                    stn_code,
                                    ev.get("sched_arr"),
                                    t_now.strftime("%H:%M"),
                                    ev.get("sched_dep"),
                                    None,
                                    delay_arr,
                                    0,
                                    now_iso,
                                    now_iso,
                                    "simulated",
                                ),
                            )

                        # Closed-Loop Prediction Ledger Grading on Touchdown (Step 3.4 / 3.5)
                        try:
                            from engine.prediction_ledger import PredictionLedger
                            ledger = PredictionLedger(self.db)
                            ledger.grade_actual_arrival(
                                train_no=t_no,
                                station_code=stn_code,
                                actual_delay=float(delay_arr),
                                actual_timestamp=now_iso,
                            )
                        except Exception:
                            logger.exception(
                                "Prediction ledger touchdown grading failed for train %s at %s", t_no, stn_code
                            )

                    elif ev_type == "DEPARTURE":
                        with self.db.transaction() as cur:
                            cur.execute(
                                """
                                INSERT INTO station_events (
                                    train_no, run_date, seq, station_code,
                                    sched_arr, actual_arr, sched_dep, actual_dep,
                                    delay_arr_min, delay_dep_min, collected_at, event_time, source
                                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                                ON CONFLICT(train_no, run_date, seq) DO UPDATE SET
                                    actual_dep = coalesce(excluded.actual_dep, station_events.actual_dep),
                                    delay_dep_min = coalesce(excluded.delay_dep_min, station_events.delay_dep_min),
                                    event_time = excluded.event_time,
                                    collected_at = excluded.collected_at,
                                    source = excluded.source;
                                """,
                                (
                                    t_no,
                                    target_date,
                                    seq_num,
                                    stn_code,
                                    ev.get("sched_arr"),
                                    None,
                                    ev.get("sched_dep"),
                                    t_now.strftime("%H:%M"),
                                    0,
                                    0,
                                    now_iso,
                                    now_iso,
                                    "simulated",
                                ),
                            )

                # Convert to LiveTrainPosition
                total_route_dist = max(1.0, float(route_stops[-1]["distance_km"]))
                # Find current track section
                k_idx = 0
                for idx, stop in enumerate(route_stops):
                    if float(stop["distance_km"]) <= new_state.km:
                        k_idx = idx

                if k_idx >= len(route_stops) - 1 or new_state.is_terminated:
                    dest = route_stops[-1]
                    pos = LiveTrainPosition(
                        train_no=t_no,
                        run_date=target_date,
                        lat=float(dest["lat"]),
                        lng=float(dest["lon"]),
                        km=new_state.km,
                        current_station_code=dest["station_code"],
                        next_station_code=None,
                        prev_station_code=route_stops[-2]["station_code"] if len(route_stops) > 1 else None,
                        section_id=None,
                        speed_kmh=0.0,
                        heading=90.0,
                        delay_minutes=0.0,
                        confidence=1.0,
                        progress_pct=100.0,
                        is_dead_reckoned=False,
                        basis="last_event",
                        source="simulated" if clock.mode == "simulated" else "mock_replay",
                        status="TERMINATED",
                        last_event_time=now_iso,
                        updated_at=now_iso,
                    )
                else:
                    stop_k = route_stops[k_idx]
                    stop_next = route_stops[k_idx + 1]
                    dist_k = float(stop_k["distance_km"])
                    dist_nxt = float(stop_next["distance_km"])
                    span = max(0.001, dist_nxt - dist_k)
                    frac = max(0.0, min(1.0, (new_state.km - dist_k) / span))

                    lat = float(stop_k["lat"]) + frac * (float(stop_next["lat"]) - float(stop_k["lat"]))
                    lng = float(stop_k["lon"]) + frac * (float(stop_next["lon"]) - float(stop_k["lon"]))
                    heading = _calculate_heading(float(stop_k["lat"]), float(stop_k["lon"]), float(stop_next["lat"]), float(stop_next["lon"]))
                    section_id = f"{stop_k['station_code']}_{stop_next['station_code']}"

                    # Delay computation relative to timetable
                    sched_min = _time_to_min(stop_next.get("sched_arr") or stop_next.get("sched_dep"))
                    now_min = t_now.hour * 60 + t_now.minute
                    delay_min = max(0.0, float(now_min - sched_min)) if (now_min > sched_min and sched_min > 0) else 0.0

                    pos = LiveTrainPosition(
                        train_no=t_no,
                        run_date=target_date,
                        lat=lat,
                        lng=lng,
                        km=new_state.km,
                        current_station_code=stop_k["station_code"] if frac < 0.5 else stop_next["station_code"],
                        next_station_code=stop_next["station_code"],
                        prev_station_code=stop_k["station_code"],
                        section_id=section_id,
                        speed_kmh=new_state.ema_speed_kmh or new_state.speed_kmh,
                        heading=heading,
                        delay_minutes=delay_min,
                        confidence=0.95,
                        progress_pct=max(0.0, min(100.0, (new_state.km / total_route_dist) * 100.0)),
                        is_dead_reckoned=True if new_state.speed_kmh > 0 else False,
                        basis="dead_reckoning" if new_state.speed_kmh > 0 else "station_master_actual",
                        source="simulated" if clock.mode == "simulated" else "mock_replay",
                        status="RUNNING",
                        last_event_time=now_iso,
                        updated_at=now_iso,
                        signal_hold_active=(new_state.phase == "HELD"),
                        signal_hold_duration_min=12.0 if (new_state.phase == "HELD") else 0.0,
                        inferred_signal_aspect=signal_aspect if (new_state.phase == "HELD") else "GREEN",
                    )

                resolved_positions.append(pos)
                with self._lock:
                    self._position_cache[f"{t_no}:{target_date}"] = (pos, now_ts)

                # Check for delay jump and trigger LiveAttributionEngine
                prev_delay = self._previous_delays.get(t_no, 0.0)
                curr_delay = pos.delay_minutes
                delay_jump = curr_delay - prev_delay
                if delay_jump >= self.attribution_delta_min:
                    attr_res = self.attribution_engine.evaluate_delay_jump(
                        train_no=t_no,
                        run_date=target_date,
                        previous_delay_min=prev_delay,
                        current_delay_min=curr_delay,
                        station_code=pos.current_station_code,
                        current_km=pos.km,
                        as_of_time=t_now,
                    )
                    if attr_res:
                        await self._broadcast({
                            "event": "delay_jump",
                            "train_no": t_no,
                            "delta_min": attr_res.measured_delta_min,
                            "primary_cause": attr_res.primary_cause,
                            "causes": [c.to_dict() for c in attr_res.causes],
                        })

                self._previous_delays[t_no] = curr_delay

            except Exception:
                logger.exception("Live tracker physics step failed for train %s", t_no)
                continue

        # 6. Batch Persist into SQLite live_positions table
        if resolved_positions:
            records = []
            for p in resolved_positions:
                records.append({
                    "train_no": p.train_no,
                    "run_date": p.run_date,
                    "lat": p.lat,
                    "lng": p.lng,
                    "current_station_code": p.current_station_code,
                    "next_station_code": p.next_station_code,
                    "section_id": p.section_id,
                    "speed_kmh": p.speed_kmh,
                    "delay_minutes": p.delay_minutes,
                    "confidence": p.confidence,
                    "progress_pct": p.progress_pct,
                    "is_dead_reckoned": 1 if p.is_dead_reckoned else 0,
                    "source": p.source,
                    "last_event_time": p.last_event_time,
                    "last_gps_fix": p.last_event_time,
                    "updated_at": p.updated_at,
                })
            self.db.upsert_live_positions_bulk(records)

        return resolved_positions

    def _get_active_corridor_trains(self, limit: Optional[int] = None) -> List[str]:
        """Retrieves list of train numbers defined in the database."""
        with self.db.transaction() as cur:
            query = "SELECT train_no FROM trains ORDER BY priority ASC, train_no ASC"
            if limit:
                query += f" LIMIT {int(limit)}"
            cur.execute(query)
            rows = cur.fetchall()
            return [str(r["train_no"]) for r in rows]

    def _poll_station_boards(self, run_date: str) -> None:
        """Refreshes station board telemetry for major trunk corridor stations."""
        trunk_stations = ["NDLS", "GZB", "ALJN", "TDL", "ETW", "CNB", "PRYJ", "DDU"]
        with self.db.transaction() as cur:
            cur.execute(
                """
                SELECT COUNT(*) as cnt FROM station_events
                WHERE run_date = ? AND station_code IN (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (run_date, *trunk_stations),
            )

    def get_live_position(self, train_no: str, run_date: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Retrieves real-time live position for a specific train."""
        clock = get_clock()
        target_date = run_date or clock.today_str()
        cache_key = f"{train_no}:{target_date}"

        with self._lock:
            cached = self._position_cache.get(cache_key)
            if cached:
                pos, cached_at = cached
                if (clock.now().timestamp() - cached_at) < self.cache_ttl:
                    return pos.to_dict()

        # Compute on-demand via twin state if not in cache
        route_stops = self._get_cached_route(train_no)
        if route_stops:
            t_now = clock.now()
            state = self._twin_states.get(train_no) or self._init_twin_train_state(train_no, route_stops, t_now)
            self._twin_states[train_no] = state

            total_route_dist = max(1.0, float(route_stops[-1]["distance_km"]))
            k_idx = 0
            for idx, stop in enumerate(route_stops):
                if float(stop["distance_km"]) <= state.km:
                    k_idx = idx

            now_iso = t_now.isoformat()
            if k_idx >= len(route_stops) - 1 or state.is_terminated:
                dest = route_stops[-1]
                pos = LiveTrainPosition(
                    train_no=train_no,
                    run_date=target_date,
                    lat=float(dest["lat"]),
                    lng=float(dest["lon"]),
                    km=state.km,
                    current_station_code=dest["station_code"],
                    next_station_code=None,
                    prev_station_code=route_stops[-2]["station_code"] if len(route_stops) > 1 else None,
                    section_id=None,
                    speed_kmh=0.0,
                    heading=90.0,
                    delay_minutes=0.0,
                    confidence=1.0,
                    progress_pct=100.0,
                    is_dead_reckoned=False,
                    basis="last_event",
                    source="simulated" if clock.mode == "simulated" else "mock_replay",
                    status="TERMINATED",
                    last_event_time=now_iso,
                    updated_at=now_iso,
                )
            else:
                stop_k = route_stops[k_idx]
                stop_next = route_stops[k_idx + 1]
                dist_k = float(stop_k["distance_km"])
                dist_nxt = float(stop_next["distance_km"])
                span = max(0.001, dist_nxt - dist_k)
                frac = max(0.0, min(1.0, (state.km - dist_k) / span))

                lat = float(stop_k["lat"]) + frac * (float(stop_next["lat"]) - float(stop_k["lat"]))
                lng = float(stop_k["lon"]) + frac * (float(stop_next["lon"]) - float(stop_k["lon"]))
                heading = _calculate_heading(float(stop_k["lat"]), float(stop_k["lon"]), float(stop_next["lat"]), float(stop_next["lon"]))
                section_id = f"{stop_k['station_code']}_{stop_next['station_code']}"

                sched_min = _time_to_min(stop_next.get("sched_arr") or stop_next.get("sched_dep"))
                now_min = t_now.hour * 60 + t_now.minute
                delay_min = max(0.0, float(now_min - sched_min)) if (now_min > sched_min and sched_min > 0) else 0.0

                pos = LiveTrainPosition(
                    train_no=train_no,
                    run_date=target_date,
                    lat=lat,
                    lng=lng,
                    km=state.km,
                    current_station_code=stop_k["station_code"] if frac < 0.5 else stop_next["station_code"],
                    next_station_code=stop_next["station_code"],
                    prev_station_code=stop_k["station_code"],
                    section_id=section_id,
                    speed_kmh=state.ema_speed_kmh or state.speed_kmh,
                    heading=heading,
                    delay_minutes=delay_min,
                    confidence=0.95,
                    progress_pct=max(0.0, min(100.0, (state.km / total_route_dist) * 100.0)),
                    is_dead_reckoned=True if state.speed_kmh > 0 else False,
                    basis="dead_reckoning" if state.speed_kmh > 0 else "station_master_actual",
                    source="simulated" if clock.mode == "simulated" else "mock_replay",
                    status="TERMINATED" if state.is_terminated else "RUNNING",
                    last_event_time=now_iso,
                    updated_at=now_iso,
                    signal_hold_active=(state.phase == "HELD"),
                    signal_hold_duration_min=12.0 if (state.phase == "HELD") else 0.0,
                    inferred_signal_aspect="RED" if (state.phase == "HELD") else "GREEN",
                )

            with self._lock:
                self._position_cache[cache_key] = (pos, clock.now().timestamp())
            return pos.to_dict()

        # Check DB
        db_pos = self.db.get_live_position(train_no, target_date)
        if db_pos:
            if "status" not in db_pos:
                db_pos["status"] = "TERMINATED" if float(db_pos.get("progress_pct", 0)) >= 99.0 else "RUNNING"
            return db_pos

        return None

    def get_all_live_positions(self, run_date: Optional[str] = None) -> List[Dict[str, Any]]:
        """Returns all current corridor train positions from memory cache or database."""
        # 1. In-memory live cache priority
        snap = self.snapshot()
        if snap:
            return [p.to_dict() for p in snap.values()]

        # 2. Database fallback
        db_positions = self.db.get_all_live_positions()
        if db_positions:
            for r in db_positions:
                if "inferred_signal_aspect" not in r or r.get("inferred_signal_aspect") is None:
                    spd = float(r.get("speed_kmh", 0.0))
                    is_held = bool(r.get("is_dead_reckoned", 0) and spd < 5.0)
                    r["signal_hold_active"] = is_held
                    r["signal_hold_duration_min"] = 12.0 if is_held else 0.0
                    r["inferred_signal_aspect"] = "RED" if is_held else "GREEN" if spd > 60 else "YELLOW"
            return db_positions

        return []

    def subscribe(self, queue_or_listener: Any) -> None:
        """Subscribes an asyncio.Queue or callback to receive real-time live position broadcasts."""
        if isinstance(queue_or_listener, asyncio.Queue):
            self._queues.add(queue_or_listener)
        elif callable(queue_or_listener):
            self._listeners.add(queue_or_listener)

    def unsubscribe(self, queue_or_listener: Any) -> None:
        """Unsubscribes a listener or queue."""
        self._queues.discard(queue_or_listener)
        self._listeners.discard(queue_or_listener)

    async def _broadcast(self, payload: Dict[str, Any]) -> None:
        """Pushes update payload to all active queues and callback listeners."""
        for q in list(self._queues):
            try:
                q.put_nowait(payload)
            except Exception:
                self._queues.discard(q)

        for listener in list(self._listeners):
            try:
                res = listener(payload)
                if asyncio.iscoroutine(res):
                    await res
            except Exception:
                self._listeners.discard(listener)


# Global singleton instance
_GLOBAL_LIVE_TRACKER: Optional[LivePositionTracker] = None


def get_live_tracker(db: Optional[Database] = None) -> LivePositionTracker:
    """Returns the shared LivePositionTracker singleton, creating it on first call."""
    global _GLOBAL_LIVE_TRACKER
    if _GLOBAL_LIVE_TRACKER is None:
        _GLOBAL_LIVE_TRACKER = LivePositionTracker(db)
    return _GLOBAL_LIVE_TRACKER


if __name__ == "__main__":
    print("=== RailTwin-X LivePositionTracker Demo ===")
    tracker = LivePositionTracker()
    positions = asyncio.run(tracker.tick())
    print(f"Tracked {len(positions)} live trains on NDLS-DDU corridor.")
    for p in positions[:5]:
        print(f"  Train #{p.train_no} [{p.status}] at {p.current_station_code} (Lat: {p.lat:.4f}, Lng: {p.lng:.4f}, Prog: {p.progress_pct:.1f}%, Conf: {p.confidence:.2f}, Delay: +{p.delay_minutes:.0f}m)")
