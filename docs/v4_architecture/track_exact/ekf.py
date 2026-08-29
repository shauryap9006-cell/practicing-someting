"""On-loco edge fusion: IMU predict @100 Hz, GNSS + odometer update.

State vector: [x, y, v, heading, gyro_bias, odo_bias] (6-DOF)
- x, y: 2D local ENU / Cartesian position (meters)
- v: Forward longitudinal speed (m/s)
- heading: Heading angle in radians (0 = East, pi/2 = North)
- gyro_bias: Yaw gyro rate bias (rad/s)
- odo_bias: Wheel odometer velocity scale/offset bias (m/s)

Features RAIM (Receiver Autonomous Integrity Monitoring) chi-square innovation
testing to reject GNSS spoofing, jamming, and multipath jumps.
"""

from __future__ import annotations

import numpy as np


class EdgeEKF:
    """High-frequency Extended Kalman Filter for locomotive onboard state estimation."""

    def __init__(
        self,
        init_x: float = 0.0,
        init_y: float = 0.0,
        init_v: float = 0.0,
        init_heading: float = 0.0,
        sigma_gnss: float = 3.0,
        sigma_odo: float = 0.3,
        chi2_threshold: float = 5.991,  # chi2, 2 DoF, 95% confidence
    ):
        # State vector: [x, y, v, heading, gyro_bias, odo_bias]
        self.x = np.array([
            float(init_x),
            float(init_y),
            float(init_v),
            float(init_heading),
            0.0,
            0.0,
        ], dtype=float)

        # State covariance P
        self.P = np.diag([
            sigma_gnss ** 2,         # x variance
            sigma_gnss ** 2,         # y variance
            2.0,                     # v variance
            np.deg2rad(5.0) ** 2,    # heading: ±5 deg
            1e-4,                    # gyro bias
            1e-4,                    # odo bias
        ]).astype(float)

        # Process noise covariance Q (continuous spectral density scaled by dt)
        self.Q = np.diag([
            0.5,                     # x noise
            0.5,                     # y noise
            0.2,                     # v accel noise
            np.deg2rad(1.0) ** 2,    # heading yaw noise
            1e-5,                    # gyro bias drift
            1e-5,                    # odo bias drift
        ]).astype(float)

        self.R_gnss = np.diag([sigma_gnss ** 2, sigma_gnss ** 2]).astype(float)
        self.R_odo = np.array([[sigma_odo ** 2]], dtype=float)
        self.chi2_threshold = chi2_threshold
        self.last_gnss_innov_d: float = 0.0
        self.last_gnss_valid: bool = True

    def predict(self, a_fwd: float, gyro_z: float, dt: float) -> None:
        """100 Hz IMU dead-reckoning state & covariance propagation."""
        if dt <= 0.0:
            return

        x = self.x
        # Correct gyro rate with estimated bias
        rate = gyro_z - x[4]
        x[3] += rate * dt
        # Normalize heading to [-pi, pi]
        x[3] = (x[3] + np.pi) % (2 * np.pi) - np.pi

        # Update speed
        x[2] = max(0.0, x[2] + a_fwd * dt)

        # Update position
        cos_h = np.cos(x[3])
        sin_h = np.sin(x[3])
        x[0] += x[2] * cos_h * dt
        x[1] += x[2] * sin_h * dt

        # State transition Jacobian F
        F = np.eye(6, dtype=float)
        F[0, 2] = cos_h * dt
        F[0, 3] = -x[2] * sin_h * dt
        F[1, 2] = sin_h * dt
        F[1, 3] = x[2] * cos_h * dt
        F[3, 4] = -dt

        self.P = F @ self.P @ F.T + self.Q * dt

    def update_gnss(self, z_xy: np.ndarray | list[float] | tuple[float, float]) -> bool:
        """Updates filter with GNSS (x, y) fix.

        Performs RAIM chi-square innovation gating.
        Returns:
            True if innovation passed chi-square gate and state updated.
            False if rejected (spoofing/jamming/multipath spike detected).
        """
        z = np.asarray(z_xy, dtype=float).flatten()[:2]
        H = np.zeros((2, 6), dtype=float)
        H[0, 0] = 1.0
        H[1, 1] = 1.0

        innov = z - self.x[:2]
        S = H @ self.P @ H.T + self.R_gnss

        # Mahalanobis distance / chi2 statistic
        try:
            d = float(innov @ np.linalg.solve(S, innov))
        except np.linalg.LinAlgError:
            d = float("inf")

        self.last_gnss_innov_d = d
        if d > self.chi2_threshold:
            # Integrity check failed: Reject fix to prevent state corruption
            self.last_gnss_valid = False
            return False

        self.last_gnss_valid = True
        try:
            K = self.P @ H.T @ np.linalg.inv(S)
            self.x += K @ innov
            I_KH = np.eye(6, dtype=float) - K @ H
            self.P = I_KH @ self.P @ I_KH.T + K @ self.R_gnss @ K.T
        except np.linalg.LinAlgError:
            return False

        return True

    def update_odo(self, v_obs: float) -> None:
        """Updates filter with wheel odometer / Doppler radar longitudinal speed."""
        H = np.zeros((1, 6), dtype=float)
        H[0, 2] = 1.0  # v
        H[0, 5] = 1.0  # odo_bias

        innov = np.array([float(v_obs) - (self.x[2] + self.x[5])], dtype=float)
        S = H @ self.P @ H.T + self.R_odo
        K = self.P @ H.T / S[0, 0]
        self.x += (K * innov[0]).flatten()
        I_KH = np.eye(6, dtype=float) - K @ H
        self.P = I_KH @ self.P @ I_KH.T + K @ self.R_odo @ K.T

    @property
    def position(self) -> tuple[float, float]:
        """Current (x, y) coordinates."""
        return float(self.x[0]), float(self.x[1])

    @property
    def speed(self) -> float:
        """Current forward speed in m/s."""
        return float(self.x[2])

    @property
    def speed_kmph(self) -> float:
        """Current forward speed in km/h."""
        return float(self.x[2] * 3.6)

    @property
    def heading(self) -> float:
        """Current heading in radians."""
        return float(self.x[3])

    @property
    def heading_deg(self) -> float:
        """Current heading in degrees."""
        return float(np.rad2deg(self.x[3]))
