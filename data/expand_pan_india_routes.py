"""RailTwin-X Pan-India Route Expansion Script.

Assigns realistic national railway corridors across India to trains in the database
that lack existing route definitions:
1. Northern Mainline (Delhi - Kanpur - Lucknow)
2. Eastern Trunk (Delhi - Kanpur - Prayagraj - Varanasi - DDU - Patna - Howrah)
3. Western Trunk (Delhi - Mathura - Kota - Ratlam - Vadodara - Surat - Mumbai)
4. Central / Grand Trunk (Delhi - Agra - Gwalior - Jhansi - Bhopal - Nagpur - Vijayawada - Chennai)
5. South-Western (Delhi - Bhopal - Nagpur - Wadi - Guntakal - Bengaluru)
6. Southern Intercity (Mumbai - Pune - Solapur - Wadi - Guntakal - Chennai)
7. East Coast (Howrah - Kharagpur - Bhubaneswar - Visakhapatnam - Vijayawada - Chennai)
8. Konkan / Malabar (Mumbai - Ratnagiri - Madgaon - Mangalore - Kochi - Trivandrum)
9. Northeast Frontier (Patna - Barauni - Katihar - New Jalpaiguri - Guwahati - Dibrugarh)
10. Northern Hill / Border (Delhi - Ambala - Ludhiana - Amritsar - Jammu - Katra)
11. Western Regional (Mumbai - Surat - Vadodara - Ahmedabad)

Safety Guarantees:
- Never executes wholesale DELETE FROM route_stations.
- Never touches corridor trains (12034, 12301, 2421, or NDLS..CNB..LKO corridor).
- No modulo-hash guessing fallback; unknown routes are skipped with a warning.
- Defaults to --dry-run (zero writes). Requires explicit --apply to write to database.
"""

from __future__ import annotations

import argparse
import datetime
import logging
from typing import Dict, List, Optional, Set

from data.db import get_db

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# Pre-defined All-India Corridors using real station codes in stations table
CORRIDORS = {
    "DELHI_LUCKNOW": ["NDLS", "GZB", "ALJN", "TDL", "ETW", "CNB", "ON", "LKO"],
    "EASTERN_TRUNK": ["NDLS", "GZB", "ALJN", "CNB", "PRYJ", "BSB", "DDU", "GAYA", "ASN", "HWH"],
    "EASTERN_PATNA": ["NDLS", "CNB", "PRYJ", "DDU", "DNR", "PNBE", "BJU", "MFP", "SPJ", "DBG"],
    "WESTERN_MUMBAI": ["NDLS", "MTJ", "KOTA", "RTM", "BRC", "ST", "MMCT", "CSMT"],
    "WESTERN_AHMEDABAD": ["NDLS", "REWARI", "JP", "AII", "ABR", "PNU", "ADI"],
    "GRAND_TRUNK_CHENNAI": ["NDLS", "AGC", "GWL", "VGLJ", "BPL", "NGP", "BPQ", "KZJ", "BZA", "MAS"],
    "KARNATAKA_BENGALURU": ["NDLS", "AGC", "VGLJ", "BPL", "NGP", "WADI", "GTL", "SBC", "MYS"],
    "NORTHEAST_DIBRUGARH": ["NDLS", "CNB", "PRYJ", "DDU", "PNBE", "KIR", "NJP", "GHY", "DBRG"],
    "KONKAN_KERALA": ["CSMT", "PUNE", "RN", "MAO", "MAQ", "CAN", "CLT", "ERS", "QLN", "TVC"],
    "SOUTHERN_INTERCITY": ["CSMT", "PUNE", "SUR", "WADI", "GTL", "RU", "MAS"],
    "EAST_COAST": ["HWH", "KGP", "ROU", "TATA", "BBS", "KUR", "PURI", "VSKP", "RJY", "BZA", "MAS"],
    "NORTH_JAMMU": ["NDLS", "SRE", "UMB", "CDG", "LDH", "JUC", "ASR", "JAT", "SVDK"],
    "CENTRAL_HOWRAH": ["CSMT", "PUNE", "BSL", "NGP", "DURG", "R", "BSP", "ROU", "TATA", "HWH"],
    "MUMBAI_AHMEDABAD": ["CSMT", "MMCT", "ST", "BRC", "ADI"],
}

