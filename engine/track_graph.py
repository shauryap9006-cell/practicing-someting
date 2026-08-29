"""RailTwin-X Track Context Graph & Topology Engine (Phase G1).

Constructs the spatial topology of stations and track sections to extract
leakage-free track context features for ML brain models:
1. trains_ahead_30k / trains_behind_30k (same-direction trains within 30 km)
2. opposing_trains_30k (opposing trains on single-line sections within 30 km)
3. min_predicted_headway_next_station (time headway to preceding train at next stop)
4. sum_delay_trains_ahead_30k (downstream congestion pressure)
5. section_occupancy_pct (block occupancy fraction)
"""

from __future__ import annotations

import datetime
import math
from typing import Dict, List, Optional, Tuple
import networkx as nx

from data.db import Database, get_db


class TrackGraph:
    """Deterministic spatial track topology and train spatial context extractor."""

    def __init__(self, db: Optional[Database] = None):
        self.db = db or get_db()
        self.graph = nx.DiGraph()
        self._sections: Dict[Tuple[str, str], dict] = {}
        self._stations: Dict[str, dict] = {}
        self._routes: Dict[str, List[dict]] = {}
        self._routes_dest: Dict[str, str] = {}
        self._routes_sched_min: Dict[str, Dict[str, int]] = {}
        self._load_topology()

    def _load_topology(self) -> None:
        """Loads static stations, physical sections, and train route topologies."""
        with self.db.transaction() as cur:
            # 1. Stations
            cur.execute("SELECT code, name, lat, lon, platforms, is_junction FROM stations")
            for stn in cur.fetchall():
                c = stn["code"]
                self._stations[c] = dict(stn)
                self.graph.add_node(
                    c,
                    name=stn["name"],
                    lat=float(stn["lat"]),
                    lon=float(stn["lon"]),
                    platforms=int(stn["platforms"]),
                    is_junction=int(stn["is_junction"]),
                )

            # 2. Sections
            cur.execute("SELECT from_code, to_code, distance_km, single_line, max_speed_kmph FROM sections")
            for sec in cur.fetchall():
                u, v = sec["from_code"], sec["to_code"]
                sec_dict = {
                    "from_code": u,
                    "to_code": v,
                    "distance_km": float(sec["distance_km"]),
                    "single_line": bool(sec["single_line"]),
                    "max_speed_kmph": int(sec["max_speed_kmph"]),
                }
                self._sections[(u, v)] = sec_dict
                self.graph.add_edge(u, v, **sec_dict)

            # 3. Routes
            cur.execute(
                """
                SELECT rs.train_no, rs.seq, rs.station_code, rs.sched_arr, rs.sched_dep,
                       rs.distance_km, t.priority, t.class as train_class
                FROM route_stations rs
                JOIN trains t ON rs.train_no = t.train_no
                ORDER BY rs.train_no, rs.seq
                """
            )
            for r in cur.fetchall():
                t_no = r["train_no"]
                if t_no not in self._routes:
                    self._routes[t_no] = []
                self._routes[t_no].append(dict(r))

        for t_no, stops in self._routes.items():
            if stops:
                self._routes_dest[t_no] = stops[-1]["station_code"]
                sched_map: Dict[str, int] = {}
                for st in stops:
                    sa = st.get("sched_arr")
                    if sa and ":" in sa:
                        try:
                            h, m = map(int, sa.split(":"))
                            sched_map[st["station_code"]] = h * 60 + m
                        except Exception:
                            pass
                self._routes_sched_min[t_no] = sched_map

    def get_route(self, train_no: str) -> List[dict]:
        """Returns ordered sequence of stops for a given train."""
        return self._routes.get(train_no, [])

    def get_next_k_stations(self, train_no: str, current_seq: int, k: int = 5) -> List[dict]:
        """Returns the next K upcoming stations along the train's route."""
        route = self.get_route(train_no)
        if not route or current_seq >= len(route):
            return []
        return route[current_seq : current_seq + k]

    def get_section_info(self, from_code: str, to_code: str) -> dict:
        """Retrieves physical section properties between two stations."""
        if (from_code, to_code) in self._sections:
            return self._sections[(from_code, to_code)]
        if (to_code, from_code) in self._sections:
            rev = dict(self._sections[(to_code, from_code)])
            rev["from_code"], rev["to_code"] = from_code, to_code
            return rev
        return {
            "from_code": from_code,
            "to_code": to_code,
            "distance_km": 50.0,
            "single_line": False,
            "max_speed_kmph": 110,
        }

    def compute_track_context_features(
        self,
        train_no: str,
        current_seq: int,
        target_seq: int,
        run_date_str: str,
        query_time_iso: str,
        current_delay: float,
    ) -> Dict[str, float]:
        """Computes deterministic, point-in-time spatial track context features.

        Strict leakage safety: Only examines events/positions known at or before query_time.
        """
        route = self.get_route(train_no)
        if not route or current_seq < 1 or current_seq > len(route):
            return {
                "trains_ahead_30k": 0.0,
                "trains_behind_30k": 0.0,
                "opposing_trains_30k": 0.0,
                "min_predicted_headway_next_station": 60.0,
                "sum_delay_trains_ahead_30k": 0.0,
                "section_occupancy_pct": 0.0,
            }

        curr_stop = route[current_seq - 1]
        curr_km = float(curr_stop["distance_km"])
        curr_stn = curr_stop["station_code"]
        next_stn = route[current_seq]["station_code"] if current_seq < len(route) else curr_stn
        sec_info = self.get_section_info(curr_stn, next_stn)
        is_single_line = sec_info["single_line"]

        # Pre-cache events by date for sub-millisecond point-in-time filtering
        if not hasattr(self, "_events_cache"):
            self._events_cache: Dict[str, List[dict]] = {}

        if run_date_str not in self._events_cache:
            with self.db.transaction() as cur:
                cur.execute(
                    """
                    SELECT train_no, seq, station_code, delay_arr_min, sched_arr, actual_arr, collected_at
                    FROM station_events
                    WHERE run_date = ?
                    ORDER BY collected_at ASC
                    """,
                    (run_date_str,),
                )
                self._events_cache[run_date_str] = [dict(r) for r in cur.fetchall()]

        date_events = self._events_cache[run_date_str]
        latest_by_train: Dict[str, dict] = {}
        for ev in date_events:
            if ev["collected_at"] > query_time_iso:
                break
            if ev["train_no"] != train_no:
                latest_by_train[ev["train_no"]] = ev

        other_trains = list(latest_by_train.values())

        trains_ahead = 0
        trains_behind = 0
        opposing_trains = 0
        sum_delay_ahead = 0.0
        headways_next_stn: List[float] = []

        # Reference scheduled arrival at next station
        sched_arr_next = route[current_seq]["sched_arr"] if current_seq < len(route) else curr_stop["sched_arr"]
        try:
            h_ref, m_ref = map(int, sched_arr_next.split(":"))
            ref_min_of_day = h_ref * 60 + m_ref
        except Exception:
            ref_min_of_day = 480

        my_dest = self._routes_dest.get(train_no, route[-1]["station_code"])

        for ot in other_trains:
            o_no = ot["train_no"]
            o_route = self.get_route(o_no)
            o_seq = int(ot["seq"])
            if not o_route or o_seq < 1 or o_seq > len(o_route):
                continue

            o_stop = o_route[o_seq - 1]
            o_km = float(o_stop["distance_km"])
            o_delay = float(ot["delay_arr_min"] or 0.0)

            # Check if trains share corridor direction
            same_direction = (self._routes_dest.get(o_no) == my_dest)

            if same_direction:
                dist_delta = o_km - curr_km
                if 0.0 < dist_delta <= 30.0:
                    trains_ahead += 1
                    sum_delay_ahead += max(0.0, o_delay)
                elif -30.0 <= dist_delta < 0.0:
                    trains_behind += 1

                # Check headway at shared next station
                o_sched_map = self._routes_sched_min.get(o_no, {})
                if next_stn in o_sched_map:
                    o_min_of_day = o_sched_map[next_stn] + int(round(o_delay))
                    gap = abs(ref_min_of_day - o_min_of_day)
                    headways_next_stn.append(float(gap))
            else:
                # Opposing train
                if is_single_line:
                    if ot["station_code"] in (curr_stn, next_stn):
                        opposing_trains += 1

        min_headway = min(headways_next_stn) if headways_next_stn else 60.0
        # Nominal section capacity is ~4 trains per 30 km block
        total_in_section = trains_ahead + trains_behind + (1 if opposing_trains > 0 else 0)
        section_occupancy = min(1.0, float(total_in_section) / 4.0)

        return {
            "trains_ahead_30k": float(trains_ahead),
            "trains_behind_30k": float(trains_behind),
            "opposing_trains_30k": float(opposing_trains),
            "min_predicted_headway_next_station": float(min_headway),
            "sum_delay_trains_ahead_30k": float(sum_delay_ahead),
            "section_occupancy_pct": float(section_occupancy),
        }

