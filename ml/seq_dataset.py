"""RailTwin-X Sequence Dataset for PyTorch GRU Challenger (Phase G2).

Builds sequential train histories across the last 8 station events for each snapshot.
Ensures identical time-based temporal splitting as the LightGBM champion.
"""

from __future__ import annotations

import datetime
from typing import List, Optional, Tuple
import numpy as np
import pandas as pd
import torch
from torch.utils.data import Dataset, DataLoader

from config import settings
from data.db import Database, get_db


class RailwaySequenceDataset(Dataset):
    """PyTorch Dataset yielding (sequence_tensor, target_delay) tuples."""

    def __init__(self, sequences: np.ndarray, targets: np.ndarray):
        self.X = torch.tensor(sequences, dtype=torch.float32)
        self.y = torch.tensor(targets, dtype=torch.float32)

    def __len__(self) -> int:
        return len(self.X)

    def __getitem__(self, idx: int) -> Tuple[torch.Tensor, torch.Tensor]:
        return self.X[idx], self.y[idx]


class SequenceDatasetBuilder:
    """Builds sequence datasets (batch_size, seq_len=8, feat_dim=8) from SQLite."""

    def __init__(self, db: Optional[Database] = None, seq_len: int = 8):
        self.db = db or get_db()
        self.seq_len = seq_len

    def build_dataset(
        self,
        start_date: str,
        end_date: str,
    ) -> Tuple[np.ndarray, np.ndarray]:
        """Constructs 3D sequence arrays [N, seq_len, 8] and target arrays [N]."""
        with self.db.transaction() as cur:
            # Query ordered station events joined with train priority and station meta
            cur.execute(
                """
                SELECT se.train_no, se.run_date, se.seq, se.station_code,
                       COALESCE(se.delay_arr_min, 0.0) as delay_arr,
                       COALESCE(se.delay_dep_min, 0.0) as delay_dep,
                       rs.distance_km, rs.halt_min, s.is_junction, t.priority,
                       SUBSTR(rs.sched_arr, 1, 2) as sched_hour
                FROM station_events se
                JOIN route_stations rs ON (se.train_no = rs.train_no AND se.seq = rs.seq)
                JOIN stations s ON se.station_code = s.code
                JOIN trains t ON se.train_no = t.train_no
                WHERE se.run_date >= ? AND se.run_date <= ?
                ORDER BY se.train_no, se.run_date, se.seq
                """,
                (start_date, end_date),
            )
            rows = cur.fetchall()

        # Group by (train_no, run_date)
        trajectories: dict = {}
        for r in rows:
            key = (r["train_no"], r["run_date"])
            if key not in trajectories:
                trajectories[key] = []

            step_feat = [
                float(r["delay_arr"]),
                float(r["delay_dep"]),
                float(r["halt_min"] or 2.0),
                float(r["distance_km"]),
                float(r["is_junction"]),
                float(r["priority"]),
                float(int(r["sched_hour"]) if r["sched_hour"] and r["sched_hour"].isdigit() else 8),
                float(r["delay_arr"] - r["delay_dep"]),  # Dwell delta
            ]
            trajectories[key].append({
                "seq": int(r["seq"]),
                "feat": step_feat,
                "delay_arr": float(r["delay_arr"]),
            })

        sequences = []
        targets = []

        feat_dim = 8
        zero_pad = [0.0] * feat_dim

        for key, steps in trajectories.items():
            if len(steps) < 2:
                continue

            for target_idx in range(1, len(steps)):
                # History steps strictly preceding target_idx
                history_steps = steps[:target_idx]
                target_val = steps[target_idx]["delay_arr"]

                # Extract last seq_len features (pad with zero vectors if history < seq_len)
                feats = [s["feat"] for s in history_steps]
                if len(feats) < self.seq_len:
                    padding = [zero_pad] * (self.seq_len - len(feats))
                    seq_matrix = padding + feats
                else:
                    seq_matrix = feats[-self.seq_len :]

                sequences.append(seq_matrix)
                targets.append(target_val)

        if not sequences:
            # Empty fallback
            return np.zeros((0, self.seq_len, feat_dim)), np.zeros((0,))

        return np.array(sequences, dtype=np.float32), np.array(targets, dtype=np.float32)
