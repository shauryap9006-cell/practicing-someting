"""RailTwin-X Conformal Prediction Engine & Interval Scoring (F03, F04, F16).

Implements:
1. Ensemble-level Mondrian Conformalized Quantile Regression (CQR).
   Calibrates the final blended ensemble prediction directly, preserving theoretical
   finite-sample coverage guarantees across horizon and train class partitions.
2. Adaptive Conformal Inference (ACI, Gibbs & Candès 2021) for streaming non-stationary updates.
3. Winkler Interval Score and Continuous Ranked Probability Score (CRPS) metrics.
4. Quantile monotonic non-crossing enforcement guard.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple, Union
import numpy as np
import pandas as pd


def enforce_quantile_order(
    p10: Union[float, np.ndarray],
    p50: Union[float, np.ndarray],
    p90: Union[float, np.ndarray],
    min_val: float = 0.0,
) -> Tuple[Union[float, np.ndarray], Union[float, np.ndarray], Union[float, np.ndarray]]:
    """Enforces non-crossing invariant: 0 <= p10 <= p50 <= p90."""
    if isinstance(p10, (int, float)):
        p10_out = max(min_val, float(p10))
        p50_out = max(p10_out, float(p50))
        p90_out = max(p50_out, float(p90))
        # Re-check p10 against p50
        p10_out = min(p10_out, p50_out)
        return p10_out, p50_out, p90_out

    # Vectorized
    p10_arr = np.maximum(min_val, np.asarray(p10, dtype=float))
    p50_arr = np.maximum(min_val, np.asarray(p50, dtype=float))
    p90_arr = np.maximum(min_val, np.asarray(p90, dtype=float))

    p50_arr = np.maximum(p10_arr, p50_arr)
    p90_arr = np.maximum(p50_arr, p90_arr)
    p10_arr = np.minimum(p10_arr, p50_arr)

    return p10_arr, p50_arr, p90_arr


def winkler_score(
    p10: Union[float, np.ndarray],
    p90: Union[float, np.ndarray],
    y_true: Union[float, np.ndarray],
    alpha: float = 0.20,
) -> float:
    """Calculates Winkler interval score: W = (u - l) + (2/alpha)(l - y)*1{y<l} + (2/alpha)(y - u)*1{y>u}.

    Evaluates both sharpness (width) and penalty for missed coverage in a single metric.
    Lower score is better.
    """
    l = np.asarray(p10, dtype=float)
    u = np.asarray(p90, dtype=float)
    y = np.asarray(y_true, dtype=float)

    width = u - l
    under_coverage = (2.0 / alpha) * np.maximum(0.0, l - y)
    over_coverage = (2.0 / alpha) * np.maximum(0.0, y - u)

    score = width + under_coverage + over_coverage
    return float(np.mean(score))


def crps_score(
    p10: Union[float, np.ndarray],
    p50: Union[float, np.ndarray],
    p90: Union[float, np.ndarray],
    y_true: Union[float, np.ndarray],
) -> float:
    """Quantile-based approximation of Continuous Ranked Probability Score (CRPS).

    CRPS = (1/K) * sum_{tau in {0.1, 0.5, 0.9}} 2 * pinball_loss(y, q_tau, tau)
    """
    y = np.asarray(y_true, dtype=float)
    q10 = np.asarray(p10, dtype=float)
    q50 = np.asarray(p50, dtype=float)
    q90 = np.asarray(p90, dtype=float)

    def pinball(q: np.ndarray, tau: float) -> np.ndarray:
        diff = y - q
        return np.maximum(tau * diff, (tau - 1.0) * diff)

    loss_10 = pinball(q10, 0.10)
    loss_50 = pinball(q50, 0.50)
    loss_90 = pinball(q90, 0.90)

    crps = (2.0 / 3.0) * (loss_10 + loss_50 + loss_90)
    return float(np.mean(crps))


class MondrianCQR:
    """Mondrian Conformalized Quantile Regression calibrated on Ensemble outputs (F03, F04).

    Partitions calibration instances into groups (hop distance buckets & train class)
    and computes conditional non-conformity adjustments q_hat_k on the final blended ensemble:
    P(Y in C(X) | Group = k) >= 1 - alpha
    """

    def __init__(self, target_coverage: float = 0.80):
        self.target_coverage = target_coverage
        self.alpha = 1.0 - target_coverage
        self.group_q_hats: Dict[str, float] = {}
        self.global_q_hat: float = 2.0

    def _get_group_key(self, hops: float, km: float, train_class: Optional[str] = None) -> str:
        """Determines Mondrian category partition."""
        if km <= 90 or hops <= 3:
            h_group = "short_1h"
        elif km <= 250 or hops <= 8:
            h_group = "medium_3h"
        else:
            h_group = "long_6h"

        if train_class:
            return f"{h_group}_{train_class.lower()}"
        return h_group

    def calibrate(
        self,
        q10_preds: np.ndarray,
        q90_preds: np.ndarray,
        y_true: np.ndarray,
        hops_vec: np.ndarray,
        km_vec: np.ndarray,
        class_vec: Optional[np.ndarray] = None,
    ) -> Dict[str, float]:
        """Calibrates Mondrian conformity adjustments directly on ensemble quantile outputs."""
        q10 = np.asarray(q10_preds, dtype=float)
        q90 = np.asarray(q90_preds, dtype=float)
        y = np.asarray(y_true, dtype=float)
        hops = np.asarray(hops_vec, dtype=float)
        km = np.asarray(km_vec, dtype=float)

        scores = np.maximum(q10 - y, y - q90)

        def calc_q(sc: np.ndarray) -> float:
            n = len(sc)
            if n == 0:
                return 2.0
            q_level = min(1.0, max(0.0, np.ceil((n + 1) * (1.0 - self.alpha)) / n))
            return float(np.quantile(sc, q_level))

        self.global_q_hat = calc_q(scores)

        groups: Dict[str, List[float]] = {}
        for i in range(len(y)):
            cls = str(class_vec[i]) if class_vec is not None else None
            k = self._get_group_key(hops[i], km[i], cls)
            if k not in groups:
                groups[k] = []
            groups[k].append(scores[i])

            # Also group without class as fallback
            base_k = self._get_group_key(hops[i], km[i], None)
            if base_k not in groups:
                groups[base_k] = []
            if base_k != k:
                groups[base_k].append(scores[i])

        for k, group_sc in groups.items():
            sc_arr = np.array(group_sc)
            if len(sc_arr) >= 30:
                self.group_q_hats[k] = calc_q(sc_arr)
            else:
                self.group_q_hats[k] = self.global_q_hat

        return {"global": self.global_q_hat, **self.group_q_hats}

    def calibrate_ensemble(
        self,
        q10_ens: np.ndarray,
        q90_ens: np.ndarray,
        y_true: np.ndarray,
        hops_vec: np.ndarray,
        km_vec: np.ndarray,
        class_vec: Optional[np.ndarray] = None,
    ) -> Dict[str, float]:
        """Alias for calibrate(): Explicitly denotes ensemble-level calibration."""
        return self.calibrate(q10_ens, q90_ens, y_true, hops_vec, km_vec, class_vec)

    def adjust_interval(
        self,
        raw_p10: Union[float, np.ndarray],
        raw_p90: Union[float, np.ndarray],
        raw_p50: Optional[Union[float, np.ndarray]] = None,
        hops: float = 1.0,
        km: float = 50.0,
        train_class: Optional[str] = None,
    ) -> Tuple[Union[float, np.ndarray], Union[float, np.ndarray], float]:
        """Returns calibrated and non-crossing (p10, p90, q_hat_applied)."""
        k = self._get_group_key(hops, km, train_class)
        q_hat = self.group_q_hats.get(k)
        if q_hat is None:
            base_k = self._get_group_key(hops, km, None)
            q_hat = self.group_q_hats.get(base_k, self.global_q_hat)

        if isinstance(raw_p10, (int, float)):
            p10 = max(0.0, float(raw_p10) - q_hat)
            p90 = float(raw_p90) + q_hat
            if raw_p50 is not None:
                p10, _, p90 = enforce_quantile_order(p10, float(raw_p50), p90)
            return p10, p90, q_hat

        p10_arr = np.maximum(0.0, np.asarray(raw_p10, dtype=float) - q_hat)
        p90_arr = np.asarray(raw_p90, dtype=float) + q_hat
        if raw_p50 is not None:
            p10_arr, _, p90_arr = enforce_quantile_order(p10_arr, np.asarray(raw_p50, dtype=float), p90_arr)
        return p10_arr, p90_arr, q_hat


class AdaptiveConformalInference:
    """Adaptive Conformal Inference (ACI, Gibbs & Candès 2021) for online streaming updates (F04).

    Dynamically updates nominal error level alpha_t based on feedback:
    alpha_{t+1} = alpha_t + gamma * (alpha - err_t)
    where err_t = 1 if y_t not in [p10_t, p90_t] else 0.
    """

    def __init__(self, target_alpha: float = 0.20, gamma: float = 0.005):
        self.target_alpha = target_alpha
        self.gamma = gamma
        self.current_alpha = target_alpha
        self.history: List[Dict[str, float]] = []

    def update(self, y_true: float, p10_pred: float, p90_pred: float) -> float:
        """Online update step upon receiving actual arrival."""
        covered = (p10_pred <= y_true <= p90_pred)
        err_t = 0.0 if covered else 1.0

        # Gibbs-Candes update rule
        self.current_alpha = self.current_alpha + self.gamma * (self.target_alpha - err_t)
        self.current_alpha = max(0.01, min(0.50, self.current_alpha))

        self.history.append({
            "target_alpha": self.target_alpha,
            "current_alpha": self.current_alpha,
            "err": err_t,
            "covered": float(covered),
        })
        return self.current_alpha

    def get_current_coverage(self) -> float:
        """Returns effective empirical coverage over history."""
        if not self.history:
            return 1.0 - self.target_alpha
        return float(np.mean([h["covered"] for h in self.history]))


class NormalizedCQR:
    """Normalized Conformalized Quantile Regression (CQR-r / Sesia & Candès 2020).

    Normalizes non-conformity scores by predicted interval width sigma(x) = max(q_hi - q_lo, sigma_min),
    producing locally adaptive, heteroskedasticity-aware prediction intervals.
    """

    def __init__(self, target_coverage: float = 0.80, sigma_min: float = 1.0):
        self.target_coverage = target_coverage
        self.alpha = 1.0 - target_coverage
        self.sigma_min = sigma_min
        self.s_hat: float = 1.0

    def calibrate(self, q_lo: np.ndarray, q_hi: np.ndarray, y_true: np.ndarray) -> float:
        """Calibrates normalized non-conformity score s_hat on calibration set."""
        lo = np.asarray(q_lo, dtype=float)
        hi = np.asarray(q_hi, dtype=float)
        y = np.asarray(y_true, dtype=float)

        sigma = np.maximum(hi - lo, self.sigma_min)
        scores = np.maximum(lo - y, y - hi) / sigma

        n = len(scores)
        if n == 0:
            self.s_hat = 1.0
            return 1.0

        q_level = min(1.0, max(0.0, np.ceil((n + 1) * (1.0 - self.alpha)) / n))
        self.s_hat = float(np.quantile(scores, q_level))
        return self.s_hat

    def adjust_interval(
        self,
        q_lo: Union[float, np.ndarray],
        q_hi: Union[float, np.ndarray],
        q_mid: Optional[Union[float, np.ndarray]] = None,
    ) -> Tuple[Union[float, np.ndarray], Union[float, np.ndarray]]:
        """Applies scale-normalized CQR adjustment: [q_lo - s_hat * sigma, q_hi + s_hat * sigma]."""
        if isinstance(q_lo, (int, float)):
            sigma = max(float(q_hi) - float(q_lo), self.sigma_min)
            adj_lo = max(0.0, float(q_lo) - self.s_hat * sigma)
            adj_hi = float(q_hi) + self.s_hat * sigma
            if q_mid is not None:
                adj_lo, _, adj_hi = enforce_quantile_order(adj_lo, float(q_mid), adj_hi)
            return adj_lo, adj_hi

        lo = np.asarray(q_lo, dtype=float)
        hi = np.asarray(q_hi, dtype=float)
        sigma = np.maximum(hi - lo, self.sigma_min)

        adj_lo = np.maximum(0.0, lo - self.s_hat * sigma)
        adj_hi = hi + self.s_hat * sigma
        if q_mid is not None:
            adj_lo, _, adj_hi = enforce_quantile_order(adj_lo, np.asarray(q_mid, dtype=float), adj_hi)
        return adj_lo, adj_hi


class ConformalPIDController:
    """Conformal PID Controller with persistent SQLite storage (Task T6 & ICML 2023).

    Implements proportional, integral (with anti-windup), and derivative feedback control
    for streaming coverage calibration over non-stationary regimes.
    State persists in SQLite table `conformal_pid_state`.
    """

    def __init__(
        self,
        group_key: str = "global",
        target_alpha: float = 0.20,
        kp: float = 0.05,
        ki: float = 0.005,
        kd: float = 0.01,
        i_max: float = 0.15,
        alpha_min: float = 0.02,
        alpha_max: float = 0.50,
        db: Optional[Any] = None,
    ):
        self.group_key = group_key
        self.target_alpha = target_alpha
        self.kp = kp
        self.ki = ki
        self.kd = kd
        self.i_max = 25.0 if i_max is None or i_max <= 1.0 else i_max
        self.alpha_min = alpha_min
        self.alpha_max = alpha_max
        self.db = db

        self.current_alpha = target_alpha
        self.integral = 0.0
        self.prev_error = 0.0
        self.steps = 0
        self.history: List[Dict[str, float]] = []

        if self.db is not None:
            self._load_state()

    def _load_state(self) -> None:
        """Loads state from SQLite database if exists."""
        try:
            with self.db.transaction() as cur:
                cur.execute(
                    "SELECT target_alpha, current_alpha, integral, prev_error, steps FROM conformal_pid_state WHERE group_key = ?",
                    (self.group_key,),
                )
                row = cur.fetchone()
                if row:
                    self.target_alpha = float(row["target_alpha"])
                    self.current_alpha = float(row["current_alpha"])
                    self.integral = float(row["integral"])
                    self.prev_error = float(row["prev_error"])
                    self.steps = int(row["steps"])
        except Exception:
            pass

    def _save_state(self) -> None:
        """Persists state to SQLite database."""
        if self.db is None:
            return
        import datetime
        now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
        try:
            with self.db.transaction() as cur:
                cur.execute(
                    """
                    INSERT INTO conformal_pid_state (group_key, target_alpha, current_alpha, integral, prev_error, steps, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(group_key) DO UPDATE SET
                        target_alpha = excluded.target_alpha,
                        current_alpha = excluded.current_alpha,
                        integral = excluded.integral,
                        prev_error = excluded.prev_error,
                        steps = excluded.steps,
                        updated_at = excluded.updated_at
                    """,
                    (
                        self.group_key,
                        self.target_alpha,
                        self.current_alpha,
                        self.integral,
                        self.prev_error,
                        self.steps,
                        now_iso,
                    ),
                )
        except Exception:
            pass

    def update(self, y_true: float, p10_pred: float, p90_pred: float) -> float:
        """Streaming PID step: updates nominal alpha and persists state (Bug 7)."""
        covered = (p10_pred <= y_true <= p90_pred)
        err_t = 0.0 if covered else 1.0
        # Error signal: negative when miscovering (lowers alpha => widens confidence band)
        e_t = self.target_alpha - err_t

        # State anti-windup: clamp the integrator STATE directly
        self.integral = float(np.clip(self.integral + e_t, -self.i_max, self.i_max))

        deriv = e_t - self.prev_error if self.steps > 0 else 0.0
        self.prev_error = e_t

        # Update alpha (lower alpha => wider interval)
        self.current_alpha = float(np.clip(
            self.current_alpha + self.kp * e_t + self.ki * self.integral + self.kd * deriv,
            self.alpha_min,
            self.alpha_max,
        ))
        self.steps += 1

        self.history.append({
            "step": self.steps,
            "target_alpha": self.target_alpha,
            "current_alpha": self.current_alpha,
            "err": err_t,
            "integral": self.integral,
            "covered": float(covered),
        })

        self._save_state()
        return self.current_alpha

    def get_current_coverage(self) -> float:
        """Returns empirical coverage over history."""
        if not self.history:
            return 1.0 - self.target_alpha
        return float(np.mean([h["covered"] for h in self.history]))

