"""RailTwin-X Enriched Operational Context Engine (Pipeline 07, Phase A4).

Aggregates 5 real-time operational context layers for any given train:
1. Weather Layer (temperature, humidity, precipitation, fog_flag, visibility)
2. Speed Restriction (TSR) Layer (active TSRs along route, speed limits, kinematic delay penalty)
3. Turnaround / Incoming Rake Layer (incoming train delay, turnaround deficit, doom status)
4. Platform State Layer (berthing platform, platform holds, conflict status)
5. Spatial Congestion Layer (30km spatial window: trains ahead, sum delay ahead, occupancy pct)

Provides thread-safe in-memory caching with TTL: settings.CONTEXT_CACHE_TTL_SECONDS.
"""

from __future__ import annotations

import datetime
import threading
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from config import settings
from data.db import Database, get_db
from engine.clocks import get_clock, IST_TIMEZONE
from engine.rakes import RakeResolver
from engine.ops import PlatformManager
from engine.spatial_context import spatial_index_cache
from collector.weather import WeatherEngine


@dataclass
class WeatherContext:
    """Micro-weather and atmospheric conditions affecting train operations."""

    station_code: str
    temp_celsius: float
    humidity_pct: float
    precip_mm: float
    fog_flag: int
    visibility_km: float
    is_caution: bool
    summary: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "station_code": self.station_code,
            "temp_celsius": round(self.temp_celsius, 1),
            "humidity_pct": round(self.humidity_pct, 1),
            "precip_mm": round(self.precip_mm, 1),
            "fog_flag": self.fog_flag,
            "visibility_km": round(self.visibility_km, 2),
            "is_caution": self.is_caution,
            "summary": self.summary,
        }


@dataclass
class TSRContextItem:
    """Individual Temporary / Permanent Speed Restriction along train trajectory."""

    from_code: str
    to_code: str
    speed_limit_kmph: int
    cause: str
    start_km: float
    end_km: float
    delay_penalty_min: float
    status: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "from_code": self.from_code,
            "to_code": self.to_code,
            "speed_limit_kmph": self.speed_limit_kmph,
            "cause": self.cause,
            "start_km": round(self.start_km, 1),
            "end_km": round(self.end_km, 1),
            "delay_penalty_min": round(self.delay_penalty_min, 1),
            "status": self.status,
        }


@dataclass
class RakeContext:
    """Same-rake turnaround constraint and downstream cascade status."""

    has_rake_link: bool
    incoming_train: Optional[str]
    incoming_delay_min: int
    turnaround_min: int
    projected_dep_delay_min: int
    turnaround_deficit_min: int
    is_doomed: bool
    official_ntes_status: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "has_rake_link": self.has_rake_link,
            "incoming_train": self.incoming_train,
            "incoming_delay_min": self.incoming_delay_min,
            "turnaround_min": self.turnaround_min,
            "projected_dep_delay_min": self.projected_dep_delay_min,
            "turnaround_deficit_min": self.turnaround_deficit_min,
            "is_doomed": self.is_doomed,
            "official_ntes_status": self.official_ntes_status,
        }


@dataclass
class PlatformContext:
    """Station platform berthing and conflict state."""

    station_code: str
    platform: int
    dwell_min: int
    is_conflicted: bool
    conflict_train: Optional[str]
    conflict_duration_min: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "station_code": self.station_code,
            "platform": self.platform,
            "dwell_min": self.dwell_min,
            "is_conflicted": self.is_conflicted,
            "conflict_train": self.conflict_train,
            "conflict_duration_min": self.conflict_duration_min,
        }


