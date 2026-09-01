"""RailTwin-X Geospatial Utilities & Weather Station Mapping (Phase B2).

Calculates Haversine distances between corridor stations and the 12 weather stations,
producing a deterministic lookup table for weather feature resolution.
"""
from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Dict, Tuple

WEATHER_STATIONS = {
    "NDLS": (28.6428, 77.2191),
    "GZB": (28.6698, 77.4386),
    "ALJN": (27.8974, 78.0709),
    "TDL": (27.2489, 78.3259),
    "ETW": (27.4833, 78.0136),
    "CNB": (26.4550, 80.3468),
    "ON": (26.5089, 80.2300),
    "LKO": (26.8310, 80.9231),
    "PRYJ": (25.4358, 81.8463),
    "DDU": (25.2820, 83.1180),
    "FTP": (25.9269, 80.8065),
    "MZP": (25.1472, 82.8473),
}


def haversine_km(a: Tuple[float, float], b: Tuple[float, float]) -> float:
    """Calculates great-circle distance between two (lat, lon) pairs in kilometers."""
    la1, lo1, la2, lo2 = map(math.radians, (a[0], a[1], b[0], b[1]))
    h = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
    return 2 * 6371 * math.asin(math.sqrt(max(0.0, min(1.0, h))))


def build_nearest_station_map(
    stations_path: str = "data/seeds/stations.json",
    output_path: str = "data/seeds/weather_station_map.json",
) -> Dict[str, Dict[str, object]]:
    """Builds and persists nearest weather station mapping for all corridor stations."""
    with open(stations_path, "r", encoding="utf-8") as f:
        stations = json.load(f)

    # Use coordinates from WEATHER_STATIONS dict as ground truth
    ws = WEATHER_STATIONS

    mapping = {}
    for s in stations:
        stn_coords = (float(s["lat"]), float(s["lon"]))
        best = min(ws, key=lambda w: haversine_km(stn_coords, ws[w]))
        d = haversine_km(stn_coords, ws[best])
        mapping[s["code"]] = {"nearest": best, "dist_km": round(d, 1)}

    out_file = Path(output_path)
    out_file.parent.mkdir(parents=True, exist_ok=True)
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(mapping, f, indent=2)

    return mapping


if __name__ == "__main__":
    m = build_nearest_station_map()
    print(f"Mapped {len(m)} stations to 12 weather stations. Saved to data/seeds/weather_station_map.json")
