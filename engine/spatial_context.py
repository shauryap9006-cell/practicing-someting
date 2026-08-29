"""Minute-resolution spatial congestion context for snapshot generation.
Fixes F23: populates trains_ahead_30k, trains_behind_30k, opposing_trains_30k,
sum_delay_trains_ahead_30k, section_occupancy_pct from real trajectory geometry.

Schema adaptation notes (data/schema.sql):
- trains table has NO 'direction' column. Direction inferred from route km ordering:
  is_up = True if route_stations.distance_km increases with seq (origin=0).
  Nearly all Indian Railway corridor trains run in one physical direction; the
  km axis is monotone per route, so sign of (km[last] - km[first]) gives direction.
- station_events uses run_date (YYYY-MM-DD) and collected_at (ISO timestamp IST).
- JOIN key for position: station_events.train_no + station_events.seq (not station_code)
  because multiple trains share stations at different seqs.
"""
from __future__ import annotations

import datetime
from typing import Dict, List, Optional, Tuple

import numpy as np

WINDOW_KM = 30.0
MIN_HEADWAY_KM = 2.0
SECTION_CAPACITY = int(WINDOW_KM / MIN_HEADWAY_KM)   # 15 trains per 30km window
ZERO: Dict[str, object] = dict(
    trains_ahead_30k=0,
    trains_behind_30k=0,
    opposing_trains_30k=0,
    sum_delay_trains_ahead_30k=0.0,
    section_occupancy_pct=0.0,
)


def _infer_direction(km_seq: List[float]) -> bool:
    """True (up-direction) if cumulative km increases along the route.
    Uses first-vs-last km, handles minor reversals safely.
    """
    if len(km_seq) < 2:
        return True
    return km_seq[-1] > km_seq[0]


class TrainTrajectory:
    """Piecewise-linear km(t) for one train-run from its own station events.

    Between event k (departure) and k+1 (arrival): interpolate km by wall clock.
    Carried delay = delay_dep_min of the last departed event (point-in-time safe).
    """

    __slots__ = ("train_no", "is_up", "segs")

    def __init__(self, train_no: str, is_up: bool):
        self.train_no: str = train_no
        self.is_up: bool = is_up
        self.segs: List[Tuple] = []  # (t0, km0, t1, km1, delay_min)

    def add(
        self,
        t0: datetime.datetime,
        km0: float,
        t1: datetime.datetime,
        km1: float,
        delay_min: float,
    ) -> None:
        if t1 > t0 and km1 != km0:
            self.segs.append((t0, km0, t1, km1, float(delay_min)))

    def at(self, t: datetime.datetime) -> Optional[Tuple[float, float]]:
        """Returns (km, delay_min) at time t, or None if outside all segments."""
        for t0, km0, t1, km1, d in self.segs:
            if t0 <= t <= t1:
                f = (t - t0).total_seconds() / (t1 - t0).total_seconds()
                return km0 + f * (km1 - km0), d
        return None


def build_trajectories(db, run_date: str) -> List[TrainTrajectory]:
    """One trajectory per train active on run_date.

    Adapted to real schema:
    - station_events: train_no, seq, delay_dep_min, collected_at (used as event_time fallback)
    - route_stations: train_no, seq, distance_km  (gives km position at each stop)
    - trains: no direction column -> infer from route km ordering

    Point-in-time safe: uses collected_at as the event timestamp (same as snapshot builder).
    """
    with db.transaction() as cur:
        cur.execute(
            """
            SELECT e.train_no,
                   COALESCE(e.event_time, e.collected_at) AS ts,
                   COALESCE(e.delay_dep_min, e.delay_arr_min, 0) AS delay,
                   r.distance_km   AS km,
                   e.seq
            FROM station_events e
            JOIN route_stations r ON e.train_no = r.train_no AND e.seq = r.seq
            WHERE e.run_date = ?
            ORDER BY e.train_no, e.seq
            """,
            (run_date,),
        )
        rows_raw = cur.fetchall()

    if not rows_raw:
        return []

    # Group by train_no, build trajectories
    trajs: List[TrainTrajectory] = []
    cur_traj: Optional[TrainTrajectory] = None
    prev_row = None
    km_by_train: Dict[str, List[float]] = {}

    # First pass: collect km sequences to infer direction per train
    for r in rows_raw:
        t_no = r["train_no"]
        if t_no not in km_by_train:
            km_by_train[t_no] = []
        km_by_train[t_no].append(float(r["km"]))

    # Second pass: build trajectory segments
    for r in rows_raw:
        t_no = r["train_no"]
        if cur_traj is None or cur_traj.train_no != t_no:
            is_up = _infer_direction(km_by_train.get(t_no, []))
            cur_traj = TrainTrajectory(t_no, is_up)
            trajs.append(cur_traj)
            prev_row = None

        if prev_row is not None:
            try:
                # Strip tz-offset so arithmetic is always naive (day_start is naive)
                ts_str = str(r["ts"])
                t1_raw = datetime.datetime.fromisoformat(ts_str)
                if t1_raw.tzinfo is not None:
                    t1_raw = t1_raw.replace(tzinfo=None)

                prev_ts = str(prev_row["ts"])
                t0_raw = datetime.datetime.fromisoformat(prev_ts)
                if t0_raw.tzinfo is not None:
                    t0_raw = t0_raw.replace(tzinfo=None)

                km0 = float(prev_row["km"])
                km1 = float(r["km"])
                d = float(prev_row["delay"])
                cur_traj.add(t0_raw, km0, t1_raw, km1, d)
            except Exception:
                pass
        prev_row = r

    return trajs


