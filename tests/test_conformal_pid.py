"""Unit and property tests for Conformal PID and Normalized CQR (Task T6)."""
from __future__ import annotations

import numpy as np
import pytest

from data.db import Database
from ml.conformal import ConformalPIDController, NormalizedCQR, AdaptiveConformalInference


def test_conformal_pid_faster_convergence_than_vanilla_aci():
    """PID controller adapts faster with less overshoot during sudden distribution drift."""
    rng = np.random.RandomState(42)
    n_steps = 300
    target_alpha = 0.20

    # Simulate drift: first 100 steps error rate ~0.20, then 100 steps error rate ~0.40, then 100 steps error rate ~0.10
    err_probs = [0.20] * 100 + [0.40] * 100 + [0.10] * 100
    errors = [rng.rand() < p for p in err_probs]

    pid = ConformalPIDController(target_alpha=target_alpha, kp=0.05, ki=0.005, kd=0.01)
    aci = AdaptiveConformalInference(target_alpha=target_alpha, gamma=0.005)

    for i, is_err in enumerate(errors):
        # If is_err is True, y_true is outside interval
        y_val = 100.0 if is_err else 5.0
        pid.update(y_true=y_val, p10_pred=0.0, p90_pred=10.0)
        aci.update(y_true=y_val, p10_pred=0.0, p90_pred=10.0)

    # PID should have lower absolute deviation from optimal target during drift transition
    pid_alphas = np.array([h["current_alpha"] for h in pid.history])
    aci_alphas = np.array([h["current_alpha"] for h in aci.history])

    # After step 120 (into high-error regime), PID should react faster (lower nominal alpha -> wider interval)
    assert pid_alphas[120] < aci_alphas[120]


def test_conformal_pid_sqlite_persistence(tmp_path):
    """PID state persists across process restarts and continues step accumulation."""
    db_path = tmp_path / "test_pid.db"
    db = Database(db_path)
    db.init_schema()

    # Migration table
    with db.transaction() as cur:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS conformal_pid_state (
                group_key TEXT PRIMARY KEY,
                target_alpha REAL NOT NULL DEFAULT 0.20,
                current_alpha REAL NOT NULL DEFAULT 0.20,
                integral REAL NOT NULL DEFAULT 0.0,
                prev_error REAL NOT NULL DEFAULT 0.0,
                steps INTEGER NOT NULL DEFAULT 0,
                updated_at TEXT NOT NULL
            )
            """
        )

    # Process 1: run 15 updates
    pid1 = ConformalPIDController(group_key="test_corridor", target_alpha=0.20, db=db)
    for _ in range(15):
        pid1.update(y_true=5.0, p10_pred=0.0, p90_pred=10.0)

    saved_alpha = pid1.current_alpha
    saved_steps = pid1.steps
    assert saved_steps == 15

    # Process 2: simulate cold start reload
    pid2 = ConformalPIDController(group_key="test_corridor", target_alpha=0.20, db=db)
    assert pid2.steps == 15
    assert np.isclose(pid2.current_alpha, saved_alpha)

    # Continue updating
    pid2.update(y_true=100.0, p10_pred=0.0, p90_pred=10.0)
    assert pid2.steps == 16


def test_normalized_cqr_scale_adaptation():
    """Normalized CQR adapts scale proportionally to heteroskedastic width sigma(x)."""
    ncqr = NormalizedCQR(target_coverage=0.80)

    # Calib set with narrow and wide predictions
    q_lo = np.array([0.0, 0.0, 0.0, 0.0, 0.0])
    q_hi = np.array([10.0, 10.0, 20.0, 20.0, 20.0])
    y = np.array([5.0, 12.0, 10.0, 22.0, 25.0])

    s_hat = ncqr.calibrate(q_lo, q_hi, y)
    assert s_hat > 0.0

    # Test adjustment on narrow vs wide interval
    adj_lo_narrow, adj_hi_narrow = ncqr.adjust_interval(0.0, 10.0, 5.0)
    adj_lo_wide, adj_hi_wide = ncqr.adjust_interval(0.0, 50.0, 25.0)

    width_narrow = adj_hi_narrow - adj_lo_narrow
    width_wide = adj_hi_wide - adj_lo_wide

    # Wide interval should scale wider than narrow interval
    assert width_wide > width_narrow


def test_conformal_pid_state_anti_windup_recovery():
    """State anti-windup clamping guarantees fast recovery (<150 steps) after extended saturation (Bug 7)."""
    pid = ConformalPIDController(target_alpha=0.20, kp=0.05, ki=0.005, kd=0.01, i_max=25.0)

    # 1. 500 consecutive misses (severe saturation event like multi-day fog)
    for _ in range(500):
        pid.update(y_true=100.0, p10_pred=0.0, p90_pred=10.0)

    assert pid.integral <= 25.0  # State clamped at i_max, not 400.0

    # 2. 500 consecutive covers - should recover quickly without huge integral lag
    recovered_step = None
    for step in range(1, 501):
        pid.update(y_true=5.0, p10_pred=0.0, p90_pred=10.0)
        # Check if alpha is recovering back towards nominal
        if pid.current_alpha >= 0.15:
            recovered_step = step
            break

    assert recovered_step is not None
    assert recovered_step < 150, f"Recovery took {recovered_step} steps >= 150 steps due to integrator windup"

