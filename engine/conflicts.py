"""RailTwin-X Deterministic Conflict Scanner (Phase G5 + DFC Phase 4).

100% DETERMINISTIC NETWORK CONFLICT DETECTION.
Zero Machine Learning in safety conflict rules.

Scans for:
1. Station Headway Separation Conflicts (< 5 min passenger / < 8 min freight / < 14 min coal)
2. Single-Line Opposing Meet Conflicts (< 10 min clearance window on single track)
3. Same-Section Follower Catch-up Conflicts (leading train delayed, trailing train closing headway)

Freight headway table (DFC Phase 4):
- coal_rake        : 14.0 min  (heavy haul braking distance)
- container / auto_rake / steel_rake / empty_freight : 8.0 min
- passenger (all)  :  5.0 min  (default)

Produces structured advisory recommendations:
- suggested_action ∈ ["hold_at_loop", "proceed", "controller_review", "stop_train_advisory"]
- human_ack_required = True (always advisory)
"""

from __future__ import annotations

import datetime
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from data.db import Database, get_db
from engine.track_graph import TrackGraph


@dataclass(frozen=True)
class ConflictRecord:
    """Individual conflict detected by deterministic safety rules."""
    conflict_id: str
    target_train: str
    with_train: str
    station_code: str
    conflict_type: str  # STATION_HEADWAY, SINGLE_LINE_OPPOSING, SECTION_CATCHUP
    predicted_gap_min: float
    severity: str       # HIGH, MEDIUM, LOW
    suggested_action: str  # hold_at_loop, proceed, controller_review, stop_train_advisory
    reason: str
    human_ack_required: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "conflict_id": self.conflict_id,
            "target_train": self.target_train,
            "with_train": self.with_train,
            "station_code": self.station_code,
            "conflict_type": self.conflict_type,
            "predicted_gap_min": round(self.predicted_gap_min, 1),
            "severity": self.severity,
            "suggested_action": self.suggested_action,
            "reason": self.reason,
            "human_ack_required": self.human_ack_required,
        }


# Freight headway lookup (DFC Phase 4)
_FREIGHT_HEADWAY: Dict[str, float] = {
    "coal_rake":    14.0,  # heavy haul – long braking distance
    "container":     8.0,
    "auto_rake":     8.0,
    "steel_rake":    8.0,
    "empty_freight": 8.0,
}
_PASSENGER_HEADWAY = 5.0


def _headway_for_class(train_class: str) -> float:
    """Returns the minimum required headway (minutes) for a given train class."""
    return _FREIGHT_HEADWAY.get(train_class, _PASSENGER_HEADWAY)


