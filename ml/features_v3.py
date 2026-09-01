"""RailTwin-X v3 Unified Feature Builder (Phase C1).

24 features, all causal, point-in-time ($t \\le \\text{as\\_of}$), single source of truth
for training dataset materialization and live prediction serving (zero train/serve skew).
"""
from __future__ import annotations

import bisect
import datetime as dt
import json
import math
import sqlite3
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Union

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from data.db import Database, get_db

FEATURE_VERSION = 3
HORIZONS_MIN = (60, 180, 360)
ALPHAS = (0.05, 0.10, 0.25, 0.50, 0.75, 0.90, 0.95)

FEATURE_NAMES_V3: List[str] = [
    "current_delay",
    "delay_velocity",
    "staleness_velocity_interaction",
    "km_remaining",
    "sched_minutes_to_target",
    "sin_hour",
    "cos_hour",
    "day_of_week",
    "target_is_terminus",
    "hist_recency_avg_delay",
    "hist_p90_delay",
    "train_priority",
    "exp_decay_trains_ahead_30k",
    "opposing_conflicts_ahead",
    "max_delay_trains_ahead",
    "route_ahead_section_occupancy_pct",
    "upstream_rake_net_delay",
    "upstream_rake_buffer_consumed_pct",
    "rake_linked",
    "tsr_active_ahead_count",
    "tsr_max_slowdown_pct",
    "winter_fog_dawn_interaction",
    "rain_mm_target",
    "festival_proximity_days",
]

PRIORITY_MAP = {
    "vande_bharat": 5,
    "rajdhani": 5,
    "shatabdi": 5,
    "superfast": 4,
    "express": 3,
    "mail": 3,
    "passenger": 2,
    "emu": 2,
    "local": 2,
    "freight": 1,
}


@dataclass
class FeatureSnapshotV3:
    """Strongly typed 24-dimensional feature snapshot."""
    train_no: str
    run_date: str
    target_station: str
    as_of: str
    horizon_min: float
    y: float
    features: Dict[str, float]

    def to_vector(self) -> List[float]:
        return [float(self.features.get(k, 0.0)) for k in FEATURE_NAMES_V3]

    def to_db_row(self) -> Tuple:
        f = self.features
        return (
            self.train_no,
            self.run_date,
            self.target_station,
            self.as_of,
            self.horizon_min,
            self.y,
            f["current_delay"],
            f["delay_velocity"],
            f["staleness_velocity_interaction"],
            f["km_remaining"],
            f["sched_minutes_to_target"],
            f["sin_hour"],
            f["cos_hour"],
            int(f["day_of_week"]),
            int(f["target_is_terminus"]),
            f["hist_recency_avg_delay"],
            f["hist_p90_delay"],
            int(f["train_priority"]),
            f["exp_decay_trains_ahead_30k"],
            f["opposing_conflicts_ahead"],
            f["max_delay_trains_ahead"],
            f["route_ahead_section_occupancy_pct"],
            f["upstream_rake_net_delay"],
            f["upstream_rake_buffer_consumed_pct"],
            int(f["rake_linked"]),
            int(f["tsr_active_ahead_count"]),
            f["tsr_max_slowdown_pct"],
            f["winter_fog_dawn_interaction"],
            f["rain_mm_target"],
            f["festival_proximity_days"],
        )


