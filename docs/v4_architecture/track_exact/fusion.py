"""TrackExactEngine: Master Orchestrator for Hierarchical Bayesian Track Identification.

Combines:
- Layer 1: EdgeEKF (100 Hz IMU dead-reckoning + GNSS/Odo updates + RAIM chi-square gate)
- Layer 2: JunctionIMM (Turnout geometry vs mainline TSR braking mode detection)
- Layer 2: RailHMMMapMatcher & MultiHypothesisTracker (Bayesian track probability & ground-truth collapse)
"""

from __future__ import annotations

from dataclasses import dataclass, field
import time
from typing import Any, Dict, List, Optional, Sequence, Tuple
import numpy as np

from engine.track_exact.ekf import EdgeEKF
from engine.track_exact.hmm_mapmatch import RailHMMMapMatcher, TrackSegment
from engine.track_exact.imm import JunctionIMM
from engine.track_exact.mht import MultiHypothesisTracker, TrackHypothesis


@dataclass
class TrackStateEstimate:
    """ATP-grade Track State Estimate produced by the fusion engine."""

    train_no: str
    ts: float
    x: float
    y: float
    v: float
    heading: float
    track_id: str
    p_track: float
    integrity_ok: bool
    mode_probs: Dict[str, float] = field(default_factory=dict)
    hypotheses: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "train_no": self.train_no,
            "ts": self.ts,
            "x": round(self.x, 3),
            "y": round(self.y, 3),
            "v_mps": round(self.v, 2),
            "v_kmph": round(self.v * 3.6, 1),
            "heading_deg": round(float(np.rad2deg(self.heading)), 1),
            "track_id": self.track_id,
            "p_track": round(self.p_track, 4),
            "integrity_ok": self.integrity_ok,
            "mode_probs": {k: round(v, 4) for k, v in self.mode_probs.items()},
            "hypotheses": self.hypotheses,
        }


class TrackExactEngine:
    """Master hierarchical state estimator for an individual train or corridor monitor."""

    def __init__(
        self,
        track_graph: Optional[Any] = None,
        segments: Optional[Sequence[TrackSegment] | Dict[str, TrackSegment]] = None,
        adjacency: Optional[Dict[str, Sequence[str]]] = None,
        init_x: float = 0.0,
        init_y: float = 0.0,
        init_v: float = 0.0,
        init_heading: float = 0.0,
        sigma_gnss: float = 3.0,
        sigma_odo: float = 0.3,
    ):
        # 1. Edge EKF
        self.ekf = EdgeEKF(
            init_x=init_x,
            init_y=init_y,
            init_v=init_v,
            init_heading=init_heading,
            sigma_gnss=sigma_gnss,
            sigma_odo=sigma_odo,
        )

        # 2. Junction IMM
        self.imm = JunctionIMM()

        # 3. Track Graph / Map Matcher setup
        if segments is None and track_graph is not None:
            if hasattr(track_graph, "get_all_track_segments"):
                segments = track_graph.get_all_track_segments()
                adjacency = getattr(track_graph, "segment_adjacency", {})
            elif hasattr(track_graph, "segments"):
                segments = track_graph.segments
                adjacency = getattr(track_graph, "adjacency", {})

        if segments is None:
            # Default parallel 3-track corridor with standard Indian Railways 4.72m spacing
            segments = [
                TrackSegment(id="UP_MAIN", polyline=[(0.0, 0.0), (2000.0, 0.0)], track_type="main", name="Up Main Line"),
                TrackSegment(id="DN_MAIN", polyline=[(0.0, 4.72), (2000.0, 4.72)], track_type="main", name="Down Main Line"),
                TrackSegment(id="LOOP_1", polyline=[(0.0, -4.72), (500.0, -4.72), (1500.0, -4.72), (2000.0, 0.0)], track_type="loop", name="Common Loop 1"),
                TrackSegment(id="PLATFORM_1", polyline=[(500.0, -9.44), (1500.0, -9.44)], track_type="platform", name="Platform 1"),
            ]
            adjacency = {
                "UP_MAIN": ["UP_MAIN", "LOOP_1"],
                "LOOP_1": ["LOOP_1", "UP_MAIN", "PLATFORM_1"],
                "PLATFORM_1": ["PLATFORM_1", "LOOP_1"],
                "DN_MAIN": ["DN_MAIN"],
            }

        self.matcher = RailHMMMapMatcher(segments, adjacency, sigma_gps=sigma_gnss)
        self.mht = MultiHypothesisTracker(self.matcher, sigma=sigma_gnss)
        self.gnss_ok: bool = True

    # ----------------------------------------------------
    # SENSOR EVENT CALLBACKS
    # ----------------------------------------------------

    def on_imu(self, a_fwd: float, gyro_z: float, dt: float = 0.01) -> None:
        """100 Hz IMU packet arrival callback (accel, yaw rate)."""
        self.ekf.predict(a_fwd, gyro_z, dt)

    def on_gnss(self, z_xy: Tuple[float, float] | Sequence[float]) -> bool:
        """1 Hz GNSS position fix arrival callback."""
        self.gnss_ok = self.ekf.update_gnss(z_xy)
        # Update Bayesian track hypotheses with current position estimate & IMM mode
        self.mht.update(self.ekf.position, self.imm.mode_probs)
        return self.gnss_ok

    def on_odo(self, v: float) -> None:
        """10 Hz Wheel odometer / Doppler speed measurement callback."""
        self.ekf.update_odo(v)
        # Step IMM filter
        self.imm.step(v_obs=v, h_obs=self.ekf.heading)

    def on_balise(self, track_id: str) -> None:
        """Kavach RFID Balise reader detection event (Hard ground truth)."""
        self.mht.collapse(track_id, "KAVACH_RFID_BALISE")

    def on_axle(self, track_id: str) -> None:
        """MSDAC Multi-Section Axle Counter occupancy trigger (Hard ground truth)."""
        self.mht.collapse(track_id, "AXLE_COUNTER")

    def on_ei_route(self, track_id: str) -> None:
        """Station Electronic Interlocking route lock event (Hard ground truth)."""
        self.mht.collapse(track_id, "ELECTRONIC_INTERLOCKING")

    # ----------------------------------------------------
    # ESTIMATION OUTPUT
    # ----------------------------------------------------

    def estimate(self, train_no: str = "TRAIN", ts: Optional[float] = None) -> TrackStateEstimate:
        """Generates the current fused track state estimate with uncertainty & integrity."""
        current_ts = ts if ts is not None else time.time()
        track_id, p_track = self.mht.estimate()

        return TrackStateEstimate(
            train_no=train_no,
            ts=current_ts,
            x=float(self.ekf.x[0]),
            y=float(self.ekf.x[1]),
            v=float(self.ekf.x[2]),
            heading=float(self.ekf.x[3]),
            track_id=track_id or "UNKNOWN",
            p_track=float(p_track),
            integrity_ok=self.gnss_ok,
            mode_probs=self.imm.mode_probs,
            hypotheses=[h.to_dict() for h in self.mht.hyps],
        )
