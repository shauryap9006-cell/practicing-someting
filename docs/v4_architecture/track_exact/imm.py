"""Interacting Multiple Model (IMM) filter for junction & speed restriction mode detection.

Solves the brittle heuristic problem (e.g. "28 km/h -> loop line" which fails when
a TSR slows a train on the main line).

Three parallel kinematic models:
1. MAIN_STRAIGHT: Constant Velocity (CV) straight line motion (main line running).
2. DIVERGE_LOOP: Constant Turn Rate with turnout curvature (1:8.5 or 1:12 IR geometry).
3. BRAKE_PLATFORM: Deceleration / braking on straight alignment (platform stop or mainline TSR).
"""

from __future__ import annotations

import numpy as np


class JunctionIMM:
    """3-Mode Interacting Multiple Model filter for turnout & braking detection."""

    MODES = ("MAIN_STRAIGHT", "DIVERGE_LOOP", "BRAKE_PLATFORM")

    # Mode Transition Matrix: PI[i, j] = P(mode_j at t | mode_i at t-1)
    PI_DEFAULT = np.array([
        [0.90, 0.07, 0.03],  # From Straight
        [0.10, 0.85, 0.05],  # From Diverging Curve
        [0.10, 0.05, 0.85],  # From Braking
    ], dtype=float)

    def __init__(
        self,
        kappa_turnout: float = 1.0 / 300.0,  # 1:12 IR turnout geometry (~300m curve radius)
        a_brake: float = 0.35,               # Service braking deceleration (m/s^2)
        dt: float = 1.0,
        pi_matrix: np.ndarray | None = None,
    ):
        self.dt = float(dt)
        self.kappa = float(kappa_turnout)
        self.a_brake = float(a_brake)
        self.PI = np.array(pi_matrix if pi_matrix is not None else self.PI_DEFAULT, dtype=float)

        # Mode probabilities mu: initially uniform [1/3, 1/3, 1/3]
        self.mu = np.ones(3, dtype=float) / 3.0

        # Mode states X: [v, heading] for each of 3 models
        self.X = [np.zeros(2, dtype=float) for _ in range(3)]

        # Mode covariances P
        self.P = [
            np.diag([5.0, np.deg2rad(5.0) ** 2]).astype(float) for _ in range(3)
        ]

        # Measurement noise covariance R: [v_noise, heading_noise]
        self.R = np.diag([0.5 ** 2, np.deg2rad(1.0) ** 2]).astype(float)
        # Process noise covariance Q
        self.Q = np.diag([0.5, np.deg2rad(0.5) ** 2]).astype(float)

    def _predict_mode(self, mode_idx: int, x: np.ndarray) -> np.ndarray:
        """Propagates state [v, heading] under specified kinematic mode."""
        v, h = float(x[0]), float(x[1])
        if mode_idx == 0:
            # Mode 0: MAIN_STRAIGHT (CV, straight)
            return np.array([v, h], dtype=float)
        elif mode_idx == 1:
            # Mode 1: DIVERGE_LOOP (diverging curve: heading rate = v * kappa)
            return np.array([v, h + v * self.kappa * self.dt], dtype=float)
        else:
            # Mode 2: BRAKE_PLATFORM (deceleration on straight line)
            return np.array([max(0.0, v - self.a_brake * self.dt), h], dtype=float)

    def step(self, v_obs: float, h_obs: float) -> dict[str, float]:
        """Executes one full IMM cycle: Interaction -> Filtering -> Mode Probability Update."""
        v_obs = float(v_obs)
        h_obs = float(h_obs)

        # 1. Interaction / Mixing Step
        # c[j] = sum_i(PI[i, j] * mu[i])
        c = self.PI.T @ self.mu
        c = np.maximum(c, 1e-12)

        # Mixed initial states X0[j] and covariances P0[j]
        X0 = []
        P0 = []
        for j in range(3):
            # Mixing weights w_ij = PI[i, j] * mu[i] / c[j]
            w_ij = (self.PI[:, j] * self.mu) / c[j]
            mixed_x = sum(w_ij[i] * self.X[i] for i in range(3))
            mixed_p = sum(
                w_ij[i] * (
                    self.P[i] + np.outer(self.X[i] - mixed_x, self.X[i] - mixed_x)
                )
                for i in range(3)
            ) + self.Q * self.dt
            X0.append(mixed_x)
            P0.append(mixed_p)

        # 2. Mode-Matched Kalman Filter Step & Likelihoods
        L = np.zeros(3, dtype=float)
        for m in range(3):
            xp = self._predict_mode(m, X0[m])
            # Heading innovation normalized to [-pi, pi]
            dh = (h_obs - xp[1] + np.pi) % (2 * np.pi) - np.pi
            innov = np.array([v_obs - xp[0], dh], dtype=float)

            S = P0[m] + self.R
            try:
                S_inv = np.linalg.inv(S)
                det_S = max(1e-12, np.linalg.det(2.0 * np.pi * S))
                exp_term = np.exp(-0.5 * float(innov @ S_inv @ innov))
                L[m] = max(1e-12, exp_term / np.sqrt(det_S))

                K = P0[m] @ S_inv
                self.X[m] = xp + K @ innov
                I_K = np.eye(2, dtype=float) - K
                self.P[m] = I_K @ P0[m] @ I_K.T + K @ self.R @ K.T
            except np.linalg.LinAlgError:
                L[m] = 1e-6
                self.X[m] = xp
                self.P[m] = P0[m]

        # 3. Mode Probability Update
        mu_unnorm = c * L
        sum_mu = np.sum(mu_unnorm)
        if sum_mu > 0:
            self.mu = mu_unnorm / sum_mu
        else:
            self.mu = np.ones(3, dtype=float) / 3.0

        return self.mode_probs

    @property
    def mode_probs(self) -> dict[str, float]:
        """Returns dictionary mapping mode names to probabilities."""
        return {
            mode: float(self.mu[i])
            for i, mode in enumerate(self.MODES)
        }

    @property
    def dominant_mode(self) -> str:
        """Returns the highest probability mode."""
        idx = int(np.argmax(self.mu))
        return self.MODES[idx]