@dataclass
class SpatialCongestionContext:
    """Minute-resolution spatial window load within 30km radius."""

    trains_ahead_30k: int
    trains_behind_30k: int
    opposing_trains_30k: int
    sum_delay_trains_ahead_30k: float
    section_occupancy_pct: float
    is_congested: bool

    def to_dict(self) -> Dict[str, Any]:
        return {
            "trains_ahead_30k": self.trains_ahead_30k,
            "trains_behind_30k": self.trains_behind_30k,
            "opposing_trains_30k": self.opposing_trains_30k,
            "sum_delay_trains_ahead_30k": round(self.sum_delay_trains_ahead_30k, 1),
            "section_occupancy_pct": round(self.section_occupancy_pct, 1),
            "is_congested": self.is_congested,
        }


@dataclass
class TrainContext:
    """Unified 5-layer operational context snapshot for an active train."""

    train_no: str
    run_date: str
    timestamp: str
    current_station_code: Optional[str]
    current_km: float
    weather: WeatherContext
    active_tsrs: List[TSRContextItem]
    rake: RakeContext
    platform: PlatformContext
    spatial: SpatialCongestionContext

    def to_dict(self) -> Dict[str, Any]:
        return {
            "train_no": self.train_no,
            "run_date": self.run_date,
            "timestamp": self.timestamp,
            "current_station_code": self.current_station_code,
            "current_km": round(self.current_km, 2),
            "weather": self.weather.to_dict(),
            "active_tsrs": [tsr.to_dict() for tsr in self.active_tsrs],
            "rake": self.rake.to_dict(),
            "platform": self.platform.to_dict(),
            "spatial": self.spatial.to_dict(),
        }


