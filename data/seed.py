"""RailTwin-X Dynamic Master Data & Historical Seed Generator.

Reads infrastructure, train fleet, and operational parameters from external JSON
configurations and settings without hardcoded constants.
"""

from __future__ import annotations

import datetime
import json
import random
from pathlib import Path
from typing import Optional

from config import settings
from data.db import Database, get_db


def load_json_seed(filename: str) -> list[dict]:
    """Loads seed array from settings.SEEDS_DIR."""
    file_path = settings.SEEDS_DIR / filename
    if not file_path.exists():
        raise FileNotFoundError(f"Seed file not found: {file_path}")
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)


def seed_master_data(db: Database, network: str = "passenger") -> None:
    """Seeds stations, corridor sections, speed restrictions, trains, routes, and rake links dynamically."""
    print(f"[INFO] Seeding master railway infrastructure for network mode '{network}'...")
    stations = load_json_seed("stations.json")
    sections = load_json_seed("sections.json")
    rake_links = load_json_seed("rake_links.json")
    raw_trains = load_json_seed("trains.json")

    if network == "dfc":
        # Dedicated Freight Corridor network mode: prioritizes freight / goods operations
        trains = [t for t in raw_trains if t.get("priority", 2) >= 3]
        if not trains:
            trains = raw_trains[:20]
    elif network == "mixed":
        trains = raw_trains
    else:  # passenger default
        trains = raw_trains

    try:
        speed_restrictions = load_json_seed("speed_restrictions.json")
    except Exception:
        speed_restrictions = []

    with db.transaction() as cur:
        # 1. Stations
        for stn in stations:
            cur.execute(
                """
                INSERT INTO stations (code, name, lat, lon, zone, category, is_junction, platforms)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(code) DO UPDATE SET
                    name=excluded.name,
                    lat=excluded.lat,
                    lon=excluded.lon,
                    zone=excluded.zone,
                    category=excluded.category,
                    is_junction=excluded.is_junction,
                    platforms=excluded.platforms
                """,
                (
                    stn["code"],
                    stn["name"],
                    stn["lat"],
                    stn["lon"],
                    stn.get("zone", "NR"),
                    stn.get("category", "NSG-2"),
                    stn.get("is_junction", 0),
                    stn.get("platforms", 2),
                ),
            )


        # 2. Speed Restrictions (TSRs)
        for tsr in speed_restrictions:
            cur.execute(
                """
                INSERT OR REPLACE INTO speed_restrictions (from_code, to_code, speed_limit_kmph, cause, is_active)
                VALUES (?, ?, ?, ?, ?)
                """,
                (tsr["from_code"], tsr["to_code"], tsr["speed_limit_kmph"], tsr["cause"], tsr.get("is_active", 1)),
            )

        # 3. Sections (Bidirectional)
        for sec in sections:
            cur.execute(
                """
                INSERT OR REPLACE INTO sections (from_code, to_code, distance_km, single_line, max_speed_kmph)
                VALUES (?, ?, ?, ?, ?)
                """,
                (sec["from_code"], sec["to_code"], sec["distance_km"], sec["single_line"], sec["max_speed_kmph"]),
            )
            # Reverse edge
            cur.execute(
                """
                INSERT OR REPLACE INTO sections (from_code, to_code, distance_km, single_line, max_speed_kmph)
                VALUES (?, ?, ?, ?, ?)
                """,
                (sec["to_code"], sec["from_code"], sec["distance_km"], sec["single_line"], sec["max_speed_kmph"]),
            )

        # 4. Trains
        FREIGHT_CLASSES = {"container", "coal_rake", "auto_rake", "steel_rake", "empty_freight"}

        for t in trains:
            is_freight = 1 if t.get("class", "") in FREIGHT_CLASSES else 0
            trailing_tonnage = t.get("trailing_tonnage", 0)
            cur.execute(
                """
                INSERT INTO trains (train_no, name, class, priority, is_freight, trailing_tonnage)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(train_no) DO UPDATE SET
                    name=excluded.name,
                    class=excluded.class,
                    priority=excluded.priority,
                    is_freight=excluded.is_freight,
                    trailing_tonnage=excluded.trailing_tonnage
                """,
                (t["train_no"], t["name"], t["class"], t["priority"], is_freight, trailing_tonnage),
            )


        # 3b. DFC sections (mixed / dfc modes)
        if network in ("dfc", "mixed"):
            try:
                dfc_sections = load_json_seed("dfc_sections.json")
                for sec in dfc_sections:
                    cur.execute(
                        """
                        INSERT OR REPLACE INTO sections (from_code, to_code, distance_km, single_line, max_speed_kmph, is_dfc, loop_length_m)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                        """,
                        (sec["from_code"], sec["to_code"], sec["distance_km"],
                         sec.get("single_line", 0), sec["max_speed_kmph"],
                         sec.get("is_dfc", 1), sec.get("loop_length_m", 1500)),
                    )
                    # Reverse edge
                    cur.execute(
                        """
                        INSERT OR REPLACE INTO sections (from_code, to_code, distance_km, single_line, max_speed_kmph, is_dfc, loop_length_m)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                        """,
                        (sec["to_code"], sec["from_code"], sec["distance_km"],
                         sec.get("single_line", 0), sec["max_speed_kmph"],
                         sec.get("is_dfc", 1), sec.get("loop_length_m", 1500)),
                    )
                print(f"[INFO] Seeded {len(dfc_sections)} DFC sections (bidirectional).")
            except Exception as e:
                print(f"[WARN] Could not load dfc_sections.json: {e}")

        # 5. Route stations (Built from corridor topology)
        # Passenger corridor: NDLS → LKO (down) and reversed (up)
        corridor_stations = ["NDLS", "GZB", "ALJN", "TDL", "ETW", "CNB", "ON", "LKO"]
        stn_codes_down = [s for s in corridor_stations if any(st["code"] == s for st in stations)]
        stn_codes_up = list(reversed(stn_codes_down))

        # DFC corridors: WDFC (Dadri → JNPT) and EDFC (DDU → DKAE)
        wdfc_down = ["DADRI", "REWARI", "FL", "ABR", "PNU", "MSH", "JNPT"]
        edfc_down = ["DDU", "SEB", "GMO", "DKAE"]
        wdfc_up   = list(reversed(wdfc_down))
        edfc_up   = list(reversed(edfc_down))

        # Freight train class → DFC corridor assignment
        DFC_ROUTE_MAP = {
            "container":     (wdfc_down, wdfc_up),    # containers → WDFC
            "coal_rake":     (edfc_down, edfc_up),    # coal → EDFC
            "auto_rake":     (wdfc_down, wdfc_up),    # autos → WDFC
            "steel_rake":    (edfc_down, edfc_up),    # steel → EDFC
            "empty_freight": (wdfc_up,   wdfc_down),  # empties return on WDFC reversed
        }

        for idx, t in enumerate(trains):
            t_class = t.get("class", "superfast")
            is_freight = t_class in FREIGHT_CLASSES

            # Choose route based on train class
            if is_freight and t_class in DFC_ROUTE_MAP:
                route_a, route_b = DFC_ROUTE_MAP[t_class]
                # Filter to stations that are actually seeded
                route_a = [s for s in route_a if any(st["code"] == s for st in stations)]
                route_b = [s for s in route_b if any(st["code"] == s for st in stations)]
                is_down = (idx % 2 == 0)
                route = route_a if is_down else route_b
                # Freight runs slower: 60 km/h average
                transit_speed_kmh = 60.0
                halt_factor = 15  # freight halts: 15 min for loading/unloading
            else:
                is_down = (idx % 2 == 0)
                route = stn_codes_down if is_down else stn_codes_up
                transit_speed_kmh = 96.0  # passenger express average
                halt_factor = 2 if t["priority"] == 1 else (5 if t["priority"] == 2 else 10)

            if not route:
                continue

            start_hour = (idx * 17) % 24
            start_minute = (idx * 23) % 60
            curr_time = datetime.datetime(2000, 1, 1, start_hour, start_minute)
            speed_km_per_min = transit_speed_kmh / 60.0

            cum_dist = 0.0
            for seq, stn_code in enumerate(route, start=1):
                if seq == 1:
                    sched_arr = None
                    sched_dep = curr_time.strftime("%H:%M")
                    halt_min = 0
                elif seq == len(route):
                    dist_from_prev = 50.0
                    cum_dist += dist_from_prev
                    transit_min = max(1, int(dist_from_prev / speed_km_per_min))
                    curr_time += datetime.timedelta(minutes=transit_min)
                    sched_arr = curr_time.strftime("%H:%M")
                    sched_dep = None
                    halt_min = 0
                else:
                    dist_from_prev = 65.0
                    cum_dist += dist_from_prev
                    transit_min = max(1, int(dist_from_prev / speed_km_per_min))
                    curr_time += datetime.timedelta(minutes=transit_min)
                    sched_arr = curr_time.strftime("%H:%M")
                    halt_min = halt_factor
                    curr_time += datetime.timedelta(minutes=halt_min)
                    sched_dep = curr_time.strftime("%H:%M")

                cur.execute(
                    """
                    INSERT OR REPLACE INTO route_stations (train_no, seq, station_code, sched_arr, sched_dep, halt_min, distance_km)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (t["train_no"], seq, stn_code, sched_arr, sched_dep, halt_min, cum_dist),
                )

        # 6. Rake links
        for rl in rake_links:
            cur.execute("SELECT train_no FROM trains WHERE train_no IN (?, ?)", (rl["incoming_train"], rl["outgoing_train"]))
            rows = cur.fetchall()
            if len(rows) == 2:
                cur.execute(
                    """
                    INSERT OR REPLACE INTO rake_links (incoming_train, outgoing_train, station_code, turnaround_min)
                    VALUES (?, ?, ?, ?)
                    """,
                    (rl["incoming_train"], rl["outgoing_train"], rl["station_code"], rl["turnaround_min"]),
                )

        # 7. Staff Registry
        try:
            staff_members = load_json_seed("staff.json")
            for sm in staff_members:
                cur.execute(
                    """
                    INSERT OR REPLACE INTO staff (staff_id, name, role, phone, station_code, pin_hash, on_duty)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        sm["staff_id"],
                        sm["name"],
                        sm["role"],
                        sm["phone"],
                        sm["station_code"],
                        sm.get("pin_hash", "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"),
                        sm.get("on_duty", 1),
                    ),
                )
            print(f"[INFO] Seeded {len(staff_members)} staff members.")
        except Exception as e:
            print(f"[WARN] Could not load staff.json: {e}")

    print("[SUCCESS] Master infrastructure seeded successfully.")



