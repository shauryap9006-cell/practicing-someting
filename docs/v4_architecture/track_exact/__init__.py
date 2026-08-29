"""RailTwin-X Hierarchical Bayesian Track Identification Engine (TRACK-EXACT).

Layer 1: EdgeEKF (100 Hz IMU dead-reckoning + GNSS/Odometer update + RAIM chi-square gate)
Layer 2: RailHMMMapMatcher, JunctionIMM, MultiHypothesisTracker
Layer 3: TrackExactEngine orchestrator & TrackStateEstimate
"""

from engine.track_exact.ekf import EdgeEKF
from engine.track_exact.hmm_mapmatch import RailHMMMapMatcher, TrackSegment, point_polyline_distance
from engine.track_exact.imm import JunctionIMM
from engine.track_exact.mht import MultiHypothesisTracker, TrackHypothesis
from engine.track_exact.fusion import TrackExactEngine, TrackStateEstimate

__all__ = [
    "EdgeEKF",
    "TrackSegment",
    "point_polyline_distance",
    "RailHMMMapMatcher",
    "JunctionIMM",
    "TrackHypothesis",
    "MultiHypothesisTracker",
    "TrackExactEngine",
    "TrackStateEstimate",
]
