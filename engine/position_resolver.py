"""RailTwin-X Probabilistic Position Resolver (F19, F20).

Resolves soft position probability distributions over route stops when exact GPS/feed
is intermittent or noisy. Computes posterior P(seq=k) using dead-reckoning recency decay,
schedule priors, and fuses actual human operational events (ad_events set-in/set-out)
as dominant evidence.
"""

from __future__ import annotations

import datetime
from typing import Dict, List, Optional, Tuple, Any
import numpy as np

from data.db import Database, get_db
from engine.clocks import get_clock, IST_TIMEZONE


class PositionRecord:
    """Encapsulates the resolved soft train position and uncertainty metrics."""

    def __init__(
        self,
        mode_seq: int,
        station_code: str,
        confidence: float,
        basis: str,
        age_seconds: float,
        source: str,
        posterior_probs: Dict[int, float],
    ):
        self.mode_seq = mode_seq
        self.station_code = station_code
        self.confidence = float(min(1.0, max(0.0, confidence)))
        self.basis = basis
        self.age_seconds = float(max(0.0, age_seconds))
        self.source = source
        self.posterior_probs = posterior_probs

    def top_k(self, k: int = 3) -> List[Tuple[int, float]]:
        """Returns the top-K highest-probability candidate stops [(seq, prob), ...]."""
        sorted_candidates = sorted(self.posterior_probs.items(), key=lambda x: x[1], reverse=True)
        return [(int(seq), float(p)) for seq, p in sorted_candidates[:k]]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "mode_seq": self.mode_seq,
            "station_code": self.station_code,
            "confidence": round(self.confidence, 3),
            "basis": self.basis,
            "age_seconds": round(self.age_seconds, 1),
            "source": self.source,
            "posterior_probs": {int(k): round(v, 4) for k, v in self.posterior_probs.items()},
            "candidates": [[int(s), round(p, 4)] for s, p in self.top_k(3)],
        }


