"""engine/infrastructure.py — L2 Static Infrastructure Model (Part 3 & Phase P2).

Static infrastructure layer:
- Subdivides sections into ~5 km blocks (length ∈ [3, 8] km, ≥8 blocks per original section).
- Every station assigned ≥1 loop line for overtakes/detentions.
- Synthetic loop-capable crossing stations placed every ~20 km (where station gap > 25 km).
- Section parameters: gradient_per_mille (default 0.0), curve_radius_m (default inf),
  line speed, turnout speed (default 30 km/h), TSR slots.
"""

from __future__ import annotations

import json
import math
import pathlib
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent


@dataclass
class Block:
    """An automatic signaling / track circuit block (~5 km)."""

    block_id: str
    from_station: str
    to_station: str
    start_km: float
    end_km: float
    length_km: float
    direction: str = "UP"  # "UP", "DOWN", or "BIDIRECTIONAL"
    line_speed_kmh: float = 130.0
    gradient_per_mille: float = 0.0
    curve_radius_m: float = float("inf")
    turnout_speed_kmh: float = 30.0
    tsr_speed_kmh: Optional[float] = None
    is_loop: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "block_id": self.block_id,
            "from_station": self.from_station,
            "to_station": self.to_station,
            "start_km": self.start_km,
            "end_km": self.end_km,
            "length_km": self.length_km,
            "direction": self.direction,
            "line_speed_kmh": self.line_speed_kmh,
            "gradient_per_mille": self.gradient_per_mille,
            "curve_radius_m": None if math.isinf(self.curve_radius_m) else self.curve_radius_m,
            "turnout_speed_kmh": self.turnout_speed_kmh,
            "tsr_speed_kmh": self.tsr_speed_kmh,
            "is_loop": self.is_loop,
        }


@dataclass
class Station:
    """A physical or synthetic crossing station with main and loop lines."""

    code: str
    name: str
    km: float
    main_lines: int = 2
    loop_lines: int = 2  # Guaranteed >= 1
    loop_capacity: int = 2
    platforms: int = 4
    is_junction: bool = False
    is_synthetic: bool = False
    turnout_speed_kmh: float = 30.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "code": self.code,
            "name": self.name,
            "km": self.km,
            "main_lines": self.main_lines,
            "loop_lines": self.loop_lines,
            "loop_capacity": self.loop_capacity,
            "platforms": self.platforms,
            "is_junction": self.is_junction,
            "is_synthetic": self.is_synthetic,
            "turnout_speed_kmh": self.turnout_speed_kmh,
        }