class DaySpatialIndex:
    """1440-minute numpy grid of every train's km position for one day.

    Build once per day (~5MB), then every snapshot lookup is a vectorized scan.
    Memory-safe for 18-month backfill: build per day, discard after use.
    """

    def __init__(self, trajs: List[TrainTrajectory], day_start: datetime.datetime):
        n = len(trajs)
        self.idx: Dict[str, int] = {t.train_no: j for j, t in enumerate(trajs)}
        self.is_up: np.ndarray = np.array([t.is_up for t in trajs], dtype=bool)
        self.pos: np.ndarray = np.full((1440, n), np.nan)
        self.delay: np.ndarray = np.zeros((1440, n))

        for j, tr in enumerate(trajs):
            for t0, km0, t1, km1, d in tr.segs:
                m0 = int((t0 - day_start).total_seconds() // 60)
                m1 = int((t1 - day_start).total_seconds() // 60)
                m0, m1 = max(0, m0), min(1439, m1)
                if m1 > m0:
                    fr = np.linspace(0.0, 1.0, m1 - m0 + 1)
                    self.pos[m0 : m1 + 1, j] = km0 + fr * (km1 - km0)
                    self.delay[m0 : m1 + 1, j] = d

    def features(self, minute: int, my_j: Optional[int], my_km: float) -> Dict[str, object]:
        if my_j is None or not (0 <= minute < 1440):
            return dict(ZERO)

        pos = self.pos[minute]
        dl = self.delay[minute]
        ok = ~np.isnan(pos)
        ok[my_j] = False  # exclude self

        if not ok.any():
            return dict(ZERO)

        # delta > 0 means "ahead of me in MY direction of travel"
        # For up-trains: ahead means higher km; for down-trains: ahead means lower km
        my_is_up = bool(self.is_up[my_j])
        direction_sign = np.where(self.is_up, 1.0, -1.0)
        my_sign = 1.0 if my_is_up else -1.0
        delta = direction_sign * (pos - my_km)

        same = self.is_up == my_is_up
        ahead = ok & same & (delta > 0) & (delta <= WINDOW_KM)
        behind = ok & same & (-delta > 0) & (-delta <= WINDOW_KM)
        opposing = ok & ~same & (np.abs(pos - my_km) <= WINDOW_KM)

        n_a = int(ahead.sum())
        n_o = int(opposing.sum())

        return dict(
            trains_ahead_30k=n_a,
            trains_behind_30k=int(behind.sum()),
            opposing_trains_30k=n_o,
            sum_delay_trains_ahead_30k=float(dl[ahead].sum()),
            # occupancy = window load vs physical capacity at min headway
            section_occupancy_pct=round(100.0 * (n_a + n_o) / SECTION_CAPACITY, 1),
        )


class SpatialIndexCache:
    """Thread-safe LRU L1 cache with event-driven version invalidation (Bug 11)."""

    def __init__(self, max_days: int = 7):
        import threading
        self.max_days = max_days
        self._cache: Dict[str, DaySpatialIndex] = {}
        self._versions: Dict[str, int] = {}  # date_str -> ingested event count
        self._access_order: List[str] = []
        self._lock = threading.Lock()

    def get(self, db: Any, date_str: str, current_event_count: Optional[int] = None) -> DaySpatialIndex:
        """Retrieves cached DaySpatialIndex, validating event version to prevent stale cache hits."""
        if current_event_count is None:
            try:
                with db.transaction() as cur:
                    cur.execute("SELECT COUNT(*) as c FROM station_events WHERE run_date = ?", (date_str,))
                    r = cur.fetchone()
                    current_event_count = int(r["c"]) if r else 0
            except Exception:
                current_event_count = 0

        with self._lock:
            # Check version match
            if date_str in self._cache and self._versions.get(date_str) == current_event_count:
                if date_str in self._access_order:
                    self._access_order.remove(date_str)
                self._access_order.append(date_str)
                return self._cache[date_str]

        # Build index outside lock to avoid contention
        day_dt = datetime.date.fromisoformat(date_str)
        day_start = datetime.datetime(day_dt.year, day_dt.month, day_dt.day, 0, 0, 0)
        trajs = build_trajectories(db, date_str)
        idx = DaySpatialIndex(trajs, day_start)

        with self._lock:
            if len(self._cache) >= self.max_days and self._access_order:
                oldest = self._access_order.pop(0)
                self._cache.pop(oldest, None)
                self._versions.pop(oldest, None)
            self._cache[date_str] = idx
            self._versions[date_str] = current_event_count
            if date_str in self._access_order:
                self._access_order.remove(date_str)
            self._access_order.append(date_str)
            return idx

    def invalidate(self, date_str: Optional[str] = None) -> None:
        """Invalidates cache for a specific date or flushes entire cache."""
        with self._lock:
            if date_str is None:
                self._cache.clear()
                self._versions.clear()
                self._access_order.clear()
            else:
                self._cache.pop(date_str, None)
                self._versions.pop(date_str, None)
                if date_str in self._access_order:
                    self._access_order.remove(date_str)


# Global singleton instance for serving
spatial_index_cache = SpatialIndexCache()