class PositionResolver:
    """Probabilistic Bayesian position estimation engine for trains along a route."""

    def __init__(self, db: Optional[Database] = None):
        self.db = db or get_db()

    def resolve_train_position(
        self,
        train_no: str,
        route_stops: List[Dict[str, Any]],
        as_of_time: Optional[datetime.datetime] = None,
    ) -> PositionRecord:
        """Computes posterior P(seq=k) over candidate stops along the train route enforcing point-in-time."""
        clock = get_clock()
        t_now = as_of_time or clock.now()
        if hasattr(t_now, "tzinfo") and t_now.tzinfo is None:
            t_now = t_now.replace(tzinfo=IST_TIMEZONE)
        
        now_iso = t_now.isoformat()

        n_stops = len(route_stops)
        if n_stops == 0:
            return PositionRecord(
                mode_seq=1,
                station_code="UNKNOWN",
                confidence=0.0,
                basis="schedule_only",
                age_seconds=9999.0,
                source="inferred",
                posterior_probs={1: 1.0},
            )

        seq_to_stop = {int(r["seq"]): r for r in route_stops}
        min_seq = min(seq_to_stop.keys())
        max_seq = max(seq_to_stop.keys())

        # 1. Check for Hard Evidence: Actual station master / controller event (ad_events) <= now
        with self.db.transaction() as cur:
            try:
                cur.execute(
                    """
                    SELECT station_code, event_kind, actual_ts
                    FROM ad_events
                    WHERE train_no = ? AND actual_ts <= ?
                    ORDER BY actual_ts DESC LIMIT 1
                    """,
                    (train_no, now_iso),
                )
                ad_row = cur.fetchone()
            except Exception:
                ad_row = None

        ad_seq: Optional[int] = None
        ad_fresh = False
        ad_age_s = 9999.0
        if ad_row and ad_row["station_code"]:
            ad_stn = ad_row["station_code"]
            ad_stop = next((r for r in route_stops if r["station_code"] == ad_stn), None)
            if ad_stop:
                ad_seq = int(ad_stop["seq"])
                try:
                    act_dt = datetime.datetime.fromisoformat(ad_row["actual_ts"].replace("Z", "+00:00"))
                    if act_dt.tzinfo is None:
                        act_dt = act_dt.replace(tzinfo=IST_TIMEZONE)
                    ad_age_s = max(0.0, (t_now - act_dt).total_seconds())
                except Exception:
                    ad_age_s = 0.0

                if ad_age_s < 900:  # Fresh hard evidence within 15 min
                    ad_fresh = True

        # 2. Check Telemetry / Station Events Feed strictly point-in-time (event_time <= now)
        with self.db.transaction() as cur:
            cur.execute(
                """
                SELECT seq, station_code, event_time, delay_arr_min, delay_dep_min, sched_arr, sched_dep, run_date
                FROM station_events
                WHERE train_no = ? AND event_time <= ?
                ORDER BY event_time DESC, seq DESC LIMIT 1
                """,
                (train_no, now_iso),
            )
            raw_ev = cur.fetchone()
            ev_dict = dict(raw_ev) if raw_ev else {}

        # Explicit assertion: any candidate event with event_time > now must be IMPOSSIBLE by construction
        if ev_dict.get("event_time"):
            assert ev_dict["event_time"] <= now_iso, (
                f"Point-in-time invariant failure: candidate event_time {ev_dict['event_time']} > now {now_iso}"
            )

        last_ev_seq = int(ev_dict["seq"]) if ev_dict.get("seq") else min_seq
        ev_source = "station_events_telemetry"
        curr_delay = float(ev_dict.get("delay_arr_min") or ev_dict.get("delay_dep_min") or 0.0)

        # Calculate time since last recorded event
        age_seconds = 60.0
        if ev_dict.get("event_time"):
            try:
                ev_dt = datetime.datetime.fromisoformat(ev_dict["event_time"].replace("Z", "+00:00"))
                if ev_dt.tzinfo is None:
                    ev_dt = ev_dt.replace(tzinfo=IST_TIMEZONE)
                age_seconds = max(0.0, (t_now - ev_dt).total_seconds())
            except Exception:
                age_seconds = 60.0
        elif ev_dict.get("run_date"):
            st = seq_to_stop.get(last_ev_seq, {})
            sched_time_str = st.get("sched_arr") or st.get("sched_dep") or "12:00"
            if ":" in sched_time_str:
                sh, sm = [int(x) for x in sched_time_str.split(":")[:2]]
                event_est_dt = datetime.datetime(t_now.year, t_now.month, t_now.day, sh, sm, tzinfo=IST_TIMEZONE) + datetime.timedelta(minutes=curr_delay)
                age_seconds = max(10.0, abs((t_now - event_est_dt).total_seconds()))

        # 3. Soft Position Posterior Distribution: P(seq=k) ∝ exp(-Δt_since_k / τ_k) · SchedPrior(k | now)
        probs: Dict[int, float] = {}
        tau = 1800.0  # 30 min characteristic decay

        for seq_k, stop in seq_to_stop.items():
            if seq_k < last_ev_seq:
                # Upstream stops already passed
                probs[seq_k] = 0.0001
            elif seq_k == last_ev_seq:
                # Last known location decayed by time elapsed
                probs[seq_k] = float(np.exp(-age_seconds / tau))
            elif seq_k in (last_ev_seq + 1, last_ev_seq + 2):
                # Next dead-reckoned stops: prior based on expected arrival vs current time
                sched_arr_str = stop.get("sched_arr") or stop.get("sched_dep") or "12:00"
                if ":" in sched_arr_str:
                    sh, sm = [int(x) for x in sched_arr_str.split(":")[:2]]
                    exp_arr_dt = datetime.datetime(t_now.year, t_now.month, t_now.day, sh, sm, tzinfo=IST_TIMEZONE) + datetime.timedelta(minutes=curr_delay)
                    time_diff_min = (exp_arr_dt - t_now).total_seconds() / 60.0
                    # Gaussian prior around expected transit window
                    prior = float(np.exp(- (time_diff_min ** 2) / (2 * (30.0 ** 2))))
                    probs[seq_k] = max(0.01, prior)
                else:
                    probs[seq_k] = 0.02
            else:
                # Far downstream stops
                probs[seq_k] = 0.001

            # Fuse ad_events hard evidence (weight ×10)
            if ad_seq is not None and seq_k == ad_seq:
                probs[seq_k] *= 10.0

        # If fresh hard ad_event exists, dominant probability
        if ad_fresh and ad_seq is not None:
            probs[ad_seq] = max(probs.get(ad_seq, 0.1), 0.95)

        # Normalize posterior
        total_p = sum(probs.values())
        if total_p > 0:
            for k in probs:
                probs[k] /= total_p
        else:
            probs = {k: 1.0 / n_stops for k in seq_to_stop}

        mode_seq = max(probs, key=probs.get)
        max_prob = probs[mode_seq]

        if ad_fresh and ad_seq == mode_seq:
            basis = "human_confirmed"
        elif age_seconds < 900:
            basis = "last_event"
        elif ev_dict:
            basis = "dead_reckoning"
        else:
            basis = "schedule_only"

        return PositionRecord(
            mode_seq=mode_seq,
            station_code=seq_to_stop[mode_seq]["station_code"],
            confidence=max_prob,
            basis=basis,
            age_seconds=age_seconds,
            source=ev_source if not (ad_fresh and ad_seq == mode_seq) else "station_master_actual",
            posterior_probs=probs,
        )
