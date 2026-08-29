"""Multi-Hypothesis Tracking (MHT) for track-exact state estimation.

Maintains K competing Bayesian track hypotheses that update under spatial and
IMM mode likelihoods, collapsing instantaneously to P(track) = 1.0 upon receiving
hard ground truth events (Kavach RFID balises, MSDAC axle counters, Electronic Interlocking).
"""

from __future__ import annotations

from dataclasses import dataclass, field
import math
from typing import Dict, List, Optional, Sequence, Tuple
import numpy as np

from engine.track_exact.hmm_mapmatch import RailHMMMapMatcher, TrackSegment, point_polyline_distance


@dataclass
class TrackHypothesis:
    """A candidate track occupancy hypothesis with associated probability weight."""

    track_id: str
    weight: float
    confirmed_by: List[str] = field(default_factory=list)
    last_updated_ts: float = 0.0

    def to_dict(self) -> dict:
        return {
            "track_id": self.track_id,
            "weight": round(float(self.weight), 4),
            "confirmed_by": list(self.confirmed_by),
        }


class MultiHypothesisTracker:
    """Bayesian tracker maintaining competing track candidates with ground-truth collapse."""

    def __init__(
        self,
        matcher: RailHMMMapMatcher,
        sigma: float = 3.0,
        prune_w: float = 1e-3,
    ):
        self.matcher = matcher
        self.sigma = max(0.1, float(sigma))
        self.prune_w = float(prune_w)
        self.hyps: List[TrackHypothesis] = []
        self._init_all_hypotheses()

    def _init_all_hypotheses(self) -> None:
        """Initializes hypotheses uniformly across all available track segments."""
        if not self.matcher.segs:
            self.hyps = []
            return
        n = len(self.matcher.segs)
        w = 1.0 / n
        self.hyps = [
            TrackHypothesis(track_id=s_id, weight=w)
            for s_id in self.matcher.segs.keys()
        ]

    def set_candidates(self, track_ids: Sequence[str]) -> None:
        """Explicitly seeds candidate hypotheses."""
        valid_ids = [tid for tid in track_ids if tid in self.matcher.segs]
        if not valid_ids:
            return
        w = 1.0 / len(valid_ids)
        self.hyps = [
            TrackHypothesis(track_id=tid, weight=w)
            for tid in valid_ids
        ]

    def update(
        self,
        z_xy: Tuple[float, float] | Sequence[float],
        imm_mode_probs: Optional[Dict[str, float]] = None,
        segment_mode_affinity: Optional[Dict[str, str]] = None,
    ) -> None:
        """Updates hypothesis weights with spatial likelihood and optional IMM mode likelihood."""
        if not self.hyps:
            self._init_all_hypotheses()
            if not self.hyps:
                return

        # Default mapping of segment types to IMM kinematic modes
        mode_affinity = segment_mode_affinity or {
            "main": "MAIN_STRAIGHT",
            "up_main": "MAIN_STRAIGHT",
            "dn_main": "MAIN_STRAIGHT",
            "loop": "DIVERGE_LOOP",
            "loop_1": "DIVERGE_LOOP",
            "loop_2": "DIVERGE_LOOP",
            "platform": "BRAKE_PLATFORM",
            "platform_1": "BRAKE_PLATFORM",
            "platform_2": "BRAKE_PLATFORM",
        }

        for h in self.hyps:
            seg = self.matcher.segs.get(h.track_id)
            if not seg:
                h.weight = 0.0
                continue

            dist = point_polyline_distance(z_xy, seg.polyline)
            # Spatial likelihood
            w_spatial = math.exp(-0.5 * (dist / self.sigma) ** 2)

            # IMM Mode likelihood
            w_mode = 1.0
            if imm_mode_probs:
                track_type = seg.track_type.lower()
                target_mode = mode_affinity.get(track_type, mode_affinity.get(seg.id, None))
                if target_mode and target_mode in imm_mode_probs:
                    # Blend mode probability (with floor to prevent total zeroing)
                    p_mode = imm_mode_probs[target_mode]
                    w_mode = 0.2 + 0.8 * p_mode

            h.weight *= (w_spatial * w_mode)

        # Normalize
        total_w = sum(h.weight for h in self.hyps)
        if total_w > 0:
            for h in self.hyps:
                h.weight /= total_w
        else:
            # Fallback if all weights zeroed: uniform over nearest segments
            self._reinit_nearest(z_xy)
            return

        # Prune low probability hypotheses
        self.hyps = [h for h in self.hyps if h.weight >= self.prune_w]
        
        # Renormalize after pruning
        total_w = sum(h.weight for h in self.hyps)
        if total_w > 0:
            for h in self.hyps:
                h.weight /= total_w
        else:
            self._reinit_nearest(z_xy)

    def _reinit_nearest(self, z_xy: Tuple[float, float] | Sequence[float]) -> None:
        """Re-seeds tracker with the closest segment if tracking was lost."""
        if not self.matcher.segs:
            return
        best_id = min(
            self.matcher.segs.keys(),
            key=lambda sid: point_polyline_distance(z_xy, self.matcher.segs[sid].polyline),
        )
        self.hyps = [TrackHypothesis(track_id=best_id, weight=1.0)]

    def collapse(self, gt_track_id: str, source: str = "GROUND_TRUTH") -> None:
        """Instantly collapses all competing hypotheses to 100% certainty upon ground truth arrival."""
        if not gt_track_id:
            return

        existing = [h for h in self.hyps if h.track_id == gt_track_id]
        if existing:
            for h in existing:
                h.weight = 1.0
                if source not in h.confirmed_by:
                    h.confirmed_by.append(source)
            self.hyps = existing
        else:
            self.hyps = [
                TrackHypothesis(
                    track_id=gt_track_id,
                    weight=1.0,
                    confirmed_by=[source],
                )
            ]

    def estimate(self) -> Tuple[Optional[str], float]:
        """Returns the most likely track ID and its posterior probability P(track)."""
        if not self.hyps:
            return None, 0.0
        best = max(self.hyps, key=lambda h: h.weight)
        return best.track_id, float(best.weight)

    def get_distribution(self) -> Dict[str, float]:
        """Returns dictionary of all active hypotheses and their weights."""
        return {h.track_id: float(h.weight) for h in self.hyps}
