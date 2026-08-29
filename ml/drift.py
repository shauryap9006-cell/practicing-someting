"""RailTwin-X ML Drift Monitor — Phase 7 (MLOps).

Implements Population Stability Index (PSI) to detect feature distribution
drift between the training reference window and the current live scoring window.

PSI thresholds (industry standard):
  PSI < 0.10  → No significant drift (GREEN)
  PSI 0.10-0.25 → Moderate drift, monitor (AMBER)
  PSI > 0.25  → Significant drift, trigger retrain (RED)

Run standalone:
    python -m ml.drift
"""

from __future__ import annotations

import datetime
import json
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from config import settings
from data.db import get_db


# ---------------------------------------------------------------------------
# PSI calculation
# ---------------------------------------------------------------------------

def _psi_score(expected: np.ndarray, actual: np.ndarray, n_bins: int = 10) -> float:
    """Computes Population Stability Index between two 1-D arrays.

    PSI = Σ (Actual% - Expected%) × ln(Actual% / Expected%)

    Bins are defined on the training (expected) distribution.
    """
    # Remove NaN
    expected = expected[~np.isnan(expected)]
    actual = actual[~np.isnan(actual)]

    if len(expected) == 0 or len(actual) == 0:
        return 0.0

    # Bin edges on training data
    breakpoints = np.percentile(expected, np.linspace(0, 100, n_bins + 1))
    breakpoints = np.unique(breakpoints)  # deduplicate edge case
    if len(breakpoints) < 2:
        return 0.0

    exp_counts, _ = np.histogram(expected, bins=breakpoints)
    act_counts, _ = np.histogram(actual, bins=breakpoints)

    exp_pct = exp_counts / len(expected)
    act_pct = act_counts / len(actual)

    # Clip to avoid log(0)
    eps = 1e-6
    exp_pct = np.clip(exp_pct, eps, None)
    act_pct = np.clip(act_pct, eps, None)

    psi = np.sum((act_pct - exp_pct) * np.log(act_pct / exp_pct))
    return float(psi)


# ---------------------------------------------------------------------------
# CUSUM & ADWIN Change-Point Detectors (F28, F29)
# ---------------------------------------------------------------------------

class CUSUMDetector:
    """Two-sided Cumulative Sum (CUSUM) change-point detector for shift in mean delay."""

    def __init__(self, target_mean: float = 0.0, threshold: float = 5.0, drift: float = 1.0):
        self.target_mean = target_mean
        self.threshold = threshold
        self.drift = drift
        self.s_pos = 0.0
        self.s_neg = 0.0
        self.change_points: List[int] = []

    def update(self, val: float, step: int = 0) -> bool:
        """Updates CUSUM accumulator and returns True if drift threshold exceeded."""
        diff = val - self.target_mean
        self.s_pos = max(0.0, self.s_pos + diff - self.drift)
        self.s_neg = max(0.0, self.s_neg - diff - self.drift)

        if self.s_pos > self.threshold or self.s_neg > self.threshold:
            self.change_points.append(step)
            self.s_pos = 0.0
            self.s_neg = 0.0
            return True
        return False


class ADWINDetector:
    """Adaptive Windowing (ADWIN) online drift detector with Hoeffding bounds."""

    def __init__(self, delta: float = 0.002, max_window: int = 1000):
        self.delta = delta
        self.max_window = max_window
        self.window: List[float] = []

    def update(self, val: float) -> bool:
        """Adds observation to window and checks sub-window mean divergence."""
        self.window.append(val)
        if len(self.window) > self.max_window:
            self.window.pop(0)

        n = len(self.window)
        if n < 30:
            return False

        # Split window into two halves
        mid = n // 2
        w0 = np.array(self.window[:mid])
        w1 = np.array(self.window[mid:])

        n0, n1 = len(w0), len(w1)
        m0, m1 = np.mean(w0), np.mean(w1)

        # Hoeffding epsilon bound
        m = 1.0 / (1.0 / n0 + 1.0 / n1)
        eps = np.sqrt((1.0 / (2.0 * m)) * np.log(4.0 / self.delta))

        if abs(m0 - m1) > eps:
            # Cut older window half
            self.window = self.window[mid:]
            return True
        return False


# ---------------------------------------------------------------------------
# Drift report dataclass
# ---------------------------------------------------------------------------


@dataclass
class FeatureDriftResult:
    feature: str
    psi: float
    status: str       # "GREEN" | "AMBER" | "RED"
    expected_mean: float
    actual_mean: float
    expected_std: float
    actual_std: float


@dataclass
class DriftReport:
    generated_at: str
    reference_window_days: int
    live_window_days: int
    total_features: int
    red_features: int
    amber_features: int
    green_features: int
    overall_status: str
    features: List[FeatureDriftResult]

    def to_dict(self) -> dict:
        d = asdict(self)
        return d

    def save(self, path: Optional[Path] = None) -> Path:
        out = path or (settings.ARTIFACTS_DIR / "drift_report.json")
        out.parent.mkdir(parents=True, exist_ok=True)
        with open(out, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2)
        return out


# ---------------------------------------------------------------------------
# PSI Drift Monitor
# ---------------------------------------------------------------------------

