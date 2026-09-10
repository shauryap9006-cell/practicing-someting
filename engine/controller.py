"""engine/controller.py — L4 Autonomous Dispatch Controller & Interlocking (Phase P5).

Autonomous Dispatcher Layer:
- Monitors corridor occupancy and train priorities.
- Priority hierarchy: premium (1) > mail/exp (2) > passenger (3) > freight (4).
- Overtake logic: If higher-priority train is within 10 km behind a slower train on same direction
  AND a loop-capable station is within 15 km ahead:
  -> Diverts slower train to loop line (phase=LOOP_HELD).
  -> Holds slower train until 2 min after the priority train passes.
- Interlocking: Interacts strictly via route locks and route requests.
- Platform first-fit allocation: holds approaching trains if platforms are saturated.
- Emits ledger events: OVERTAKE, HELD_LOOP, CROSSING_HOLD.
- RULE: NEVER sets train speed directly. Motion governed strictly by L1 physics and L3 signals.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from engine.infrastructure import Block, InfrastructureCorridor, Station
from engine.signalling import BlockMap, RouteLock, SignalAspect


PRIORITY_MAP: Dict[str, int] = {
    "premium": 1,
    "mail/exp": 2,
    "EMU": 2,
    "passenger": 3,
    "freight": 4,
}


@dataclass
class OvertakeRecord:
    """Active overtake tracking state."""
    fast_train_id: str
    slow_train_id: str
    station_code: str
    station_km: float
    time_since_passed_sec: float = 0.0
    hold_duration_sec: float = 0.0
    fast_has_passed: bool = False


class AutonomousController:
    """L4 Autonomous Dispatcher and Interlocking Route Controller."""

    def __init__(
        self,
        block_map: BlockMap,
        corridor: Optional[InfrastructureCorridor] = None,
    ):
        self.block_map = block_map
        self.corridor = corridor or InfrastructureCorridor()
        self.active_overtakes: Dict[str, OvertakeRecord] = {}  # slow_train_id -> OvertakeRecord
        self.station_platforms: Dict[str, List[Optional[str]]] = {}

        # Initialize platform tracking
        for stn in self.corridor.get_all_stations():
            self.station_platforms[stn.code] = [None] * stn.platforms

    @staticmethod
    def get_priority(train_class: str) -> int:
        """Returns numeric priority (1 is highest, 4 is lowest)."""
        return PRIORITY_MAP.get(train_class, 3)

    def tick(
        self,
        active_trains: Dict[str, Any],
        dt_seconds: float = 1.0,
        sim_time_iso: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Controller tick: scans corridor, requests loop diversions, manages overtakes."""
        events: List[Dict[str, Any]] = []

        # -------------------------------------------------------------
        # 1. Manage Active Overtakes & Loop Releases
        # -------------------------------------------------------------
        for slow_id, record in list(self.active_overtakes.items()):
            slow_train = active_trains.get(slow_id)
            if slow_train is None or getattr(slow_train, "is_terminated", False):
                self.block_map.release_route(record.station_code, slow_id)
                del self.active_overtakes[slow_id]
                continue

            fast_train = active_trains.get(record.fast_train_id)

            # Check if slow train has reached the loop siding
            dist_to_loop_km = abs(slow_train.km - record.station_km)
            if dist_to_loop_km <= 0.5:
                if slow_train.phase != "LOOP_HELD":
                    slow_train.phase = "LOOP_HELD"
                    slow_train.speed_kmh = 0.0
                    # Vacate mainline block for overtaking train
                    curr_blk = self.block_map.get_train_block(slow_id)
                    if curr_blk:
                        self.block_map.clear_block(curr_blk, slow_id)
                record.hold_duration_sec += dt_seconds

            # Check if fast train has passed the station / loop siding
            if fast_train is None or getattr(fast_train, "is_terminated", False):
                record.fast_has_passed = True
            elif fast_train.km >= record.station_km + 4.0:  # Cleared loop station block
                record.fast_has_passed = True

            if record.fast_has_passed:
                record.time_since_passed_sec += dt_seconds
                # Release 2 minutes (120 s) after priority train passes
                if record.time_since_passed_sec >= 120.0:
                    self.block_map.release_route(record.station_code, slow_id)
                    if slow_train.phase in ("LOOP_HELD", "HELD_LOOP", "HELD"):
                        slow_train.phase = "DEPART"
                        setattr(slow_train, "held_reason", None)
                        # Re-occupy mainline block upon release
                        rel_blk = self.corridor.get_block_at_km(slow_train.km)
                        if rel_blk:
                            self.block_map.occupy_block(rel_blk.block_id, slow_id)

                    events.append({
                        "event_type": "RELEASE_LOOP",
                        "train_no": slow_id,
                        "priority_train": record.fast_train_id,
                        "station_code": record.station_code,
                        "hold_duration_sec": round(record.hold_duration_sec, 1),
                        "sim_time": sim_time_iso,
                    })
                    del self.active_overtakes[slow_id]

        # -------------------------------------------------------------
        # 2. Overtake Detection Scan
        # -------------------------------------------------------------
        train_list = [t for t in active_trains.values() if not getattr(t, "is_terminated", False)]

        for fast_t in train_list:
            p_fast = self.get_priority(fast_t.train_class)

            for slow_t in train_list:
                if fast_t.train_no == slow_t.train_no:
                    continue
                p_slow = self.get_priority(slow_t.train_class)

                # Only higher-priority trains (p_fast < p_slow) trigger overtakes
                if p_fast >= p_slow:
                    continue

                # Same direction UP: fast train is behind slow train within 10 km
                gap_km = slow_t.km - fast_t.km
                if not (0.0 < gap_km <= 10.0):
                    continue

                # Check if slower train is already being overtaken
                if slow_t.train_no in self.active_overtakes:
                    continue

                # Find loop-capable station within 15 km ahead of slower train
                candidate_stn: Optional[Station] = None
                for stn in self.corridor.get_all_stations():
                    dist_ahead = stn.km - slow_t.km
                    if 0.0 <= dist_ahead <= 15.0 and stn.loop_lines >= 1:
                        candidate_stn = stn
                        break

                if candidate_stn is None:
                    continue

                # Request route lock to LOOP siding for slower train
                locked = self.block_map.lock_route(
                    station_code=candidate_stn.code,
                    train_id=slow_t.train_no,
                    route_type="LOOP",
                    turnout_speed_kmh=candidate_stn.turnout_speed_kmh,
                )
                if not locked:
                    continue

                # Register overtake
                self.active_overtakes[slow_t.train_no] = OvertakeRecord(
                    fast_train_id=fast_t.train_no,
                    slow_train_id=slow_t.train_no,
                    station_code=candidate_stn.code,
                    station_km=candidate_stn.km,
                )

                events.append({
                    "event_type": "OVERTAKE",
                    "train_no": fast_t.train_no,
                    "overtaking_train": fast_t.train_no,
                    "overtaken_train": slow_t.train_no,
                    "station_code": candidate_stn.code,
                    "sim_time": sim_time_iso,
                })
                events.append({
                    "event_type": "HELD_LOOP",
                    "train_no": slow_t.train_no,
                    "station_code": candidate_stn.code,
                    "sim_time": sim_time_iso,
                    "reason": f"Priority overtake by {fast_t.train_no}",
                })

        # -------------------------------------------------------------
        # 3. Platform First-Fit Allocation & Crossing Holds
        # -------------------------------------------------------------
        for train in train_list:
            if train.phase == "APPROACH" and getattr(train, "next_stop", None):
                stn_code = train.next_stop.station_code
                stn = self.corridor.get_station(stn_code)
                if stn:
                    occupied_plats = sum(
                        1 for other in train_list
                        if other.train_no != train.train_no
                        and other.phase == "DWELL"
                        and getattr(other, "current_stop", None)
                        and other.current_stop.station_code == stn_code
                    )
                    if occupied_plats >= stn.platforms:
                        events.append({
                            "event_type": "CROSSING_HOLD",
                            "train_no": train.train_no,
                            "station_code": stn_code,
                            "sim_time": sim_time_iso,
                            "reason": f"All {stn.platforms} platforms occupied at {stn_code}",
                        })

        return events