class V3FeatureBuilder:
    """Unified Single Source of Truth for Feature Extraction across Training and Serving."""

    def __init__(self, db_path: str = "data/railtwin.db", seeds_dir: str = "data/seeds"):
        self.db_path = db_path
        self.seeds_dir = Path(seeds_dir)
        self.con = sqlite3.connect(db_path)
        self.con.row_factory = sqlite3.Row
        self._load_static()
        self._build_history_cache()
        self._build_weather_cache()
        self._build_events_cache()
        self._spatial_cache: Dict[str, Any] = {}

    def _build_events_cache(self) -> None:
        """Caches all station events grouped by journey and date in memory for lightning fast O(1) feature building."""
        self.events_by_journey: Dict[Tuple[str, str], List[Dict[str, Any]]] = {}
        self.events_by_date: Dict[str, List[Dict[str, Any]]] = {}
        self.events_by_date_minute: Dict[str, Dict[int, List[Dict[str, Any]]]] = {}
        try:
            cur = self.con.execute(
                """
                SELECT se.train_no, se.run_date, se.station_code, se.seq,
                       se.delay_arr_min, se.delay_dep_min,
                       COALESCE(se.event_time, se.collected_at) as event_time,
                       COALESCE(rc.cum_km, rs.distance_km, 0.0) as cum_km
                FROM station_events se
                LEFT JOIN route_cum_km rc ON (se.train_no = rc.train_no AND se.seq = rc.seq)
                LEFT JOIN route_stations rs ON (se.train_no = rs.train_no AND se.seq = rs.seq)
                ORDER BY se.run_date ASC, se.train_no ASC, se.seq ASC
                """
            )
            for r in cur.fetchall():
                ts_raw = str(r[6]).replace("T", " ").split("+")[0].split("Z")[0].strip()
                ts_str = ts_raw if len(ts_raw) == 19 else f"{ts_raw}:00" if len(ts_raw) == 16 else f"{ts_raw} 00:00:00"
                # Parse minute of day
                try:
                    time_part = ts_str.split(" ")[1]
                    h, m = int(time_part.split(":")[0]), int(time_part.split(":")[1])
                    min_of_day = h * 60 + m
                except Exception:
                    min_of_day = 720

                d = {
                    "train_no": str(r[0]),
                    "run_date": str(r[1]),
                    "station_code": str(r[2]),
                    "seq": int(r[3]),
                    "delay_arr_min": r[4],
                    "delay_dep_min": r[5],
                    "event_time": ts_str,
                    "cum_km": float(r[7] or 0.0),
                    "min_of_day": min_of_day,
                }
                self.events_by_journey.setdefault((d["train_no"], d["run_date"]), []).append(d)
                self.events_by_date.setdefault(d["run_date"], []).append(d)
                self.events_by_date_minute.setdefault(d["run_date"], {}).setdefault(min_of_day, []).append(d)
        except Exception:
            pass

    def _load_static(self) -> None:
        """Loads static JSON registries into fast memory indexes."""
        def load_seed(filename: str) -> Any:
            path = self.seeds_dir / filename
            if not path.exists():
                return []
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)

        # Train priorities
        self.priority: Dict[str, int] = {}
        try:
            cur = self.con.execute("SELECT train_no, class FROM trains")
            for r in cur.fetchall():
                cls = str(r[1] or "mail").lower()
                self.priority[str(r[0])] = PRIORITY_MAP.get(cls, 3)
        except Exception:
            trains = load_seed("trains.json")
            for t in trains:
                cls = str(t.get("class", "express")).lower()
                self.priority[str(t["train_no"])] = PRIORITY_MAP.get(cls, 3)

        # Festivals
        self.festivals = load_seed("festivals_v3.json")
        if not self.festivals:
            self.festivals = load_seed("festivals.json")

        # Speed restrictions (TSRs)
        self.tsrs = load_seed("speed_restrictions_v3.json")
        if not self.tsrs:
            self.tsrs = load_seed("speed_restrictions.json")

        # Rake links
        self.rake_links = load_seed("rake_links_expanded.json")
        if not self.rake_links:
            self.rake_links = load_seed("rake_links.json")

        self.rake_out_map: Dict[str, Dict[str, Any]] = {}
        for l in sorted(self.rake_links, key=lambda x: (1 if x.get("source") == "seed" else 0, float(x.get("corr", 0.0)))):
            outg = str(l.get("outgoing") or l.get("outgoing_train"))
            self.rake_out_map[outg] = l

        # Weather station map
        self.weather_map = load_seed("weather_station_map.json")
        if not self.weather_map:
            from ml.geo import build_nearest_station_map
            self.weather_map = build_nearest_station_map()

        # Cumulative distances from route_cum_km table
        self.cum_km_map: Dict[Tuple[str, str], float] = {}
        self.route_seq_map: Dict[Tuple[str, str], int] = {}
        self.route_max_seq: Dict[str, int] = {}
        self.train_routes: Dict[str, List[Tuple[str, int, float]]] = {}

        try:
            cur = self.con.execute("SELECT train_no, station_code, seq, cum_km FROM route_cum_km ORDER BY train_no, seq")
            rows = cur.fetchall()
            if not rows:
                cur = self.con.execute("SELECT train_no, station_code, seq, distance_km FROM route_stations ORDER BY train_no, seq")
                rows = cur.fetchall()

            for r in rows:
                t_no = str(r[0])
                stn = str(r[1])
                seq = int(r[2])
                km = float(r[3] or 0.0)
                self.cum_km_map[(t_no, stn)] = km
                self.route_seq_map[(t_no, stn)] = seq
                self.route_max_seq[t_no] = max(self.route_max_seq.get(t_no, 0), seq)
                self.train_routes.setdefault(t_no, []).append((stn, seq, km))
        except Exception:
            pass

    def _build_history_cache(self) -> None:
        """Builds point-in-time sorted historical delay lists for bisect search."""
        self.hist: Dict[Tuple[str, str], List[Tuple[str, float]]] = {}
        cur = self.con.execute(
            """
            SELECT train_no, station_code, run_date, COALESCE(delay_arr_min, delay_dep_min, 0.0) as delay
            FROM station_events
            WHERE delay_arr_min IS NOT NULL OR delay_dep_min IS NOT NULL
            ORDER BY run_date ASC
            """
        )
        for r in cur.fetchall():
            self.hist.setdefault((str(r["train_no"]), str(r["station_code"])), []).append(
                (str(r["run_date"]), float(r["delay"]))
            )

    def _build_weather_cache(self) -> None:
        """Caches weather observations for fast O(1) timestamp lookup."""
        self.weather_hourly_cache: Dict[Tuple[str, str, int], Tuple[float, float, int, float]] = {}
        try:
            cur = self.con.execute(
                """
                SELECT station_code, date, hour, temperature_2m, precipitation, fog_flag, visibility
                FROM weather_hourly
                """
            )
            for r in cur.fetchall():
                self.weather_hourly_cache[(str(r["station_code"]), str(r["date"]), int(r["hour"]))] = (
                    float(r["temperature_2m"] or 20.0),
                    float(r["precipitation"] or 0.0),
                    int(r["fog_flag"] or 0),
                    float(r["visibility"] or 10000.0),
                )
        except Exception:
            pass

        # Fallback to daily weather table
        self.weather_daily_cache: Dict[Tuple[str, str], Tuple[float, float, int]] = {}
        try:
            cur = self.con.execute(
                """
                SELECT station_code, date, temp, precip_mm, fog_flag
                FROM weather
                """
            )
            for r in cur.fetchall():
                self.weather_daily_cache[(str(r["station_code"]), str(r["date"]))] = (
                    float(r["temp"] or 20.0),
                    float(r["precip_mm"] or 0.0),
                    int(r["fog_flag"] or 0),
                )
        except Exception:
            pass

    def _hist_window(self, train_no: str, station_code: str, run_date: str) -> Tuple[float, float]:
        """Looks up strictly earlier runs via bisect to guarantee zero future data leakage."""
        key = (train_no, station_code)
        if key not in self.hist:
            return 5.0, 8.0

        records = self.hist[key]
        idx = bisect.bisect_left(records, (run_date, -1e9))

        short_past = [d for _, d in records[max(0, idx - 7) : idx]]
        long_past = [d for _, d in records[max(0, idx - 60) : idx]]

        if not short_past:
            return 5.0, 8.0

        arr_short = np.array(short_past, dtype=float)
        arr_long = np.array(long_past, dtype=float)

        weights = np.exp(np.linspace(-0.8, 0.0, len(arr_short)))
        recency_avg = float(np.average(arr_short, weights=weights))
        p90 = float(np.percentile(arr_long, 90))
        return recency_avg, p90

    def cum_km(self, train_no: str, station_code: str) -> float:
        """Returns cumulative kilometer coordinate for a train at a given station."""
        return self.cum_km_map.get((train_no, station_code), 0.0)

    def is_terminus(self, train_no: str, station_code: str) -> int:
        """Returns 1 if station_code is the final destination for train_no."""
        seq = self.route_seq_map.get((train_no, station_code), 0)
        max_seq = self.route_max_seq.get(train_no, 0)
        return 1 if (seq > 0 and seq == max_seq) else 0

    def build_snapshot_features(
        self,
        train_no: str,
        run_date: str,
        target_station: str,
        as_of_dt: dt.datetime,
        sched_arr_target_dt: dt.datetime,
    ) -> Dict[str, float]:
        """Computes all 24 features strictly from events and state where event_time <= as_of."""
        as_of_str = as_of_dt.strftime("%Y-%m-%d %H:%M:%S")
        as_of_date_str = as_of_dt.strftime("%Y-%m-%d")
        as_of_hour = as_of_dt.hour
        as_of_minute = as_of_dt.minute

        # 1. Past observed events on this journey up to as_of
        journey_events = self.events_by_journey.get((train_no, run_date), [])
        obs_events = [e for e in journey_events if e["event_time"] <= as_of_str]

        if obs_events:
            last_event = obs_events[-1]
            last_stn = str(last_event["station_code"])
            current_delay = float(last_event["delay_arr_min"] if last_event["delay_arr_min"] is not None else (last_event["delay_dep_min"] or 0.0))
            last_km = float(last_event["cum_km"] or 0.0)
            last_ts_str = str(last_event["event_time"])

            try:
                last_dt = dt.datetime.fromisoformat(last_ts_str).replace(tzinfo=None)
                staleness_min = max(0.0, (as_of_dt.replace(tzinfo=None) - last_dt).total_seconds() / 60.0)
            except Exception:
                staleness_min = 0.0

            if len(obs_events) >= 2:
                prev_event = obs_events[-2]
                prev_delay = float(prev_event["delay_arr_min"] if prev_event["delay_arr_min"] is not None else (prev_event["delay_dep_min"] or 0.0))
                delay_velocity = current_delay - prev_delay
            else:
                delay_velocity = 0.0
        else:
            last_stn = ""
            current_delay = 0.0
            delay_velocity = 0.0
            staleness_min = 0.0
            last_km = 0.0

        staleness_vel_interaction = staleness_min * abs(delay_velocity)

        # 2. Target distance and lead-time
        target_km = self.cum_km(train_no, target_station)
        km_remaining = max(0.0, target_km - last_km)

        sched_min_to_target = max(
            0.0, (sched_arr_target_dt.replace(tzinfo=None) - as_of_dt.replace(tzinfo=None)).total_seconds() / 60.0
        )

        # 3. Diurnal & Calendar signals
        hour_fraction = as_of_hour + as_of_minute / 60.0
        sin_hour = math.sin(2 * math.pi * hour_fraction / 24.0)
        cos_hour = math.cos(2 * math.pi * hour_fraction / 24.0)
        day_of_week = float(as_of_dt.weekday())

        target_is_term = float(self.is_terminus(train_no, target_station))

        # 4. Historical point-in-time delays
        hist_avg, hist_p90 = self._hist_window(train_no, target_station, run_date)

        # 5. Train Priority
        train_prio = float(self.priority.get(train_no, 3))

        # 6. Forward Spatial Congestion & Conflict Signals
        exp_decay_ahead = 0.0
        opposing_conflicts = 0.0
        max_delay_ahead = 0.0
        route_occ_pct = 0.0

        # Query other active trains near last_km within as_of window from in-memory minute buckets
        day_minutes = self.events_by_date_minute.get(run_date, {})
        as_of_min_of_day = as_of_hour * 60 + as_of_minute
        start_min = max(0, as_of_min_of_day - 45)

        n_ahead = 0
        n_opposing = 0
        delays_ahead = []

        for m_idx in range(start_min, as_of_min_of_day + 1):
            for sr in day_minutes.get(m_idx, []):
                if sr["train_no"] == train_no:
                    continue
                other_km = sr["cum_km"]
                other_delay = float(sr["delay_arr_min"] if sr["delay_arr_min"] is not None else (sr["delay_dep_min"] or 0.0))
                delta_km = other_km - last_km

                if 0.0 < delta_km <= 30.0:
                    n_ahead += 1
                    exp_decay_ahead += math.exp(-delta_km / 10.0)
                    delays_ahead.append(other_delay)
                elif -15.0 <= delta_km <= 0.0:
                    n_opposing += 1

        opposing_conflicts = float(n_opposing)
        max_delay_ahead = float(max(delays_ahead)) if delays_ahead else 0.0
        route_occ_pct = min(100.0, round(100.0 * (n_ahead + n_opposing) / 15.0, 1))

        # 7. Rake Turnaround Linkage
        rake_link = self.rake_out_map.get(train_no)
        if rake_link:
            rake_linked = 1.0
            inc_train = str(rake_link.get("incoming") or rake_link.get("incoming_train"))
            term_stn = str(rake_link.get("terminal") or rake_link.get("station_code") or "NDLS")
            turnaround_buf = float(rake_link.get("turnaround_min", 240.0))

            inc_events = self.events_by_journey.get((inc_train, run_date), [])
            if not inc_events:
                prev_date = (as_of_dt - dt.timedelta(days=1)).strftime("%Y-%m-%d")
                inc_events = self.events_by_journey.get((inc_train, prev_date), [])

            matching = [
                e for e in inc_events
                if e["station_code"] == term_stn and e["event_time"] <= as_of_str
            ]
            if matching:
                last_inc = matching[-1]
                inc_delay = float(last_inc["delay_arr_min"] if last_inc["delay_arr_min"] is not None else (last_inc["delay_dep_min"] or 0.0))
            elif inc_events:
                # If incoming journey happened earlier without terminal stop event recorded, take max observed delay
                delays = [float(e["delay_arr_min"] or e["delay_dep_min"] or 0.0) for e in inc_events if e["event_time"] <= as_of_str]
                inc_delay = float(delays[-1]) if delays else 0.0
            else:
                inc_delay = 0.0

            upstream_rake_net_delay = max(0.0, inc_delay - turnaround_buf)
            upstream_rake_buf_pct = min(100.0, max(0.0, (inc_delay / max(1.0, turnaround_buf)) * 100.0))
        else:
            rake_linked = 0.0
            upstream_rake_net_delay = 0.0
            upstream_rake_buf_pct = 0.0

        # 8. Temporary Speed Restrictions Ahead (TSRs)
        as_of_d = dt.date.fromisoformat(as_of_date_str)
        active_tsrs_ahead = 0
        max_tsr_slowdown = 0.0

        target_seq = self.route_seq_map.get((train_no, target_station), 999)
        cur_seq = self.route_seq_map.get((train_no, last_stn), 0) if obs_events else 0

        route_stations_list = [
            stn for stn, s_idx, _ in self.train_routes.get(train_no, []) if cur_seq <= s_idx <= target_seq
        ]
        route_station_set = set(route_stations_list)

        for tsr in self.tsrs:
            try:
                t_start = dt.date.fromisoformat(tsr["start_date"])
                t_end = dt.date.fromisoformat(tsr["end_date"])
                if t_start <= as_of_d <= t_end:
                    sec_id = tsr.get("section_id", "")
                    # Check if section intersects remaining route
                    parts = sec_id.split("-")
                    if any(p in route_station_set for p in parts):
                        active_tsrs_ahead += 1
                        tsr_spd = float(tsr.get("tsr_speed_kmh", 60.0))
                        norm_spd = float(tsr.get("normal_speed_kmh", 110.0))
                        slowdown = max(0.0, (1.0 - tsr_spd / max(1.0, norm_spd)) * 100.0)
                        max_tsr_slowdown = max(max_tsr_slowdown, slowdown)
            except Exception:
                pass

        # 9. Weather Interactions (Target Station)
        nearest_ws_info = self.weather_map.get(target_station, {"nearest": "NDLS", "dist_km": 0.0})
        ws_code = nearest_ws_info.get("nearest", "NDLS")

        weather_obs = self.weather_hourly_cache.get((ws_code, as_of_date_str, as_of_hour))
        if weather_obs:
            t_temp, t_precip, t_fog_flag, t_vis = weather_obs
        else:
            daily_obs = self.weather_daily_cache.get((ws_code, as_of_date_str), (20.0, 0.0, 0))
            t_temp, t_precip, t_fog_flag = daily_obs
            t_vis = 500.0 if t_fog_flag else 8000.0

        rain_mm_target = float(t_precip)

        # Winter radiative fog dawn interaction (peak in 05-09 IST winter months)
        is_winter = as_of_d.month in (11, 12, 1, 2)
        is_dawn = 5 <= as_of_hour <= 9

        if is_winter and (t_fog_flag == 1 or t_vis < 1000.0):
            fog_dawn_val = 1.0 if is_dawn else 0.4
        elif is_winter and is_dawn and t_temp < 15.0:
            fog_dawn_val = 0.5
        else:
            fog_dawn_val = 0.0

        # 10. Festival Proximity
        min_fest_dist = 60.0
        for fest in self.festivals:
            try:
                f_start = dt.date.fromisoformat(fest["start"])
                f_end = dt.date.fromisoformat(fest["end"])
                if f_start <= as_of_d <= f_end:
                    dist = 0.0
                elif as_of_d < f_start:
                    dist = float((f_start - as_of_d).days)
                else:
                    dist = float((as_of_d - f_end).days)
                min_fest_dist = min(min_fest_dist, dist)
            except Exception:
                pass

        festival_proximity_days = float(min_fest_dist)

        return {
            "current_delay": round(current_delay, 2),
            "delay_velocity": round(delay_velocity, 2),
            "staleness_velocity_interaction": round(staleness_vel_interaction, 2),
            "km_remaining": round(km_remaining, 2),
            "sched_minutes_to_target": round(sched_min_to_target, 2),
            "sin_hour": round(sin_hour, 4),
            "cos_hour": round(cos_hour, 4),
            "day_of_week": day_of_week,
            "target_is_terminus": target_is_term,
            "hist_recency_avg_delay": round(hist_avg, 2),
            "hist_p90_delay": round(hist_p90, 2),
            "train_priority": train_prio,
            "exp_decay_trains_ahead_30k": round(exp_decay_ahead, 4),
            "opposing_conflicts_ahead": opposing_conflicts,
            "max_delay_trains_ahead": round(max_delay_ahead, 2),
            "route_ahead_section_occupancy_pct": route_occ_pct,
            "upstream_rake_net_delay": round(upstream_rake_net_delay, 2),
            "upstream_rake_buffer_consumed_pct": round(upstream_rake_buf_pct, 2),
            "rake_linked": rake_linked,
            "tsr_active_ahead_count": float(active_tsrs_ahead),
            "tsr_max_slowdown_pct": round(max_tsr_slowdown, 2),
            "winter_fog_dawn_interaction": round(fog_dawn_val, 2),
            "rain_mm_target": round(rain_mm_target, 2),
            "festival_proximity_days": festival_proximity_days,
        }
