"""Global map-matching: states = track segments in TrackGraph.

Enforces Newson-Krumm Hidden Markov Model over physical railway track topology.
Topology is a HARD constraint: trains cannot teleport across parallel tracks (4.72 m spacing).
"""

from __future__ import annotations

from dataclasses import dataclass, field
import math
from typing import Dict, List, Optional, Sequence, Tuple


def point_polyline_distance(
    p: Tuple[float, float] | Sequence[float],
    polyline: Sequence[Tuple[float, float]] | Sequence[Sequence[float]],
) -> float:
    """Computes minimum Euclidean distance from 2D point p to polyline vertices & segments."""
    if not polyline:
        return float("inf")
    if len(polyline) == 1:
        x, y = p[0], p[1]
        x1, y1 = polyline[0][0], polyline[0][1]
        return math.hypot(x - x1, y - y1)

    x, y = p[0], p[1]
    best_dist = float("inf")

    for i in range(len(polyline) - 1):
        x1, y1 = polyline[i][0], polyline[i][1]
        x2, y2 = polyline[i + 1][0], polyline[i + 1][1]

        dx = x2 - x1
        dy = y2 - y1
        l2 = dx * dx + dy * dy

        if l2 == 0.0:
            proj_x, proj_y = x1, y1
        else:
            t = max(0.0, min(1.0, ((x - x1) * dx + (y - y1) * dy) / l2))
            proj_x = x1 + t * dx
            proj_y = y1 + t * dy

        dist = math.hypot(x - proj_x, y - proj_y)
        if dist < best_dist:
            best_dist = dist

    return best_dist


@dataclass
class TrackSegment:
    """Physical track segment polyline within a station yard or block section."""

    id: str
    polyline: List[Tuple[float, float]]
    name: str = ""
    track_type: str = "main"  # main, loop, platform, turnout
    speed_limit_kmph: float = 130.0
    length_m: float = 0.0

    def __post_init__(self):
        if not self.length_m and len(self.polyline) > 1:
            total = 0.0
            for i in range(len(self.polyline) - 1):
                p1, p2 = self.polyline[i], self.polyline[i + 1]
                total += math.hypot(p2[0] - p1[0], p2[1] - p1[1])
            self.length_m = total

    def distance_to(self, other: TrackSegment) -> float:
        """Computes connecting distance from this segment end to other segment start."""
        if not self.polyline or not other.polyline:
            return 0.0
        end_p = self.polyline[-1]
        start_p = other.polyline[0]
        return math.hypot(start_p[0] - end_p[0], start_p[1] - end_p[1])


class RailHMMMapMatcher:
    """HMM Map-Matcher with hard railway topological graph constraints."""

    def __init__(
        self,
        segments: Sequence[TrackSegment] | Dict[str, TrackSegment],
        adjacency: Optional[Dict[str, Sequence[str]]] = None,
        sigma_gps: float = 3.0,
        sigma_odo: float = 2.0,
    ):
        if isinstance(segments, dict):
            self.segs = segments
        else:
            self.segs = {s.id: s for s in segments}

        self.adj = adjacency or {}
        self.sg = max(0.1, float(sigma_gps))
        self.so = max(0.1, float(sigma_odo))
        self._log_norm_gps = math.log(math.sqrt(2.0 * math.pi) * self.sg)
        self._log_norm_odo = math.log(math.sqrt(2.0 * math.pi) * self.so)

    def _emission(self, z: Tuple[float, float], seg: TrackSegment) -> float:
        """Gaussian log-likelihood of observation z given segment polyline."""
        d = point_polyline_distance(z, seg.polyline)
        return -0.5 * (d / self.sg) ** 2 - self._log_norm_gps

    def _transition(self, si: str, sj: str, d_odo: float) -> float:
        """Log-transition probability between track segments enforcing topological graph."""
        if si != sj and sj not in self.adj.get(si, ()):
            return -float("inf")  # HARD topology constraint: forbidden track jump

        if si == sj:
            arc = 0.0
        else:
            arc = self.segs[si].distance_to(self.segs[sj])

        delta = abs(d_odo - arc)
        return -0.5 * (delta / self.so) ** 2 - self._log_norm_odo

    def match(
        self, observations: Sequence[Tuple[Tuple[float, float], float]]
    ) -> List[str]:
        """Viterbi decoding over sequence of observations [(z_xy, d_odo_since_prev), ...].

        Returns:
            Most likely sequence of track segment IDs.
        """
        if not observations or not self.segs:
            return []

        states = list(self.segs.keys())
        first_z, _ = observations[0]

        # Initialize Viterbi trellis with emission probabilities
        v_curr: Dict[str, float] = {
            s: self._emission(first_z, self.segs[s]) for s in states
        }
        backpointers: List[Dict[str, Optional[str]]] = [{s: None for s in states}]

        for t in range(1, len(observations)):
            z, d_odo = observations[t]
            v_next: Dict[str, float] = {}
            bp_next: Dict[str, Optional[str]] = {}

            for sj in states:
                best_score = -float("inf")
                best_prev = None

                for si in states:
                    prev_score = v_curr[si]
                    if prev_score == -float("inf"):
                        continue
                    trans_score = self._transition(si, sj, d_odo)
                    if trans_score == -float("inf"):
                        continue

                    total_score = prev_score + trans_score
                    if total_score > best_score:
                        best_score = total_score
                        best_prev = si

                # If no valid transitions reached sj (e.g. topological trap), fallback to emission only
                if best_score == -float("inf"):
                    v_next[sj] = self._emission(z, self.segs[sj]) - 100.0
                    bp_next[sj] = max(v_curr, key=v_curr.get) if v_curr else None
                else:
                    v_next[sj] = best_score + self._emission(z, self.segs[sj])
                    bp_next[sj] = best_prev

            v_curr = v_next
            backpointers.append(bp_next)

        # Backtrack best path
        best_end_state = max(v_curr, key=v_curr.get)
        path = [best_end_state]

        for t in range(len(backpointers) - 1, 0, -1):
            prev_state = backpointers[t].get(path[-1])
            if prev_state is None:
                prev_state = path[-1]
            path.append(prev_state)

        return path[::-1]

    def get_spatial_likelihoods(
        self, z: Tuple[float, float] | Sequence[float]
    ) -> Dict[str, float]:
        """Calculates normalized spatial probabilities P(track | z) for all segments."""
        if not self.segs:
            return {}

        log_likes: Dict[str, float] = {}
        for s_id, seg in self.segs.items():
            d = point_polyline_distance(z, seg.polyline)
            log_likes[s_id] = -0.5 * (d / self.sg) ** 2

        # Softmax normalization for numerical stability
        max_log = max(log_likes.values())
        exp_weights = {s: math.exp(ll - max_log) for s, ll in log_likes.items()}
        total = sum(exp_weights.values()) or 1.0
        return {s: w / total for s, w in exp_weights.items()}
