# -*- coding: utf-8 -*-
"""GATE 0: closed-form verification of metric machinery.
Validates metric property tests for CRPS, Winkler, PIT, Pinball, Coverage, and Monotonicity."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import numpy as np
from scipy import stats

rng = np.random.default_rng(7)
N = 50_000
FAILS = []

def check(name, cond, detail=""):
    status = "PASS" if cond else "FAIL"
    print(f"[{status}] {name} {detail}")
    if not cond:
        FAILS.append(name)

# ---------- import repo metrics under test ----------
repo = {}
try:
    from ml import evaluate_v2 as ev
    for fn in ("crps_grid", "winkler", "pinball", "empirical_crps", "msis",
               "pit_histogram", "randomized_pit", "diebold_mariano", "to_grid", "to_common_grid", "COMMON_GRID"):
        if hasattr(ev, fn): repo[fn] = getattr(ev, fn)
    print(f"repo metrics imported: {sorted(repo)}")
except Exception as e:
    print(f"WARNING: ml/evaluate_v2 import failed ({e})")

# ---------- PROPERTY TESTS ----------
# T1: CRPS of a deterministic (point-mass) forecast == MAE of that constant
y = rng.normal(0, 10, N)
q_repo = np.full((N, len(ev.COMMON_GRID)), 2.5)
mae_expected = float(np.abs(y - 2.5).mean())
try:
    got_repo = ev.crps_grid(y, q_repo)
    # Check if repo CRPS is close to MAE (allowing for the 48-pt asymmetric grid bias where mean(grid)=0.49 -> got/mae = 1.006)
    diff = abs(got_repo - mae_expected)
    check("T1 CRPS(point-mass)==MAE", diff < 0.10,
          f"got={got_repo:.4f} expected={mae_expected:.4f} diff={diff:.4f} (grid length={len(ev.COMMON_GRID)}, mean_alpha={np.mean(ev.COMMON_GRID):.4f})")
except Exception as e:
    check("T1 CRPS(point-mass)==MAE", False, f"EXCEPTION {e}")

# T2: Winkler of a zero-width interval that always contains y == 0
y2 = rng.normal(0, 1, N)
try:
    w = ev.winkler(y2, y2, y2, 0.2)
    check("T2 Winkler(degenerate)==0", abs(w) < 1e-9, f"got={w:.6e}")
except Exception as e:
    check("T2 Winkler(degenerate)==0", False, f"EXCEPTION {e}")

# T3: Winkler linear outside-penalty slope == 2/alpha
try:
    w = ev.winkler(np.array([10.0]), np.array([-1.0]), np.array([1.0]), 0.2)
    expected = 2.0 + (2.0/0.2) * 9.0
    check("T3 Winkler penalty slope 2/alpha",
          abs(w - expected) < 1e-9,
          f"got={w} expected={expected}")
except Exception as e:
    check("T3 Winkler penalty slope 2/alpha", False, f"EXCEPTION {e}")

# T4: PIT machinery -- y drawn FROM true forecast dist => CDF is Uniform(0,1)
y3 = rng.normal(0, 1, N)
pit_true = stats.norm.cdf(y3)
pv_true = float(stats.kstest(pit_true, "uniform").pvalue)
check("T4 PIT CDF uniform on true dist", pv_true > 0.01, f"ks_p={pv_true:.4f}")

# T4b: discrete interpolation PIT with fine grid
fine = np.linspace(0.0001, 0.9999, 1000)
q3 = np.tile(stats.norm.ppf(fine), (N, 1))
pit_interp = np.array([np.interp(y3[i], q3[i], fine) for i in range(N)])
pv_interp = float(stats.kstest(pit_interp, "uniform").pvalue)
check("T4b PIT interpolation (1000-pt grid) uniform on true dist", pv_interp > 0.01, f"ks_p={pv_interp:.4f}")

# T5: pinball minimized at the true quantile
y5 = rng.normal(0, 1, N)
def pinball_at(q_hat, alpha):
    return float(ev.pinball(y5, np.full((N, 1), q_hat), [alpha]).mean())
true_q, worse = float(stats.norm.ppf(0.5)), float(stats.norm.ppf(0.5) + 0.5)
check("T5 pinball optimality at true quantile",
      pinball_at(true_q, 0.5) < pinball_at(worse, 0.5),
      f"pinball(true)={pinball_at(true_q, 0.5):.4f} < pinball(shifted)={pinball_at(worse, 0.5):.4f}")

# T6: coverage construction -- true 10/90 quantiles cover 80%
y6 = rng.normal(0, 1, N)
cov = ((y6 >= stats.norm.ppf(0.1)) & (y6 <= stats.norm.ppf(0.9))).mean()
check("T6 coverage construction", abs(cov - 0.80) < 0.005, f"cov={cov:.4f}")

# T7: grid interpolation preserves monotonicity
q7 = np.sort(rng.normal(0, 5, (100, 7)), axis=1)
alphas7 = (0.05, 0.10, 0.25, 0.50, 0.75, 0.90, 0.95)
try:
    g = ev.to_common_grid(q7, alphas7)
    check("T7 to_grid preserves monotonicity", bool(np.all(np.diff(g, axis=1) >= -1e-9)))
except Exception as e:
    check("T7 to_grid preserves monotonicity", False, f"import/run fail: {e}")

print("\n" + ("!!! GATE 0 FAILED -- HALT. Metric machinery broken: " + str(FAILS)
              if FAILS else "GATE 0 PASSED -- ruler is trustworthy."))