# Explicit corridor train protection set
PROTECTED_TRAIN_NUMBERS: Set[str] = {"12034", "12301", "2421"}


def determine_corridor(train_no: str, name: str) -> Optional[List[str]]:
    """Deterministically match a train to a corridor based on name, or return None."""
    n = name.upper()

    # Check specific destinations / keywords in name
    if "MUMBAI" in n or ("TEJAS" in n and "MUMBAI" in n):
        return CORRIDORS["WESTERN_MUMBAI"]
    if "HOWRAH" in n or "SEALDAH" in n or "POORVA" in n:
        return CORRIDORS["EASTERN_TRUNK"]
    if "PATNA" in n or "BIHAR" in n or "MAGADH" in n:
        return CORRIDORS["EASTERN_PATNA"]
    if "DIBRUGARH" in n or "GUWAHATI" in n or "ASSAM" in n:
        return CORRIDORS["NORTHEAST_DIBRUGARH"]
    if "CHENNAI" in n or "TAMIL NADU" in n or "GRAND TRUNK" in n:
        return CORRIDORS["GRAND_TRUNK_CHENNAI"]
    if "BENGALURU" in n or "BANGALORE" in n or "KARNATAKA" in n:
        return CORRIDORS["KARNATAKA_BENGALURU"]
    if "KERALA" in n or "TRIVANDRUM" in n or "KOCHI" in n or "MANGALA" in n:
        return CORRIDORS["KONKAN_KERALA"]
    if "JAMMU" in n or "VAISHNO" in n or "KATRA" in n or "AMRITSAR" in n:
        return CORRIDORS["NORTH_JAMMU"]
    if "AJMER" in n or "JAIPUR" in n or "AHMEDABAD" in n:
        return CORRIDORS["WESTERN_AHMEDABAD"]
    if "PURI" in n or "ORISSA" in n or "NEELACHAL" in n:
        return CORRIDORS["EAST_COAST"]
    if (
        "LUCKNOW" in n
        or "KANPUR" in n
        or "CNB" in n
        or "GOMTI" in n
        or "SHRAM SHAKTI" in n
        or "SHATABDI" in n
    ):
        return CORRIDORS["DELHI_LUCKNOW"]

    # Explicit policy: NEVER guess via hash fallback. Skip unmatched trains.
    logger.warning(
        "Could not determine explicit corridor for train %s (%s). Skipping.",
        train_no,
        name,
    )
    return None


