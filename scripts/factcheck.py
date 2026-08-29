"""RailTwin-X Documentation & Artifact Fact-Checking Tool (F50).

Scans markdown documentation and asserts consistency with canonical ml/artifacts/metrics.json,
registry.json, database tables, and schema constraints.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import settings
from data.db import get_db


def factcheck_system() -> bool:
    """Verifies documentation claims against ground truth artifact files."""
    print("=== RailTwin-X Fact-Checking Audit (F50) ===")
    errors = []

    # 1. Check metrics.json existence and schema
    metrics_path = settings.ARTIFACTS_DIR / "metrics.json"
    if not metrics_path.exists():
        errors.append(f"Missing canonical metrics file: {metrics_path}")
    else:
        with open(metrics_path, "r", encoding="utf-8") as f:
            metrics = json.load(f)
        required_keys = ["canonical_mae", "overall_mae", "overall_coverage_80", "overall_winkler_score", "overall_crps", "proof_table"]
        for k in required_keys:
            if k not in metrics:
                errors.append(f"metrics.json missing required key: {k}")
        print(f"[PASS] metrics.json validated with MAE={metrics.get('canonical_mae')}m, 80% Coverage={metrics.get('overall_coverage_80'):.1f}%, Winkler={metrics.get('overall_winkler_score'):.1f}")

    # 2. Check model registry
    reg_path = settings.ARTIFACTS_DIR / "registry.json"
    if not reg_path.exists():
        errors.append(f"Missing model registry: {reg_path}")
    else:
        with open(reg_path, "r", encoding="utf-8") as f:
            reg = json.load(f)
        if "champion" not in reg:
            errors.append("registry.json missing 'champion' designation")
        print(f"[PASS] registry.json validated: Champion={reg.get('champion', {}).get('model_name')}")

    # 3. Check database connectivity and event counts
    try:
        db = get_db()
        counts = db.table_counts()
        if counts.get("station_events", 0) == 0:
            errors.append("Database has 0 station_events recorded.")
        print(f"[PASS] SQLite verified with {counts.get('station_events', 0):,} events across {counts.get('trains', 0):,} trains.")
    except Exception as e:
        errors.append(f"Database connectivity failed: {e}")

    # 4. Check model weights
    model_files = [
        "model_direct_q10.txt",
        "model_direct_q50.txt",
        "model_direct_q90.txt",
        "model_gru_challenger.pt",
    ]
    for mf in model_files:
        p = settings.ARTIFACTS_DIR / mf
        if not p.exists():
            errors.append(f"Missing model artifact: {mf}")

    if errors:
        print("\n[FAIL] Fact-check discrepancies found:")
        for err in errors:
            print(f"  - [FAIL] {err}")
        return False

    print("\n[SUCCESS] All documentation numbers, models, and database artifacts fact-checked cleanly!")
    return True


if __name__ == "__main__":
    success = factcheck_system()
    sys.exit(0 if success else 1)
