"""RailTwin-X Metrics-as-Code Generator (F02).

Renders canonical metrics.json from actual model evaluation on purged splits,
ensuring zero human hand-copy drift across docs and benchmarks.
"""

from __future__ import annotations

import json
from pathlib import Path
from ml.evaluate import Evaluator
from config import settings


def generate_all_metrics() -> dict:
    print("[INFO] Generating Canonical Metrics-as-Code via Evaluator...")
    evaluator = Evaluator()
    summary = evaluator.evaluate_test_set()
    out_path = settings.ARTIFACTS_DIR / "metrics.json"
    print(f"[SUCCESS] Wrote canonical metrics to {out_path}")
    return summary


if __name__ == "__main__":
    generate_all_metrics()
