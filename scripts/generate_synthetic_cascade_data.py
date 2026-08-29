"""RailTwin-X Synthetic Cascade Data Generator (SimPy Engine).

Runs parameterized discrete-event simulations over the corridor with stochastic shocks,
generating causal attribution training records for the exact sim_ledger table.

Usage:
    python scripts/generate_synthetic_cascade_data.py [--runs 100] [--hours 12.0]
"""

from __future__ import annotations

import argparse
import os
import random
import sys
from pathlib import Path
from typing import Optional

# Ensure root directory is on PYTHONPATH
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from data.db import Database, get_db
from engine.simulator import CascadeSimulator


def generate_synthetic_simulations(
    db: Optional[Database] = None,
    num_runs: int = 100,
    hours_per_run: float = 12.0,
) -> dict:
    """Runs multiple discrete-event simulations with diverse operational shocks."""
    target_db = db or get_db()
    simulator = CascadeSimulator(target_db)

    with target_db.transaction() as cur:
        cur.execute("SELECT train_no FROM trains")
        train_pool = [r["train_no"] for r in cur.fetchall()]

        cur.execute("SELECT code FROM stations WHERE is_junction = 1")
        junction_pool = [r["code"] for r in cur.fetchall()] or ["CNB", "GZB", "TDL", "ALJN", "ETW"]

        cur.execute("SELECT from_code, to_code FROM sections")
        section_pool = [(r["from_code"], r["to_code"]) for r in cur.fetchall()]

    print(f"[INFO] Launching {num_runs} cascade simulation runs ({hours_per_run}h each)...")
    total_ledger_events = 0

    for i in range(1, num_runs + 1):
        injected = {}
        shock_trains = random.sample(train_pool, min(len(train_pool), random.randint(1, 4)))
        for tr in shock_trains:
            stn = random.choice(junction_pool)
            shock_delay = random.choice([15, 25, 40, 60, 90, 120])
            injected[tr] = {stn: shock_delay}

        tsrs = {}
        if section_pool and random.random() < 0.6:
            chosen_sec = random.choice(section_pool)
            speed_factor = random.choice([0.4, 0.5, 0.6, 0.75])
            tsrs[chosen_sec] = speed_factor

        run_id, events, delays = simulator.run_simulation(
            injected_delays=injected,
            active_tsrs=tsrs,
            simulation_hours=hours_per_run,
        )
        total_ledger_events += len(events)
        if i % 25 == 0 or i == num_runs:
            print(f"  [Run {i:03d}/{num_runs:03d}] Generated {len(events)} events (Cumulative: {total_ledger_events:,} ledger rows)")

    print(f"[SUCCESS] Completed {num_runs} simulation runs. Total ledger events added: {total_ledger_events:,}")
    return {
        "runs_executed": num_runs,
        "total_ledger_events_generated": total_ledger_events,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate synthetic cascade delay datasets with SimPy.")
    parser.add_argument("--runs", type=int, default=100, help="Number of simulation runs (default: 100)")
    parser.add_argument("--hours", type=float, default=12.0, help="Hours per simulation (default: 12.0)")
    args = parser.parse_args()

    summary = generate_synthetic_simulations(num_runs=args.runs, hours_per_run=args.hours)
    print("=== Simulation Generation Summary ===")
    for k, v in summary.items():
        print(f"  {k}: {v}")
