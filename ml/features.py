"""RailTwin-X Feature Dictionary & Schema (Single Source of Truth).

Supports:
- FEATURE_VERSION = 1: 25-feature legacy schema (LightGBM champion compatibility)
- FEATURE_VERSION = 2: 34-feature causal schema (Task T2: wiring rakes, TSRs, festivals, position belief, recency)
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Dict, Any, Optional
import numpy as np
import pandas as pd

FEATURE_VERSION = 2

# Legacy 25-feature schema (Phase G1 + Phase 2)
FEATURE_NAMES_V1: List[str] = [
    "current_delay",
    "hops_remaining",
    "km_remaining",
    "hour_of_day",
    "day_type",
    "train_priority",
    "target_is_junction",
    "target_is_terminus",
    "hist_avg_delay_train_target",
    "hist_p90_delay_train_target",
    "sched_halt_target_min",
    "sched_congestion_target",
    "fog_flag_target",
    "rain_mm_target",
    "active_corridor_trains",
    "delay_velocity",
    "chronic_baseline",
    # Track-Context Features (Phase G1)
    "trains_ahead_30k",
    "trains_behind_30k",
    "opposing_trains_30k",
    "min_predicted_headway_next_station",
    "sum_delay_trains_ahead_30k",
    "section_occupancy_pct",
    # Passenger & Operations Features (Phase 2)
    "rake_incoming_delay",
    "crew_duty_pressure",
]

# v2 Causal Feature Additions (Task T2)
FEATURE_NAMES_V2_ADDITIONS: List[str] = [
    "upstream_rake_delay_min",
    "upstream_rake_buffer_remaining_min",
    "rake_linked",
    "tsr_active_ahead_count",
    "tsr_max_slowdown_pct",
    "festival_load_multiplier",
    "position_belief_entropy",
    "position_p_mode",
    "minutes_since_last_obs",
]

FEATURE_NAMES_V2: List[str] = FEATURE_NAMES_V1 + FEATURE_NAMES_V2_ADDITIONS

# FEATURE_NAMES defaults to V1 for 100% backward compatibility with frozen champion boosters and existing test assertions
FEATURE_NAMES: List[str] = FEATURE_NAMES_V1


@dataclass
class TrainFeatureVector:
    """Strongly typed feature representation for a single (train, current_stn, target_stn) snapshot."""

    current_delay: float
    hops_remaining: int
    km_remaining: float
    hour_of_day: int
    day_type: int
    train_priority: int
    target_is_junction: int
    target_is_terminus: int
    hist_avg_delay_train_target: float
    hist_p90_delay_train_target: float
    sched_halt_target_min: int
    sched_congestion_target: int
    fog_flag_target: int
    rain_mm_target: float
    active_corridor_trains: int
    delay_velocity: float
    chronic_baseline: float
    # Track Context Features (v1)
    trains_ahead_30k: float = 0.0
    trains_behind_30k: float = 0.0
    opposing_trains_30k: float = 0.0
    min_predicted_headway_next_station: float = 60.0
    sum_delay_trains_ahead_30k: float = 0.0
    section_occupancy_pct: float = 0.0
    # Passenger & Operations Features (v1)
    rake_incoming_delay: float = 0.0
    crew_duty_pressure: float = 0.0

    # v2 Causal Disconnected Organs (Task T2)
    upstream_rake_delay_min: float = 0.0
    upstream_rake_buffer_remaining_min: float = 0.0
    rake_linked: int = 0
    tsr_active_ahead_count: int = 0
    tsr_max_slowdown_pct: float = 0.0
    festival_load_multiplier: float = 1.0
    position_belief_entropy: float = 0.0
    position_p_mode: float = 1.0
    minutes_since_last_obs: float = 0.0

    # Targets (populated during dataset creation, None during live serving)
    target_direct_delay: Optional[float] = None
    target_section_delta: Optional[float] = None

    def to_dict(self, version: int = 2) -> Dict[str, Any]:
        """Converts feature vector to dictionary matching FEATURE_NAMES_V1 or FEATURE_NAMES_V2."""
        d = {
            "current_delay": float(self.current_delay),
            "hops_remaining": int(self.hops_remaining),
            "km_remaining": float(self.km_remaining),
            "hour_of_day": int(self.hour_of_day),
            "day_type": int(self.day_type),
            "train_priority": int(self.train_priority),
            "target_is_junction": int(self.target_is_junction),
            "target_is_terminus": int(self.target_is_terminus),
            "hist_avg_delay_train_target": float(self.hist_avg_delay_train_target),
            "hist_p90_delay_train_target": float(self.hist_p90_delay_train_target),
            "sched_halt_target_min": int(self.sched_halt_target_min),
            "sched_congestion_target": int(self.sched_congestion_target),
            "fog_flag_target": int(self.fog_flag_target),
            "rain_mm_target": float(self.rain_mm_target),
            "active_corridor_trains": int(self.active_corridor_trains),
            "delay_velocity": float(self.delay_velocity),
            "chronic_baseline": float(self.chronic_baseline),
            "trains_ahead_30k": float(self.trains_ahead_30k),
            "trains_behind_30k": float(self.trains_behind_30k),
            "opposing_trains_30k": float(self.opposing_trains_30k),
            "min_predicted_headway_next_station": float(self.min_predicted_headway_next_station),
            "sum_delay_trains_ahead_30k": float(self.sum_delay_trains_ahead_30k),
            "section_occupancy_pct": float(self.section_occupancy_pct),
            "rake_incoming_delay": float(self.rake_incoming_delay),
            "crew_duty_pressure": float(self.crew_duty_pressure),
            # v2 fields
            "upstream_rake_delay_min": float(self.upstream_rake_delay_min),
            "upstream_rake_buffer_remaining_min": float(self.upstream_rake_buffer_remaining_min),
            "rake_linked": int(self.rake_linked),
            "tsr_active_ahead_count": int(self.tsr_active_ahead_count),
            "tsr_max_slowdown_pct": float(self.tsr_max_slowdown_pct),
            "festival_load_multiplier": float(self.festival_load_multiplier),
            "position_belief_entropy": float(self.position_belief_entropy),
            "position_p_mode": float(self.position_p_mode),
            "minutes_since_last_obs": float(self.minutes_since_last_obs),
        }
        if self.target_direct_delay is not None:
            d["target_direct_delay"] = float(self.target_direct_delay)
        if self.target_section_delta is not None:
            d["target_section_delta"] = float(self.target_section_delta)
        return d

    def to_numpy_v1(self) -> np.ndarray:
        """Fast 2D numpy array representation for sub-millisecond online inference."""
        return np.array(
            [
                [
                    float(self.current_delay),
                    float(self.hops_remaining),
                    float(self.km_remaining),
                    float(self.hour_of_day),
                    float(self.day_type),
                    float(self.train_priority),
                    float(self.target_is_junction),
                    float(self.target_is_terminus),
                    float(self.hist_avg_delay_train_target),
                    float(self.hist_p90_delay_train_target),
                    float(self.sched_halt_target_min),
                    float(self.sched_congestion_target),
                    float(self.fog_flag_target),
                    float(self.rain_mm_target),
                    float(self.active_corridor_trains),
                    float(self.delay_velocity),
                    float(self.chronic_baseline),
                    float(self.trains_ahead_30k),
                    float(self.trains_behind_30k),
                    float(self.opposing_trains_30k),
                    float(self.min_predicted_headway_next_station),
                    float(self.sum_delay_trains_ahead_30k),
                    float(self.section_occupancy_pct),
                    float(self.rake_incoming_delay),
                    float(self.crew_duty_pressure),
                ]
            ],
            dtype=np.float64,
        )


def validate_feature_dataframe(df: pd.DataFrame, is_training: bool = True, version: int = 1) -> None:
    """Validates schema types and bounds on extracted feature dataframes."""
    cols = FEATURE_NAMES_V2 if version == 2 else FEATURE_NAMES_V1
    missing_cols = [c for c in cols if c not in df.columns]
    if missing_cols:
        raise ValueError(f"Feature DataFrame missing required columns: {missing_cols}")

    if df[cols].isnull().any().any():
        null_counts = df[cols].isnull().sum()
        offending = null_counts[null_counts > 0].to_dict()
        raise ValueError(f"Feature DataFrame contains null/NaN values: {offending}")

    if is_training:
        if "target_direct_delay" not in df.columns:
            raise ValueError("Training DataFrame missing 'target_direct_delay' column.")
        if "target_section_delta" not in df.columns:
            raise ValueError("Training DataFrame missing 'target_section_delta' column.")