def run(apply: bool = False) -> None:
    """Run route expansion with dry-run safety by default."""
    dry_run = not apply
    if dry_run:
        logger.info(
            "[DRY RUN MODE] No database changes will be committed. Run with --apply to write."
        )
    else:
        logger.info("[APPLY MODE] Changes will be committed to database.")

    db = get_db()
    with db.transaction() as cur:
        # Find all trains that already have routes defined
        cur.execute("SELECT DISTINCT train_no FROM route_stations")
        existing_route_trains = {str(r[0]) for r in cur.fetchall()}

        # Scan for existing corridor sequences to dynamically protect corridor trains
        cur.execute(
            """
            SELECT train_no, GROUP_CONCAT(station_code) as stns
            FROM route_stations
            GROUP BY train_no
            """
        )
        for r in cur.fetchall():
            stns = str(r["stns"] or "")
            if "NDLS" in stns and "CNB" in stns and "LKO" in stns:
                PROTECTED_TRAIN_NUMBERS.add(str(r["train_no"]))

        # Get all trains
        cur.execute("SELECT train_no, name, class, priority FROM trains")
        trains = cur.fetchall()
        logger.info(
            "Found %d trains in database (%d already have routes; %d protected corridor trains).",
            len(trains),
            len(existing_route_trains),
            len(PROTECTED_TRAIN_NUMBERS),
        )

        # Get stations map
        cur.execute("SELECT code, name, lat, lon FROM stations")
        station_map = {r["code"]: dict(r) for r in cur.fetchall()}

        seeded_routes = 0
        skipped_existing = 0
        skipped_protected = 0
        skipped_no_match = 0
        corridor_counts: Dict[str, int] = {}

        for idx, t in enumerate(trains):
            t_no = str(t["train_no"])
            name = str(t["name"])
            priority = int(t["priority"] or 2)

            # Guard 1: Safety check against overwriting protected corridor trains
            if t_no in PROTECTED_TRAIN_NUMBERS:
                skipped_protected += 1
                continue

            # Guard 2: Only INSERT missing trains; NEVER modify or overwrite existing routes
            if t_no in existing_route_trains:
                skipped_existing += 1
                continue

            raw_route = determine_corridor(t_no, name)
            if not raw_route:
                skipped_no_match += 1
                continue

            # Filter to stations that exist in stations table
            valid_stations = [s for s in raw_route if s in station_map]
            if len(valid_stations) < 2:
                logger.warning(
                    "Train %s matched corridor but fewer than 2 valid stations found. Skipping.",
                    t_no,
                )
                skipped_no_match += 1
                continue

            # Reverse half of trains for UP / DN bidirectional operations
            is_up = int(t_no[-1]) % 2 != 0
            route = valid_stations if is_up else list(reversed(valid_stations))

            # Timings
            start_hour = (idx * 3) % 24
            start_minute = (idx * 17) % 60
            curr_time = datetime.datetime(2026, 9, 7, start_hour, start_minute)
            speed_kmh = 95.0 if priority == 1 else 75.0
            speed_km_per_min = speed_kmh / 60.0

            cum_dist = 0.0
            for seq, stn_code in enumerate(route, start=1):
                if seq == 1:
                    sched_arr = None
                    sched_dep = curr_time.strftime("%H:%M")
                    halt_min = 0
                elif seq == len(route):
                    dist_from_prev = 85.0
                    cum_dist += dist_from_prev
                    transit_min = max(2, int(dist_from_prev / speed_km_per_min))
                    curr_time += datetime.timedelta(minutes=transit_min)
                    sched_arr = curr_time.strftime("%H:%M")
                    sched_dep = None
                    halt_min = 0
                else:
                    dist_from_prev = 70.0
                    cum_dist += dist_from_prev
                    transit_min = max(2, int(dist_from_prev / speed_km_per_min))
                    curr_time += datetime.timedelta(minutes=transit_min)
                    sched_arr = curr_time.strftime("%H:%M")
                    halt_min = 2 if priority == 1 else 5
                    curr_time += datetime.timedelta(minutes=halt_min)
                    sched_dep = curr_time.strftime("%H:%M")

                if apply:
                    cur.execute(
                        """
                        INSERT INTO route_stations (train_no, seq, station_code, sched_arr, sched_dep, halt_min, distance_km)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                        """,
                        (t_no, seq, stn_code, sched_arr, sched_dep, halt_min, round(cum_dist, 1)),
                    )

            seeded_routes += 1
            start_stn, end_stn = route[0], route[-1]
            pair_key = f"{start_stn} <-> {end_stn}"
            corridor_counts[pair_key] = corridor_counts.get(pair_key, 0) + 1

        if dry_run:
            logger.info(
                "[DRY RUN COMPLETE] Planned %d new routes (skipped: %d existing, %d protected, %d unmatched). 0 rows written.",
                seeded_routes,
                skipped_existing,
                skipped_protected,
                skipped_no_match,
            )
        else:
            logger.info(
                "[SUCCESS] Seeded %d new train routes into route_stations! (Skipped: %d existing, %d protected, %d unmatched).",
                seeded_routes,
                skipped_existing,
                skipped_protected,
                skipped_no_match,
            )


def main() -> None:
    parser = argparse.ArgumentParser(description="RailTwin-X Pan-India Route Expansion")
    parser.add_argument(
        "--apply",
        action="store_true",
        default=False,
        help="Apply changes to the database. If omitted, runs in safe dry-run mode.",
    )
    args = parser.parse_args()
    run(apply=args.apply)


if __name__ == "__main__":
    main()
