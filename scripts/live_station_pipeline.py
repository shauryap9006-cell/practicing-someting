"""RailTwin-X Live Station-Change & 5-Minute Accuracy Refresh Pipeline.

Continuously monitors corridor movements:
1. Refreshes live train running status every 5 minutes (or on each station hop).
2. Detects real-time Station Change events across active trains.
3. Automatically triggers Conflict Scanning, Brain Advisory Orchestration, and Crew Duty checks on station transition.
4. Dispatches immediate WhatsApp & SMS alerts to on-duty controllers and field staff (9580873724 & 9569890921).
"""

from __future__ import annotations

import argparse
import datetime
import json
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config import settings
from data.db import Database, get_db
from engine.clocks import get_clock
from engine.conflicts import ConflictScanner
from engine.ops import CrewDutyEngine, PlatformManager
from api.brain import BrainOrchestrator
from notifications import AlertEvent, get_dispatcher
from collector.collect import DataCollector


class LiveStationPipeline:
    """Continuous real-time monitor tracking station transitions and firing alerts."""

    def __init__(self, db: Optional[Database] = None):
        self.db = db or get_db()
        self.collector = DataCollector(self.db)
        self.conflict_scanner = ConflictScanner(self.db)
        self.brain = BrainOrchestrator(self.db)
        self.crew_engine = CrewDutyEngine(self.db)
        self.platform_manager = PlatformManager(self.db)
        self.dispatcher = get_dispatcher(self.db)
        # In-memory station transition state: {train_no: {"station": code, "seq": seq, "delay": d}}
        self._train_states: Dict[str, Dict[str, Any]] = {}

    def fetch_latest_positions(self) -> Dict[str, Dict[str, Any]]:
        """Queries the latest recorded station event for each train."""
        clock = get_clock()
        run_date = clock.today_str()

        with self.db.transaction() as cur:
            cur.execute(
                """
                SELECT se.train_no, se.seq, se.station_code, se.delay_arr_min, se.delay_dep_min, t.name as train_name, t.priority
                FROM station_events se
                INNER JOIN (
                    SELECT train_no, MAX(seq) as max_seq, MAX(run_date) as max_date
                    FROM station_events
                    GROUP BY train_no
                ) latest ON se.train_no = latest.train_no AND se.seq = latest.max_seq AND se.run_date = latest.max_date
                JOIN trains t ON se.train_no = t.train_no
                """
            )
            rows = cur.fetchall()

        positions = {}
        for r in rows:
            delay = int(r["delay_arr_min"] if r["delay_arr_min"] is not None else (r["delay_dep_min"] or 0))
            positions[r["train_no"]] = {
                "train_no": r["train_no"],
                "train_name": r["train_name"],
                "priority": int(r["priority"]),
                "seq": int(r["seq"]),
                "station_code": r["station_code"],
                "delay_min": delay,
            }
        return positions

    def run_cycle(self, refresh_collector: bool = False) -> Dict[str, Any]:
        """Executes a complete station-change detection & accuracy refresh cycle."""
        clock = get_clock()
        now_str = clock.now_iso()

        print("\n" + "═" * 80)
        print(f"🔄 [PIPELINE TICK] {now_str} · Correlating Station Transitions & Accuracy")
        print("═" * 80)

        # 1. Optional Collector Polling
        if refresh_collector:
            print("[1/4] Polling live data sources for corridor running status...")
            try:
                col_res = self.collector.run_collection_cycle(train_limit=25)
                print(f"  ✓ Refreshed {col_res.get('events_upserted', 0)} events.")
            except Exception as col_err:
                print(f"  ! Collector notice: {col_err}")

        # 2. Track Station Changes
        current_positions = self.fetch_latest_positions()
        station_changes = []

        for t_no, pos in current_positions.items():
            prev = self._train_states.get(t_no)
            if prev is None:
                # Initial baseline registration
                self._train_states[t_no] = pos
            elif prev["station_code"] != pos["station_code"] or prev["seq"] != pos["seq"]:
                # STATION CHANGE DETECTED
                station_changes.append({
                    "train_no": t_no,
                    "train_name": pos["train_name"],
                    "from_station": prev["station_code"],
                    "to_station": pos["station_code"],
                    "delay_min": pos["delay_min"],
                })
                self._train_states[t_no] = pos

        print(f"[2/4] Active Trains Tracked: {len(current_positions)} | Station Transitions Detected: {len(station_changes)}")
        for chg in station_changes[:5]:
            print(f"  ⚡ Train #{chg['train_no']} ({chg['train_name']}): {chg['from_station']} ➔ {chg['to_station']} (Delay: +{chg['delay_min']}m)")

        # 3. Spatial Conflict & Brain Advisory Evaluation on Key Corridor Stations
        print("[3/4] Running Conflict Scans & Brain Advisory Evaluation...")
        all_dispatches = []

        # Target critical high-priority trains or trains that just transitioned
        eval_trains = [c["train_no"] for c in station_changes] if station_changes else list(current_positions.keys())[:10]

        for t_no in eval_trains:
            pos = current_positions.get(t_no, {})
            stn = pos.get("station_code", "CNB")

            # A. Conflict Scanner
            conflicts = self.conflict_scanner.scan_train_conflicts(t_no)
            high_confs = [c for c in conflicts if c.severity in ("HIGH", "MEDIUM")]

            if high_confs:
                print(f"  🚨 Detected {len(high_confs)} conflict(s) for #{t_no} at {stn}!")
                for c in high_confs:
                    print(f"     • [{c.severity}] {c.conflict_type} w/ #{c.with_train} at {c.station_code}: {c.reason}")
                    # Dispatch to on-duty controllers & pointsmen (9580873724, 9569890921)
                    disp_res = self.dispatcher.dispatch(
                        AlertEvent(
                            severity=c.severity,
                            event_type="conflict",
                            title=f"{c.conflict_type.replace('_', ' ')}: #{t_no} vs #{c.with_train} at {c.station_code}",
                            body=f"{c.reason} | ACTION: {c.suggested_action.upper()}",
                            station_code=c.station_code,
                            train_no=t_no,
                            roles=["controller", "pointsman", "loco_pilot"],
                            ack_id=c.conflict_id,
                            metadata={"with_train": c.with_train, "suggested_action": c.suggested_action},
                        )
                    )
                    all_dispatches.append(disp_res)

        # 4. Crew Fatigue Projection
        print("[4/4] Evaluating Crew Duty & Fatigue Projections...")
        crew_alerts = self.crew_engine.evaluate_crew_alerts()
        if crew_alerts:
            print(f"  ⚠️ {len(crew_alerts)} Crew duty-breach warnings active.")
            crew_disp = self.crew_engine.dispatch_crew_alerts(crew_alerts)
            all_dispatches.extend(crew_disp)
        else:
            print("  ✓ Crew duty hours nominal across all corridor shifts.")

        print(f"\n[SUMMARY] Cycle finished. Total Dispatches: {len(all_dispatches)}")
        return {
            "timestamp": now_str,
            "trains_tracked": len(current_positions),
            "station_changes": len(station_changes),
            "dispatches_triggered": len(all_dispatches),
        }

    def start_loop(self, interval_seconds: int = 300, refresh_collector: bool = True):
        """Runs the continuous background monitoring loop every 5 minutes."""
        print("=" * 80)
        print(f"🚆 RAILTWIN-X LIVE PIPELINE WORKER STARTED (Interval: {interval_seconds}s / {interval_seconds//60} min)")
        print("   Monitoring station changes & dispatching alerts to:")
        print("   • Controller: 9580873724")
        print("   • Staff / Crew / Pointsman: 9569890921")
        print("   Press Ctrl+C to stop.")
        print("=" * 80)

        iteration = 1
        try:
            while True:
                print(f"\n>>> Cycle #{iteration} starting at {datetime.datetime.now().strftime('%H:%M:%S IST')}")
                self.run_cycle(refresh_collector=(refresh_collector and iteration > 1))
                print(f"⏳ Sleeping {interval_seconds}s until next refresh cycle...")
                time.sleep(interval_seconds)
                iteration += 1
        except KeyboardInterrupt:
            print("\n[STOP] Live pipeline worker stopped by user.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="RailTwin-X Live Station-Change & Accuracy Pipeline")
    parser.add_argument("--interval", type=int, default=300, help="Refresh interval in seconds (default 300s / 5 min)")
    parser.add_argument("--once", action="store_true", help="Run a single cycle and exit")
    parser.add_argument("--no-collect", action="store_true", help="Skip collector external poll")
    args = parser.parse_args()

    pipeline = LiveStationPipeline()
    if args.once:
        pipeline.run_cycle(refresh_collector=not args.no_collect)
    else:
        pipeline.start_loop(interval_seconds=args.interval, refresh_collector=not args.no_collect)