class ContextEngine:
    """Unified engine for retrieving and caching 5-layer operational train context."""

    def __init__(self, db: Optional[Database] = None):
        self.db = db or get_db()
        self.weather_engine = WeatherEngine(self.db)
        self.rake_resolver = RakeResolver(self.db)
        self.platform_manager = PlatformManager(self.db)
        self._cache: Dict[str, Tuple[TrainContext, float]] = {}
        self._weather_cache: Dict[str, Tuple[WeatherContext, float]] = {}
        self._tsrs_cache: Tuple[List[dict], float] = ([], 0.0)
        self._rake_links_cache: Optional[Dict[str, dict]] = None
        self._routes_cache: Dict[str, List[dict]] = {}
        self._lock = threading.Lock()
        self.cache_ttl = float(settings.CONTEXT_CACHE_TTL_SECONDS)

    def _get_cache_key(self, train_no: str, run_date: str, station_code: Optional[str]) -> str:
        return f"{train_no}:{run_date}:{station_code or 'UNKNOWN'}"

    def _get_cached_route(self, train_no: str) -> List[dict]:
        """Loads and caches route stations for a train."""
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

    def enrich(
        self,
        train_no: str,
        run_date: Optional[str] = None,
        current_station: Optional[str] = None,
        current_km: Optional[float] = None,
        as_of_time: Optional[datetime.datetime] = None,
        force_refresh: bool = False,
    ) -> TrainContext:
        """Enriches a train with 5-layer operational context (Phase A4 requirement)."""
        return self.get_train_context(
            train_no=train_no,
            run_date=run_date,
            current_station_code=current_station,
            current_km=current_km,
            as_of_time=as_of_time,
            force_refresh=force_refresh,
        )

    def get_train_context(
        self,
        train_no: str,
        run_date: Optional[str] = None,
        current_station_code: Optional[str] = None,
        current_km: Optional[float] = None,
        as_of_time: Optional[datetime.datetime] = None,
        force_refresh: bool = False,
    ) -> TrainContext:
        """Fetches complete 5-layer context for a train, using TTL cache when valid."""
        clock = get_clock()
        t_now = as_of_time or clock.now()
        if hasattr(t_now, "tzinfo") and t_now.tzinfo is None:
            t_now = t_now.replace(tzinfo=IST_TIMEZONE)

        target_date = run_date or clock.today_str()
        cache_key = self._get_cache_key(train_no, target_date, current_station_code)
        now_ts = t_now.timestamp()

        if not force_refresh:
            with self._lock:
                cached_entry = self._cache.get(cache_key)
                if cached_entry:
                    ctx, cached_at = cached_entry
                    if (now_ts - cached_at) < self.cache_ttl:
                        return ctx

        # 1. Resolve Route Geometry & Station
        resolved_stn, resolved_km = self._resolve_station_and_km(train_no, current_station_code, current_km)

        # Layer 1: Weather
        weather_ctx = self._enrich_weather(resolved_stn, target_date, t_now)

        # Layer 2: TSRs
        tsrs_ctx = self._enrich_tsrs(train_no, resolved_stn, resolved_km)

        # Layer 3: Rake Turnaround Doom
        rake_ctx = self._enrich_rake(train_no, target_date)

        # Layer 4: Platform Berthing & Conflicts
        platform_ctx = self._enrich_platform(train_no, resolved_stn, target_date)

        # Layer 5: Spatial Congestion
        spatial_ctx = self._enrich_spatial(train_no, target_date, resolved_km, t_now)

        ctx = TrainContext(
            train_no=train_no,
            run_date=target_date,
            timestamp=t_now.isoformat(),
            current_station_code=resolved_stn,
            current_km=resolved_km,
            weather=weather_ctx,
            active_tsrs=tsrs_ctx,
            rake=rake_ctx,
            platform=platform_ctx,
            spatial=spatial_ctx,
        )

        with self._lock:
            self._cache[cache_key] = (ctx, now_ts)

        return ctx

    def _resolve_station_and_km(
        self, train_no: str, station_code: Optional[str], km: Optional[float]
    ) -> Tuple[str, float]:
        """Resolves realistic station code and cumulative kilometer distance for the train."""
        if station_code and km is not None:
            return station_code, float(km)

        route = self._get_cached_route(train_no)
        if not route:
            return station_code or "NDLS", km if km is not None else 0.0

        if station_code:
            for r in route:
                if r["station_code"] == station_code:
                    return station_code, float(r["distance_km"])

        # Default to first stop
        first = route[0]
        return first["station_code"], float(first["distance_km"])

    def _enrich_weather(
        self, station_code: str, date_str: str, as_of: datetime.datetime
    ) -> WeatherContext:
        """Enriches station micro-weather from weather_hourly / weather or forecast fallback."""
        w_cache_key = f"{station_code}:{date_str}:{as_of.hour}"
        now_ts = as_of.timestamp()
        with self._lock:
            if w_cache_key in self._weather_cache:
                w_ctx, cached_ts = self._weather_cache[w_cache_key]
                if (now_ts - cached_ts) < (settings.WEATHER_CACHE_MINUTES * 60):
                    return w_ctx

        with self.db.transaction() as cur:
            # 1. Try hourly micro-weather table first
            cur.execute(
                """
                SELECT temperature_2m, relative_humidity_2m, precipitation, visibility, fog_flag
                FROM weather_hourly
                WHERE station_code = ? AND date = ?
                ORDER BY ABS(hour - ?) ASC LIMIT 1
                """,
                (station_code, date_str, as_of.hour),
            )
            hourly_row = cur.fetchone()

            if hourly_row:
                temp = float(hourly_row["temperature_2m"] or 25.0)
                humid = float(hourly_row["relative_humidity_2m"] or 60.0)
                precip = float(hourly_row["precipitation"] or 0.0)
                raw_vis = hourly_row["visibility"]
                vis_km = float(raw_vis / 1000.0) if raw_vis is not None else (0.8 if hourly_row["fog_flag"] else 10.0)
                fog = int(hourly_row["fog_flag"] or 0)
            else:
                # 2. Try daily weather summary table
                cur.execute(
                    """
                    SELECT temp, humidity, precip_mm, fog_flag
                    FROM weather
                    WHERE station_code = ? AND date = ?
                    """,
                    (station_code, date_str),
                )
                daily_row = cur.fetchone()

                if daily_row:
                    temp = float(daily_row["temp"] or 25.0)
                    humid = float(daily_row["humidity"] or 60.0)
                    precip = float(daily_row["precip_mm"] or 0.0)
                    fog = int(daily_row["fog_flag"] or 0)
                    vis_km = 0.6 if fog else 10.0
                else:
                    # Deterministic offline fallback based on month
                    is_winter = as_of.month in (11, 12, 1, 2)
                    temp = 14.5 if is_winter else 29.0
                    humid = 88.0 if is_winter else 55.0
                    precip = 0.0
                    fog = 1 if is_winter and (temp < settings.FOG_MAX_TEMP_CELSIUS and humid > settings.FOG_MIN_HUMIDITY_PERCENT) else 0
                    vis_km = 0.5 if fog else 10.0

        is_caution = bool(
            fog == 1
            or precip >= settings.HEAVY_RAIN_THRESHOLD_MM
            or (temp < settings.FOG_MAX_TEMP_CELSIUS and humid > settings.FOG_MIN_HUMIDITY_PERCENT)
        )

        if fog == 1:
            summary = f"Dense Fog (Vis: {vis_km:.1f}km, Temp: {temp:.1f}°C, Hum: {humid:.0f}%)"
        elif precip >= settings.HEAVY_RAIN_THRESHOLD_MM:
            summary = f"Heavy Rain ({precip:.1f}mm, Caution Speed Mandatory)"
        elif precip > 0.0:
            summary = f"Light Rain ({precip:.1f}mm, Clear Visibility)"
        else:
            summary = f"Clear Weather (Temp: {temp:.1f}°C, Hum: {humid:.0f}%)"

        w_res = WeatherContext(
            station_code=station_code,
            temp_celsius=temp,
            humidity_pct=humid,
            precip_mm=precip,
            fog_flag=fog,
            visibility_km=vis_km,
            is_caution=is_caution,
            summary=summary,
        )

        with self._lock:
            self._weather_cache[w_cache_key] = (w_res, now_ts)

        return w_res

    def _get_active_tsrs_cached(self) -> List[dict]:
        now_ts = datetime.datetime.now().timestamp()
        with self._lock:
            cached_tsrs, cached_at = self._tsrs_cache
            if cached_tsrs and (now_ts - cached_at) < 30.0:
                return cached_tsrs

        with self.db.transaction() as cur:
            cur.execute(
                """
                SELECT from_code, to_code, speed_limit_kmph, cause, start_km, end_km, status
                FROM speed_restrictions
                WHERE (status = 'ACTIVE' OR is_active = 1)
                """
            )
            rows = [dict(r) for r in cur.fetchall()]

        with self._lock:
            self._tsrs_cache = (rows, now_ts)
        return rows

    def _enrich_tsrs(
        self, train_no: str, current_station_code: str, current_km: float
    ) -> List[TSRContextItem]:
        """Identifies active speed restrictions along the train route and calculates delay penalties."""
        rows = self._get_active_tsrs_cached()
        route_rows = self._get_cached_route(train_no)
        route_stns = {r["station_code"] for r in route_rows}
        tsrs: List[TSRContextItem] = []

        for r in rows:
            from_c = r["from_code"]
            to_c = r["to_code"]
            v_tsr = max(10, int(r["speed_limit_kmph"]))
            v_norm = 110.0  # Normal line speed in km/h

            # Check if TSR is on this train's route or adjoining sections
            if from_c in route_stns or to_c in route_stns or from_c == current_station_code:
                start_k = float(r["start_km"]) if r["start_km"] else current_km
                end_k = float(r["end_km"]) if r["end_km"] else (start_k + 5.0)
                length_km = max(1.0, abs(end_k - start_k))

                # Kinematic delay penalty: Delta_t = Length * (1/v_tsr - 1/v_norm) * 60 minutes
                delay_penalty = max(0.5, length_km * (1.0 / v_tsr - 1.0 / v_norm) * 60.0)

                tsrs.append(
                    TSRContextItem(
                        from_code=from_c,
                        to_code=to_c,
                        speed_limit_kmph=v_tsr,
                        cause=r["cause"] or "Track Maintenance",
                        start_km=start_k,
                        end_km=end_k,
                        delay_penalty_min=delay_penalty,
                        status=r["status"] or "ACTIVE",
                    )
                )

        return tsrs

    def _enrich_rake(self, train_no: str, date_str: str) -> RakeContext:
        """Evaluates same-rake incoming link turnaround delay and doom probability."""
        with self.db.transaction() as cur:
            cur.execute(
                """
                SELECT rl.incoming_train, rl.outgoing_train, rl.station_code, rl.turnaround_min
                FROM rake_links rl
                WHERE rl.outgoing_train = ?
                """,
                (train_no,),
            )
            link = cur.fetchone()

        if not link:
            return RakeContext(
                has_rake_link=False,
                incoming_train=None,
                incoming_delay_min=0,
                turnaround_min=0,
                projected_dep_delay_min=0,
                turnaround_deficit_min=0,
                is_doomed=False,
                official_ntes_status="NOT_LINKED",
            )

        in_t = link["incoming_train"]
        stn = link["station_code"]
        turnaround = int(link["turnaround_min"] or 240)

        # Query incoming train actual arrival delay at interchange station
        with self.db.transaction() as cur:
            cur.execute(
                """
                SELECT sched_arr, actual_arr, delay_arr_min
                FROM station_events
                WHERE train_no = ? AND station_code = ? AND run_date = ?
                ORDER BY seq DESC LIMIT 1
                """,
                (in_t, stn, date_str),
            )
            in_ev = cur.fetchone()

            cur.execute(
                """
                SELECT sched_dep FROM route_stations WHERE train_no = ? AND station_code = ?
                """,
                (train_no, stn),
            )
            out_route = cur.fetchone()

        in_delay = int(in_ev["delay_arr_min"]) if in_ev and in_ev["delay_arr_min"] is not None else 0
        in_sched_arr = in_ev["sched_arr"] if in_ev and in_ev["sched_arr"] else "08:00"
        out_sched_dep = out_route["sched_dep"] if out_route and out_route["sched_dep"] else "12:00"

        # Calculate scheduled slack
        if ":" in in_sched_arr and ":" in out_sched_dep:
            sh_in, sm_in = [int(x) for x in in_sched_arr.split(":")[:2]]
            sh_out, sm_out = [int(x) for x in out_sched_dep.split(":")[:2]]
            sched_buffer = (sh_out * 60 + sm_out) - (sh_in * 60 + sm_in)
            if sched_buffer < 0:
                sched_buffer += 1440
        else:
            sched_buffer = turnaround

        turnaround_deficit = max(0, in_delay - max(0, sched_buffer - turnaround))
        is_doomed = turnaround_deficit >= 15

        return RakeContext(
            has_rake_link=True,
            incoming_train=in_t,
            incoming_delay_min=in_delay,
            turnaround_min=turnaround,
            projected_dep_delay_min=turnaround_deficit,
            turnaround_deficit_min=turnaround_deficit,
            is_doomed=is_doomed,
            official_ntes_status="ON TIME" if not is_doomed else "DOOMED_DELAY",
        )

    def _enrich_platform(
        self, train_no: str, station_code: str, date_str: str
    ) -> PlatformContext:
        """Determines platform berthing, scheduled dwell, and platform conflict status."""
        try:
            blocks, conflicts = self.platform_manager.get_station_gantt(station_code, date_str)
            target_block = next((b for b in blocks if b.train_no == train_no), None)
            is_conflicted = target_block.is_conflicted if target_block else False
            platform = target_block.platform if target_block else 1
            dwell = target_block.dwell_min if target_block else 15

            conflict_train = None
            conflict_dur = 0
            if is_conflicted:
                c = next((x for x in conflicts if x.train_1 == train_no or x.train_2 == train_no), None)
                if c:
                    conflict_train = c.train_2 if c.train_1 == train_no else c.train_1
                    conflict_dur = c.overlap_duration_min
        except Exception:
            platform = (abs(hash((train_no, settings.DEFAULT_PLATFORM_HASH_SEED))) % 8) + 1
            dwell = settings.DEFAULT_PLATFORM_DWELL_BUFFER_MINUTES
            is_conflicted = False
            conflict_train = None
            conflict_dur = 0

        return PlatformContext(
            station_code=station_code,
            platform=platform,
            dwell_min=dwell,
            is_conflicted=is_conflicted,
            conflict_train=conflict_train,
            conflict_duration_min=conflict_dur,
        )

    def _enrich_spatial(
        self, train_no: str, date_str: str, current_km: float, as_of: datetime.datetime
    ) -> SpatialCongestionContext:
        """Calculates spatial window load within 30km from DaySpatialIndex."""
        try:
            minute_of_day = min(1439, max(0, as_of.hour * 60 + as_of.minute))
            idx = spatial_index_cache.get(self.db, date_str)
            j = idx.idx.get(train_no)
            feats = idx.features(minute_of_day, j, current_km)

            ahead = int(feats.get("trains_ahead_30k", 0))
            behind = int(feats.get("trains_behind_30k", 0))
            opp = int(feats.get("opposing_trains_30k", 0))
            delay_ahead = float(feats.get("sum_delay_trains_ahead_30k", 0.0))
            occupancy = float(feats.get("section_occupancy_pct", 0.0))
            is_congested = (occupancy >= 70.0 or ahead >= 2 or delay_ahead >= 20.0)

            return SpatialCongestionContext(
                trains_ahead_30k=ahead,
                trains_behind_30k=behind,
                opposing_trains_30k=opp,
                sum_delay_trains_ahead_30k=delay_ahead,
                section_occupancy_pct=occupancy,
                is_congested=is_congested,
            )
        except Exception:
            return SpatialCongestionContext(
                trains_ahead_30k=0,
                trains_behind_30k=0,
                opposing_trains_30k=0,
                sum_delay_trains_ahead_30k=0.0,
                section_occupancy_pct=0.0,
                is_congested=False,
            )

    def invalidate_cache(self, train_no: Optional[str] = None) -> None:
        """Invalidates context cache entries for a specific train or entire cache."""
        with self._lock:
            if train_no is None:
                self._cache.clear()
            else:
                prefix = f"{train_no}:"
                keys_to_remove = [k for k in self._cache if k.startswith(prefix)]
                for k in keys_to_remove:
                    self._cache.pop(k, None)