class InfrastructureCorridor:
    """L2 Static Infrastructure Manager for Delhi-Kanpur-Lucknow corridor."""

    def __init__(self, sections_path: Optional[pathlib.Path] = None, stations_path: Optional[pathlib.Path] = None):
        self.sections_path = sections_path or (REPO_ROOT / "data" / "seeds" / "sections.json")
        self.stations_path = stations_path or (REPO_ROOT / "data" / "seeds" / "stations.json")
        self.original_stations: List[Station] = []
        self.all_stations: List[Station] = []
        self.stations_by_code: Dict[str, Station] = {}
        self.sections: List[Dict[str, Any]] = []
        self.blocks: List[Block] = []
        self.blocks_by_section: Dict[Tuple[str, str], List[Block]] = {}

        self._build_infrastructure()

    def _build_infrastructure(self) -> None:
        """Constructs canonical L2 infrastructure model from seeds."""
        with open(self.sections_path, "r", encoding="utf-8") as f:
            raw_sections = json.load(f)

        # 1. Compute cumulative station kilometers along the main corridor
        # NDLS -> GZB -> ALJN -> TDL -> ETW -> CNB -> ON -> LKO
        corridor_edges = [
            ("NDLS", "GZB"),
            ("GZB", "ALJN"),
            ("ALJN", "TDL"),
            ("TDL", "ETW"),
            ("ETW", "CNB"),
            ("CNB", "ON"),
            ("ON", "LKO"),
        ]

        # Load section lookup
        sec_map = {(s["from_code"], s["to_code"]): s for s in raw_sections}

        station_names = {
            "NDLS": "New Delhi",
            "GZB": "Ghaziabad Junction",
            "ALJN": "Aligarh Junction",
            "TDL": "Tundla Junction",
            "ETW": "Etawah Junction",
            "CNB": "Kanpur Central",
            "ON": "Unnao Junction",
            "LKO": "Lucknow Charbagh",
        }

        # Original station sequence
        curr_km = 0.0
        self.original_stations.append(
            Station(
                code="NDLS",
                name=station_names["NDLS"],
                km=0.0,
                main_lines=2,
                loop_lines=4,
                platforms=16,
                is_junction=True,
                is_synthetic=False,
            )
        )

        for u, v in corridor_edges:
            sec = sec_map.get((u, v))
            dist = float(sec["distance_km"]) if sec else 50.0
            curr_km += dist
            self.original_stations.append(
                Station(
                    code=v,
                    name=station_names.get(v, v),
                    km=round(curr_km, 3),
                    main_lines=2,
                    loop_lines=3 if v in ("GZB", "ALJN", "CNB", "LKO") else 2,
                    platforms=10 if v == "CNB" else 6,
                    is_junction=True if v in ("GZB", "ALJN", "TDL", "ETW", "CNB", "ON", "LKO") else False,
                    is_synthetic=False,
                )
            )

        # 2. Interleave synthetic loop-capable crossing stations every ~20 km (where gap > 25 km)
        self.all_stations = []
        for i in range(len(self.original_stations) - 1):
            stn_a = self.original_stations[i]
            stn_b = self.original_stations[i + 1]
            self.all_stations.append(stn_a)

            gap = stn_b.km - stn_a.km
            if gap > 25.0:
                # Add crossing stations every ~20 km
                num_crossings = int(math.floor(gap / 20.0))
                # Distribute evenly
                spacing = gap / (num_crossings + 1)
                for c_idx in range(1, num_crossings + 1):
                    cross_km = round(stn_a.km + c_idx * spacing, 3)
                    cross_code = f"SYN_{stn_a.code}_{stn_b.code}_{c_idx}"
                    cross_stn = Station(
                        code=cross_code,
                        name=f"{stn_a.code}-{stn_b.code} Crossing {c_idx}",
                        km=cross_km,
                        main_lines=2,
                        loop_lines=1,  # Every station gets >= 1 loop line
                        loop_capacity=1,
                        platforms=1,
                        is_junction=False,
                        is_synthetic=True,
                        turnout_speed_kmh=30.0,
                    )
                    self.all_stations.append(cross_stn)

        # Append final station
        self.all_stations.append(self.original_stations[-1])
        self.stations_by_code = {s.code: s for s in self.all_stations}

        # 3. Subdivide every original section into ~5 km blocks (length ∈ [3, 8] km, ≥8 blocks per section)
        for u, v in corridor_edges:
            sec = sec_map.get((u, v))
            dist = float(sec["distance_km"]) if sec else 25.0
            line_speed = float(sec.get("max_speed_kmph", 130.0)) if sec else 130.0
            grad = float(sec.get("gradient_per_mille", 0.0)) if sec else 0.0
            curve_r = sec.get("curve_radius_m")
            curve_r_val = float(curve_r) if curve_r is not None else float("inf")

            # Determine number of blocks: >= 8 blocks, targeting ~5 km per block
            # If dist=25 km, n_blocks=8 -> block_len=3.125 km (∈ [3, 8])
            # If dist=106 km, n_blocks=21 -> block_len=5.048 km (∈ [3, 8])
            # If dist=24 km, n_blocks=8 -> block_len=3.0 km (∈ [3, 8])
            n_blocks = max(8, round(dist / 5.0))
            block_len = round(dist / n_blocks, 4)

            sec_start_km = self.stations_by_code[u].km
            sec_blocks: List[Block] = []

            for b_idx in range(n_blocks):
                b_start = round(sec_start_km + b_idx * block_len, 4)
                b_end = round(sec_start_km + (b_idx + 1) * block_len if b_idx < n_blocks - 1 else sec_start_km + dist, 4)
                actual_len = round(b_end - b_start, 4)

                block_id = f"BLK_{u}_{v}_{b_idx + 1:02d}"
                block = Block(
                    block_id=block_id,
                    from_station=u,
                    to_station=v,
                    start_km=b_start,
                    end_km=b_end,
                    length_km=actual_len,
                    direction="BIDIRECTIONAL" if sec and sec.get("single_line") else "UP",
                    line_speed_kmh=line_speed,
                    gradient_per_mille=grad,
                    curve_radius_m=curve_r_val,
                    turnout_speed_kmh=30.0,
                    tsr_speed_kmh=None,
                    is_loop=False,
                )
                sec_blocks.append(block)
                self.blocks.append(block)

            self.blocks_by_section[(u, v)] = sec_blocks

    def get_blocks_for_section(self, from_code: str, to_code: str) -> List[Block]:
        """Returns ordered blocks for a given original section."""
        return self.blocks_by_section.get((from_code, to_code), [])

    def get_station(self, code: str) -> Optional[Station]:
        """Retrieves a station by code."""
        return self.stations_by_code.get(code)

    def get_all_stations(self) -> List[Station]:
        """Returns all stations in corridor order."""
        return list(self.all_stations)

    def get_all_blocks(self) -> List[Block]:
        """Returns all subdivided blocks in corridor order."""
        return list(self.blocks)

    def get_block_at_km(self, km: float) -> Optional[Block]:
        """Finds the block containing a given kilometer mark."""
        for b in self.blocks:
            if b.start_km <= km <= b.end_km:
                return b
        return None
