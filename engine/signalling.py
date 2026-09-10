"""engine/signalling.py — L3 Pure Signaling & Block Occupancy Layer (Part 3 & Phase P4).

Pure functional signaling architecture:
1. BlockMap: per-direction track occupancy updated strictly on block boundary crossings.
2. SignalSystem: pure function of occupancy + route locks. No internal state, no random, no clock.
3. 4-Aspect sequence: GREEN (G) -> DOUBLE_YELLOW (YY) -> YELLOW (Y) -> RED (R).
4. Station route locks: MAIN vs LOOP turnout governing speed restrictions.
5. Invariant: NEVER allows two trains in the same block.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from engine.infrastructure import Block, InfrastructureCorridor


@dataclass(frozen=True)
class SignalAspect:
    """Immutable result of signal aspect calculation."""
    code: str              # 'R', 'Y', 'YY', 'G'
    target_speed_kmh: float # 0.0 for R, 30.0 for Y, 60.0 for YY, line_speed for G
    stop_required: bool    # True if RED
    description: str


@dataclass
class RouteLock:
    """Station interlocking route lock."""
    station_code: str
    train_id: str
    route_type: str = "MAIN"  # "MAIN" or "LOOP"
    turnout_speed_kmh: float = 30.0
    locked: bool = True


class SignalSystem:
    """Pure functional 4-aspect signaling engine."""

    ASPECT_RED = "R"
    ASPECT_YELLOW = "Y"
    ASPECT_DOUBLE_YELLOW = "YY"
    ASPECT_GREEN = "G"

    @staticmethod
    def compute_aspect(
        current_block_idx: int,
        corridor_blocks: List[Block],
        occupancy_map: Dict[str, Optional[str]],
        route_lock: Optional[RouteLock] = None,
        direction: str = "UP",
    ) -> SignalAspect:
        """Pure function: computes 4-aspect signal at the exit of current_block_idx.

        Aspect logic:
        - R (RED): next block occupied -> target speed 0 km/h (stop AT signal).
        - Y (YELLOW): next block clear, 2nd block occupied -> target speed 30 km/h.
        - YY (DOUBLE YELLOW): next 2 blocks clear, 3rd block occupied -> target speed 60 km/h.
        - G (GREEN): 3+ blocks clear -> line speed.
        Route lock to LOOP clamps aspect to Y / turnout speed (30 km/h).
        """
        n_blocks = len(corridor_blocks)
        curr = corridor_blocks[current_block_idx] if 0 <= current_block_idx < n_blocks else None
        line_speed = curr.line_speed_kmh if curr else 130.0

        step = 1 if direction == "UP" else -1
        idx_1 = current_block_idx + step
        idx_2 = current_block_idx + 2 * step
        idx_3 = current_block_idx + 3 * step

        # Block 1 (immediate next block)
        if 0 <= idx_1 < n_blocks:
            b1 = corridor_blocks[idx_1]
            if occupancy_map.get(b1.block_id) is not None:
                return SignalAspect(
                    code=SignalSystem.ASPECT_RED,
                    target_speed_kmh=0.0,
                    stop_required=True,
                    description="Stop at signal: next block occupied",
                )
        else:
            # Beyond corridor boundary
            return SignalAspect(
                code=SignalSystem.ASPECT_GREEN,
                target_speed_kmh=line_speed,
                stop_required=False,
                description="Clear: exit corridor",
            )

        # Handle Route Lock for turnout/loop diversion
        if route_lock and route_lock.locked and route_lock.route_type == "LOOP":
            return SignalAspect(
                code=SignalSystem.ASPECT_YELLOW,
                target_speed_kmh=min(30.0, route_lock.turnout_speed_kmh),
                stop_required=False,
                description=f"Caution: diverted to loop at {route_lock.station_code}",
            )

        # Block 2 (second block ahead)
        if 0 <= idx_2 < n_blocks:
            b2 = corridor_blocks[idx_2]
            if occupancy_map.get(b2.block_id) is not None:
                return SignalAspect(
                    code=SignalSystem.ASPECT_YELLOW,
                    target_speed_kmh=30.0,
                    stop_required=False,
                    description="Caution: 2nd block occupied, prepare to stop at next signal",
                )
        else:
            return SignalAspect(
                code=SignalSystem.ASPECT_GREEN,
                target_speed_kmh=line_speed,
                stop_required=False,
                description="Clear: corridor end",
            )

        # Block 3 (third block ahead)
        if 0 <= idx_3 < n_blocks:
            b3 = corridor_blocks[idx_3]
            if occupancy_map.get(b3.block_id) is not None:
                return SignalAspect(
                    code=SignalSystem.ASPECT_DOUBLE_YELLOW,
                    target_speed_kmh=60.0,
                    stop_required=False,
                    description="Attention: 3rd block occupied, pass at 60 km/h",
                )

        # 3+ blocks clear
        return SignalAspect(
            code=SignalSystem.ASPECT_GREEN,
            target_speed_kmh=line_speed,
            stop_required=False,
            description="Proceed: next 3+ blocks clear",
        )


class BlockMap:
    """Tracks per-direction block occupancy and interlocking route locks."""

    def __init__(self, blocks: Optional[List[Block]] = None):
        if blocks is None:
            corridor = InfrastructureCorridor()
            self.blocks = corridor.get_all_blocks()
        else:
            self.blocks = list(blocks)

        self._block_by_id: Dict[str, Block] = {b.block_id: b for b in self.blocks}
        self._block_idx_by_id: Dict[str, int] = {b.block_id: i for i, b in enumerate(self.blocks)}
        # block_id -> train_id (or None if clear)
        self._occupancy: Dict[str, Optional[str]] = {b.block_id: None for b in self.blocks}
        # train_id -> block_id
        self._train_locations: Dict[str, str] = {}
        # station_code -> RouteLock
        self._route_locks: Dict[str, RouteLock] = {}

    def is_occupied(self, block_id: str) -> bool:
        return self._occupancy.get(block_id) is not None

    def get_occupant(self, block_id: str) -> Optional[str]:
        return self._occupancy.get(block_id)

    def get_train_block(self, train_id: str) -> Optional[str]:
        return self._train_locations.get(train_id)

    def occupy_block(self, block_id: str, train_id: str) -> bool:
        """Attempts to occupy block. Fails safely if already occupied by another train."""
        current = self._occupancy.get(block_id)
        if current is not None and current != train_id:
            return False  # Safety invariant: strictly one train per block!
        self._occupancy[block_id] = train_id
        self._train_locations[train_id] = block_id
        return True

    def clear_block(self, block_id: str, train_id: Optional[str] = None) -> None:
        """Clears block occupancy if matching train."""
        if block_id in self._occupancy:
            if train_id is None or self._occupancy[block_id] == train_id:
                self._occupancy[block_id] = None
                if train_id and self._train_locations.get(train_id) == block_id:
                    del self._train_locations[train_id]

    def move_train(self, train_id: str, to_block_id: str) -> bool:
        """Moves train into to_block_id and vacates previous block atomically."""
        from_block = self._train_locations.get(train_id)
        if to_block_id == from_block:
            return True
        if self.is_occupied(to_block_id):
            return False  # Target occupied -> motion blocked
        # Occupy new block first, then clear previous
        self._occupancy[to_block_id] = train_id
        self._train_locations[train_id] = to_block_id
        if from_block and self._occupancy.get(from_block) == train_id:
            self._occupancy[from_block] = None
        return True

    def remove_train(self, train_id: str) -> None:
        """Removes train from corridor."""
        b_id = self._train_locations.pop(train_id, None)
        if b_id and self._occupancy.get(b_id) == train_id:
            self._occupancy[b_id] = None

    def lock_route(self, station_code: str, train_id: str, route_type: str = "MAIN", turnout_speed_kmh: float = 30.0) -> bool:
        """Locks route for interlocking."""
        existing = self._route_locks.get(station_code)
        if existing and existing.locked and existing.train_id != train_id:
            return False  # Route conflict
        self._route_locks[station_code] = RouteLock(
            station_code=station_code,
            train_id=train_id,
            route_type=route_type,
            turnout_speed_kmh=turnout_speed_kmh,
            locked=True,
        )
        return True

    def release_route(self, station_code: str, train_id: Optional[str] = None) -> None:
        """Releases interlocking route lock."""
        if station_code in self._route_locks:
            if train_id is None or self._route_locks[station_code].train_id == train_id:
                del self._route_locks[station_code]

    def get_signal_for_train(self, train_id: str, direction: str = "UP") -> SignalAspect:
        """Pure aspect lookup for a train based on its current block."""
        curr_block_id = self._train_locations.get(train_id)
        if not curr_block_id:
            return SignalAspect(code="G", target_speed_kmh=130.0, stop_required=False, description="Clear")
        curr_idx = self._block_idx_by_id[curr_block_id]
        curr_block = self.blocks[curr_idx]
        station = curr_block.to_station
        route_lock = self._route_locks.get(station)
        return SignalSystem.compute_aspect(
            current_block_idx=curr_idx,
            corridor_blocks=self.blocks,
            occupancy_map=self._occupancy,
            route_lock=route_lock,
            direction=direction,
        )

    def get_occupancy_snapshot(self) -> Dict[str, Optional[str]]:
        return dict(self._occupancy)