class PSIDriftMonitor:
    """Computes per-feature PSI drift between training reference and recent live window."""

    PSI_AMBER = 0.10
    PSI_RED   = 0.25

    def __init__(
        self,
        db=None,
        reference_days: int = settings.ML_TRAIN_DAYS,
        live_days: int = 3,
    ):
        self.db = db or get_db()
        self.reference_days = reference_days
        self.live_days = live_days

    def _load_snapshots(self, start_date: str, end_date: str) -> pd.DataFrame:
        """Loads snapshot rows (station_events joined with route) for a date window."""
        with self.db.transaction() as cur:
            cur.execute(
                """
                SELECT
                    se.delay_arr_min  AS current_delay,
                    se.delay_dep_min  AS delay_dep,
                    rs.seq            AS hops_remaining,
                    rs.distance_km    AS km_remaining,
                    CAST(strftime('%H', substr(se.sched_arr, 1, 5)) AS INT) AS hour_of_day,
                    t.priority        AS train_priority,
                    w.fog_flag        AS fog_flag_target,
                    w.precip_mm       AS rain_mm_target
                FROM station_events se
                JOIN route_stations rs ON rs.train_no = se.train_no AND rs.seq = se.seq
                JOIN trains t ON t.train_no = se.train_no
                LEFT JOIN weather w ON w.date = se.run_date AND w.station_code = se.station_code
                WHERE se.run_date BETWEEN ? AND ?
                  AND se.delay_arr_min IS NOT NULL
                  AND rs.seq > 1
                """,
                (start_date, end_date),
            )
            rows = cur.fetchall()

        if not rows:
            return pd.DataFrame()
        return pd.DataFrame([dict(r) for r in rows])

    def run(self) -> DriftReport:
        """Runs PSI drift analysis and returns a DriftReport."""
        today = datetime.date.today()

        # Reference window: training split
        ref_end   = today - datetime.timedelta(days=self.live_days)
        ref_start = ref_end - datetime.timedelta(days=self.reference_days)

        # Live window: last N days
        live_start = today - datetime.timedelta(days=self.live_days)
        live_end   = today

        ref_df  = self._load_snapshots(ref_start.isoformat(), ref_end.isoformat())
        live_df = self._load_snapshots(live_start.isoformat(), live_end.isoformat())

        features_to_monitor = [
            "current_delay", "hops_remaining", "km_remaining",
            "hour_of_day", "train_priority", "fog_flag_target", "rain_mm_target",
        ]

        results: List[FeatureDriftResult] = []

        for feat in features_to_monitor:
            if feat not in ref_df.columns or feat not in live_df.columns:
                continue

            exp = ref_df[feat].dropna().values.astype(float)
            act = live_df[feat].dropna().values.astype(float) if not live_df.empty else np.array([])

            psi = _psi_score(exp, act)

            if psi >= self.PSI_RED:
                status = "RED"
            elif psi >= self.PSI_AMBER:
                status = "AMBER"
            else:
                status = "GREEN"

            results.append(
                FeatureDriftResult(
                    feature=feat,
                    psi=round(psi, 4),
                    status=status,
                    expected_mean=round(float(np.mean(exp)), 3) if len(exp) else 0.0,
                    actual_mean=round(float(np.mean(act)), 3) if len(act) else 0.0,
                    expected_std=round(float(np.std(exp)), 3) if len(exp) else 0.0,
                    actual_std=round(float(np.std(act)), 3) if len(act) else 0.0,
                )
            )

        red_count   = sum(1 for r in results if r.status == "RED")
        amber_count = sum(1 for r in results if r.status == "AMBER")

        overall = "RED" if red_count > 0 else ("AMBER" if amber_count > 0 else "GREEN")

        report = DriftReport(
            generated_at=datetime.datetime.now().isoformat(),
            reference_window_days=self.reference_days,
            live_window_days=self.live_days,
            total_features=len(results),
            red_features=red_count,
            amber_features=amber_count,
            green_features=len(results) - red_count - amber_count,
            overall_status=overall,
            features=results,
        )

        if overall == "RED" or red_count > 0:
            self.emit_drift_alert(report)

        return report

    def emit_drift_alert(self, report: DriftReport) -> None:
        """Emits system notification and audit record upon significant feature drift breach (F29)."""
        try:
            db = get_db()
            with db.transaction() as cur:
                cur.execute(
                    """
                    INSERT INTO notifications (
                        event_type, target_role, severity, title, message, payload_json, state, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        "DRIFT_ALERT",
                        "mlops",
                        "critical" if report.overall_status == "RED" else "warning",
                        "ML Feature Distribution Drift Detected",
                        f"CRITICAL DRIFT BREACH: {report.red_features} features exceeded PSI threshold 0.25 (Status: {report.overall_status})",
                        json.dumps({"red_features": report.red_features, "overall_status": report.overall_status}),
                        "queued",
                        datetime.datetime.now().isoformat(),
                    ),
                )
        except Exception as e:
            print(f"[WARN] Failed to emit drift notification: {e}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("=== RailTwin-X PSI Drift Monitor ===")
    monitor = PSIDriftMonitor()
    report = monitor.run()
    saved = report.save()
    print(f"Overall status: {report.overall_status}")
    print(f"Features monitored: {report.total_features}")
    print(f"  GREEN: {report.green_features}  AMBER: {report.amber_features}  RED: {report.red_features}")
    for r in report.features:
        flag = "⚠️  " if r.status != "GREEN" else "   "
        print(f"  {flag}{r.feature:35s}  PSI={r.psi:.4f}  [{r.status}]")
    print(f"\nReport saved -> {saved}")
    if report.overall_status == "RED":
        print("[ACTION REQUIRED] Significant drift detected — consider retraining.")
    elif report.overall_status == "AMBER":
        print("[MONITOR] Moderate drift detected — watch closely.")
    else:
        print("[OK] No significant drift detected.")