# Global singleton instance
_GLOBAL_CONTEXT_ENGINE: Optional[ContextEngine] = None


def get_context_engine(db: Optional[Database] = None) -> ContextEngine:
    """Returns the shared ContextEngine instance."""
    global _GLOBAL_CONTEXT_ENGINE
    if db is not None:
        return ContextEngine(db)
    if _GLOBAL_CONTEXT_ENGINE is None:
        _GLOBAL_CONTEXT_ENGINE = ContextEngine()
    return _GLOBAL_CONTEXT_ENGINE


if __name__ == "__main__":
    print("=== RailTwin-X ContextEngine Demo ===")
    ce = ContextEngine()
    ctx = ce.get_train_context("12301", current_station_code="CNB", current_km=440.0)
    print(f"Enriched Context for Train #12301 at {ctx.current_station_code} (KM {ctx.current_km}):")
    print(f"  - Weather: {ctx.weather.summary}")
    print(f"  - Active TSRs: {len(ctx.active_tsrs)} items")
    print(f"  - Rake Doom: {ctx.rake.is_doomed} (Deficit: {ctx.rake.turnaround_deficit_min}m)")
    print(f"  - Platform: PF {ctx.platform.platform} (Conflicted: {ctx.platform.is_conflicted})")
    print(f"  - Spatial Congestion: {ctx.spatial.trains_ahead_30k} ahead, Occ: {ctx.spatial.section_occupancy_pct}%")