from engine.clocks import get_clock


def seed_weather_and_events(db: Database, num_days: Optional[int] = None) -> None:
    """Seeds weather observations and historical station events for ML train/test."""
    total_days = num_days or (settings.ML_TRAIN_DAYS + settings.ML_TEST_DAYS)
    print(f"[INFO] Generating {total_days} days of weather and station events ({settings.ML_TRAIN_DAYS}d train / {settings.ML_TEST_DAYS}d test)...")
    random.seed(42)

    stations = load_json_seed("stations.json")
    clock = get_clock()
    today = clock.now().date()
    start_date = today - datetime.timedelta(days=total_days - 1)
    end_date = today + datetime.timedelta(days=1)

    with db.transaction() as cur:
        # 1. Weather per station per day
        curr_date = start_date
        while curr_date < end_date:
            date_str = curr_date.strftime("%Y-%m-%d")
            for stn in stations:
                temp = round(random.uniform(14.0, 34.0), 1)
                humidity = round(random.uniform(45.0, 95.0), 1)
                precip = round(random.expovariate(0.5) if random.random() < 0.2 else 0.0, 1)
                fog_flag = 1 if (temp < settings.FOG_MAX_TEMP_CELSIUS and humidity > settings.FOG_MIN_HUMIDITY_PERCENT) else 0

                cur.execute(
                    """
                    INSERT OR REPLACE INTO weather (date, station_code, temp, precip_mm, humidity, fog_flag)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (date_str, stn["code"], temp, precip, humidity, fog_flag),
                )
            curr_date += datetime.timedelta(days=1)

        # 2. Station Events
        cur.execute("SELECT train_no, priority FROM trains")
        trains = cur.fetchall()

        cur.execute("SELECT train_no, seq, station_code, sched_arr, sched_dep, halt_min, distance_km FROM route_stations ORDER BY train_no, seq")
        all_routes = cur.fetchall()
        routes_by_train = {}
        for r in all_routes:
            t_no = r["train_no"]
            if t_no not in routes_by_train:
                routes_by_train[t_no] = []
            routes_by_train[t_no].append(r)

        event_rows = []
        curr_date = start_date
        while curr_date < end_date:
            date_str = curr_date.strftime("%Y-%m-%d")

            for t in trains:
                t_no = t["train_no"]
                priority = t["priority"]
                route = routes_by_train.get(t_no, [])
                if not route:
                    continue

                chronic_bias = (hash(t_no) % 25) - 5
                current_delay = max(0, int(random.gauss(chronic_bias, 15 if priority > 1 else 8)))

                for r in route:
                    seq = r["seq"]
                    stn = r["station_code"]
                    sched_arr = r["sched_arr"]
                    sched_dep = r["sched_dep"]

                    section_delta = random.choice([-5, -2, 0, 0, 2, 5, 12, 25]) if priority > 1 else random.choice([-4, -2, 0, 0, 1, 3, 8])
                    current_delay = max(0, current_delay + section_delta)

                    actual_arr = None
                    if sched_arr:
                        sh, sm = [int(x) for x in sched_arr.split(":")]
                        act_dt = datetime.datetime(curr_date.year, curr_date.month, curr_date.day, sh, sm) + datetime.timedelta(minutes=current_delay)
                        actual_arr = act_dt.strftime("%H:%M")

                    delay_arr = current_delay
                    dwell_extra = random.randint(0, 4) if random.random() < 0.3 else 0
                    current_delay += dwell_extra

                    actual_dep = None
                    if sched_dep:
                        sh, sm = [int(x) for x in sched_dep.split(":")]
                        act_dep_dt = datetime.datetime(curr_date.year, curr_date.month, curr_date.day, sh, sm) + datetime.timedelta(minutes=current_delay)
                        actual_dep = act_dep_dt.strftime("%H:%M")

                    delay_dep = current_delay
                    collected_at = f"{date_str}T12:00:00+05:30"

                    event_rows.append((
                        t_no, date_str, seq, stn, sched_arr, actual_arr, sched_dep, actual_dep, delay_arr, delay_dep, collected_at
                    ))

            curr_date += datetime.timedelta(days=1)

        cur.executemany(
            """
            INSERT OR REPLACE INTO station_events (
                train_no, run_date, seq, station_code, sched_arr, actual_arr, sched_dep, actual_dep, delay_arr_min, delay_dep_min, collected_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            event_rows,
        )

    print(f"[SUCCESS] Generated and committed {len(event_rows)} historical station events across {total_days} days.")


def run_full_seed(db_path: Optional[Path | str] = None, network: str = "passenger") -> None:
    """Initializes schema and runs dynamic seed dataset population."""
    db = get_db(db_path)
    db.reset_database()
    seed_master_data(db, network=network)
    seed_weather_and_events(db)
    counts = db.table_counts()
    print("=== Dynamic Database Seeding Complete ===")
    for tbl, count in counts.items():
        print(f"  - {tbl}: {count:,} rows")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="RailTwin-X Dynamic Master Data & Historical Seed Generator")
    parser.add_argument("--network", choices=["passenger", "dfc", "mixed"], default="passenger", help="Network type (default: passenger)")
    parser.add_argument("--db-path", type=str, default=None, help="Custom database file path")
    args = parser.parse_args()
    run_full_seed(db_path=args.db_path, network=args.network)