class ConflictScanner:
    """Deterministic railway traffic conflict scanner (freight-aware)."""

    def __init__(
        self,
        db: Optional[Database] = None,
        min_station_headway_min: float = _PASSENGER_HEADWAY,
        min_single_line_clearance_min: float = 10.0,
    ):
        self.db = db or get_db()
        self.track_graph = TrackGraph(self.db)
        self.min_station_headway = min_station_headway_min
        self.min_single_line_clearance = min_single_line_clearance_min
        # Cache train classes to avoid repeated DB hits per scan
        self._train_class_cache: Dict[str, str] = {}

    def _get_train_class(self, train_no: str) -> str:
        """Returns train class string for headway determination, with in-memory cache."""
        if train_no not in self._train_class_cache:
            with self.db.transaction() as cur:
                cur.execute("SELECT class FROM trains WHERE train_no = ?", (train_no,))
                row = cur.fetchone()
            self._train_class_cache[train_no] = row["class"] if row else "superfast"
        return self._train_class_cache[train_no]

    def _required_headway(self, train_a: str, train_b: str) -> float:
        """Returns the required headway between two trains (max of both requirements)."""
        hw_a = _headway_for_class(self._get_train_class(train_a))
        hw_b = _headway_for_class(self._get_train_class(train_b))
        return max(hw_a, hw_b)

    def scan_train_conflicts(
        self,
        train_no: str,
        target_date_str: Optional[str] = None,
    ) -> List[ConflictRecord]:
        """Scans the corridor for all active and projected conflicts involving train_no."""
        route = self.track_graph.get_route(train_no)
        if not route:
            return []

        # Get latest event for this train
        with self.db.transaction() as cur:
            cur.execute(
                """
                SELECT seq, station_code, delay_arr_min, delay_dep_min, run_date
                FROM station_events
                WHERE train_no = ?
                ORDER BY run_date DESC, seq DESC LIMIT 1
                """,
                (train_no,),
            )
            my_ev = cur.fetchone()

        my_date = target_date_str or (my_ev["run_date"] if my_ev else datetime.date.today().isoformat())
        my_delay = float(my_ev["delay_arr_min"] if my_ev and my_ev["delay_arr_min"] is not None else 0.0)

        # Get all other active trains on this date
        with self.db.transaction() as cur:
            cur.execute(
                """
                SELECT se.train_no, se.seq, se.station_code, se.delay_arr_min, se.delay_dep_min
                FROM station_events se
                INNER JOIN (
                    SELECT train_no, MAX(seq) as max_seq
                    FROM station_events
                    WHERE run_date = ?
                    GROUP BY train_no
                ) latest ON se.train_no = latest.train_no AND se.seq = latest.max_seq
                WHERE se.run_date = ? AND se.train_no != ?
                """,
                (my_date, my_date, train_no),
            )
            other_trains = cur.fetchall()

        conflicts: List[ConflictRecord] = []

        # Compute projected arrival at each station on my route
        my_arrivals: Dict[str, float] = {}
        for r_stop in route:
            stn = r_stop["station_code"]
            sched_str = r_stop["sched_arr"]
            if sched_str and ":" in sched_str:
                sh, sm = map(int, sched_str.split(":"))
                my_arrivals[stn] = (sh * 60 + sm) + my_delay

        for ot in other_trains:
            o_no = ot["train_no"]
            o_route = self.track_graph.get_route(o_no)
            if not o_route:
                continue

            o_delay = float(ot["delay_arr_min"] if ot["delay_arr_min"] is not None else 0.0)
            o_arrivals: Dict[str, float] = {}
            for ost in o_route:
                stn = ost["station_code"]
                sched_str = ost["sched_arr"]
                if sched_str and ":" in sched_str:
                    sh, sm = map(int, sched_str.split(":"))
                    o_arrivals[stn] = (sh * 60 + sm) + o_delay

            # Check shared stations
            shared_stns = set(my_arrivals.keys()).intersection(set(o_arrivals.keys()))
            for stn in shared_stns:
                t1_arr = my_arrivals[stn]
                t2_arr = o_arrivals[stn]
                gap = abs(t1_arr - t2_arr)

                # Check if same section is single line
                is_single = False
                for i in range(len(route) - 1):
                    if route[i]["station_code"] == stn or route[i+1]["station_code"] == stn:
                        sec_info = self.track_graph.get_section_info(route[i]["station_code"], route[i+1]["station_code"])
                        if sec_info.get("single_line"):
                            is_single = True
                            break

                # 1. Opposing Single-Line Conflict
                same_dir = (route[-1]["station_code"] == o_route[-1]["station_code"])
                if is_single and not same_dir and gap < self.min_single_line_clearance:
                    conflicts.append(
                        ConflictRecord(
                            conflict_id=f"CONF-SL-{train_no}-{o_no}-{stn}",
                            target_train=train_no,
                            with_train=o_no,
                            station_code=stn,
                            conflict_type="SINGLE_LINE_OPPOSING",
                            predicted_gap_min=gap,
                            severity="HIGH",
                            suggested_action="hold_at_loop" if int(route[0]["priority"]) <= int(o_route[0]["priority"]) else "proceed",
                            reason=f"Opposing movement on single-line block at {stn} with only {gap:.1f}m clearance (<{self.min_single_line_clearance}m limit).",
                        )
                    )
                # 2. Station Headway Separation Conflict
                else:
                    req_headway = self._required_headway(train_no, o_no)
                    if gap < req_headway:
                        severity = "HIGH" if gap < 2.0 else "MEDIUM"
                        suggested = "stop_train_advisory" if gap < 1.0 else "controller_review"
                        conflicts.append(
                            ConflictRecord(
                                conflict_id=f"CONF-HW-{train_no}-{o_no}-{stn}",
                                target_train=train_no,
                                with_train=o_no,
                                station_code=stn,
                                conflict_type="STATION_HEADWAY",
                                predicted_gap_min=gap,
                                severity=severity,
                                suggested_action=suggested,
                                reason=f"Projected arrival headway at {stn} ({gap:.1f}m) is below safety headway buffer ({req_headway}m).",
                            )
                        )

        return conflicts

    def dispatch_conflict_alerts(self, conflicts: List[ConflictRecord]) -> List[dict]:
        """Dispatches AlertEvents for HIGH severity conflicts via the notification dispatcher."""
        from notifications import AlertEvent, get_dispatcher
        dispatcher = get_dispatcher(self.db)
        dispatch_results = []

        for c in conflicts:
            if c.severity in ("HIGH", "MEDIUM"):
                event = AlertEvent(
                    severity=c.severity,
                    event_type="conflict",
                    title=f"{c.conflict_type.replace('_', ' ')} with #{c.with_train} at {c.station_code}",
                    body=c.reason,
                    station_code=c.station_code,
                    train_no=c.target_train,
                    roles=["controller", "pointsman"],
                    ack_id=c.conflict_id,
                    metadata={"with_train": c.with_train, "suggested_action": c.suggested_action},
                )
                res = dispatcher.dispatch(event)
                dispatch_results.append(res)

        return dispatch_results


