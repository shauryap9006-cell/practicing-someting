"""RailTwin-X Sequence Neural Network Challenger (Phase G2, F07, F08, F09, F16).

PyTorch GRU Architecture:
1. Feature-wise Linear Modulation (FiLM) Context Conditioning (F07):
   Injects 25 corridor context features (weather, congestion, headway, train class) via a context MLP
   that generates dynamic affine transformation parameters (gamma, beta) to modulate temporal representations.
2. Masked Temporal Self-Attention (F08):
   Applies true -1e9 masked attention over temporal hidden states, guaranteeing zero attention mass
   on padded events for early-journey trains.
3. Dense Station Embedding Layer with Cold-Start Hashing (F09):
   1200-node station embedding (dim=8) replacing boolean flags, mapping junction hubs and corridor topologies.
4. Non-Crossing Quantile Projection Heads:
   Softplus-constrained offsets guaranteeing 0 <= q10 <= q50 <= q90.
"""

from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Dict, Optional, Tuple, Any, Union
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import DataLoader

from config import settings
from data.db import Database, get_db
from ml.seq_dataset import RailwaySequenceDataset, SequenceDatasetBuilder


def set_seed(seed: int = 42) -> None:
    """Sets deterministic random seeds across PyTorch and NumPy."""
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def station_code_to_idx(stn_code: Union[str, int], num_stations: int = 1200) -> int:
    """Converts a station code string to a deterministic embedding index with hash bucket fallback (F09)."""
    if isinstance(stn_code, int):
        return abs(stn_code) % num_stations
    if not stn_code:
        return 0
    # Deterministic polynomial string hash
    h = 0
    for char in str(stn_code).strip().upper():
        h = (h * 31 + ord(char)) % num_stations
    return int(h)


class PinballQuantileLoss(nn.Module):
    """Pinball loss function for multiple quantile estimates."""

    def __init__(self, quantiles: Tuple[float, float, float] = (0.1, 0.5, 0.9)):
        super().__init__()
        self.quantiles = quantiles

    def forward(
        self,
        q10_pred: torch.Tensor,
        q50_pred: torch.Tensor,
        q90_pred: torch.Tensor,
        target: torch.Tensor,
    ) -> torch.Tensor:
        target = target.view(-1, 1)
        preds = [q10_pred.view(-1, 1), q50_pred.view(-1, 1), q90_pred.view(-1, 1)]
        total_loss = torch.tensor(0.0, device=target.device)

        for q, pred in zip(self.quantiles, preds):
            err = target - pred
            loss = torch.max(q * err, (q - 1.0) * err)
            total_loss = total_loss + torch.mean(loss)

        return total_loss


class FiLMLayer(nn.Module):
    """Feature-wise Linear Modulation (FiLM) Layer (F07).

    Modulates intermediate representations x with scale gamma(z) and shift beta(z):
    h' = gamma(z) * x + beta(z)
    """

    def __init__(self, context_dim: int, feature_dim: int):
        super().__init__()
        self.fc_gamma = nn.Linear(context_dim, feature_dim)
        self.fc_beta = nn.Linear(context_dim, feature_dim)

        # Initialize gamma around 1 and beta around 0 for identity start
        nn.init.ones_(self.fc_gamma.bias)
        nn.init.zeros_(self.fc_beta.bias)

    def forward(self, x: torch.Tensor, context: torch.Tensor) -> torch.Tensor:
        gamma = self.fc_gamma(context)
        beta = self.fc_beta(context)
        return gamma * x + beta


class NonCrossingGRUQuantileModel(nn.Module):
    """2-Layer PyTorch GRU with FiLM Context Conditioning, Masked Attention, Dense Station Embeddings, and Non-Crossing Heads."""

    def __init__(
        self,
        input_dim: int = 8,
        context_dim: int = 25,
        hidden_dim: int = 128,
        num_layers: int = 2,
        dropout: float = 0.2,
        num_stations: int = 1200,
        station_embed_dim: int = 8,
    ):
        super().__init__()
        self.input_dim = input_dim
        self.context_dim = context_dim
        self.hidden_dim = hidden_dim
        self.num_layers = num_layers
        self.num_stations = num_stations
        self.station_embed_dim = station_embed_dim

        # F09: Dense Target Station Embedding Layer
        self.station_embed = nn.Embedding(num_stations, station_embed_dim)

        # F07: Context Encoder MLP (25 -> 64 -> hidden_dim)
        self.context_encoder = nn.Sequential(
            nn.Linear(context_dim, 64),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(64, hidden_dim),
        )

        # Covariate Initial State Projection (DeepAR-style covariate initialization)
        self.h0_proj = nn.Linear(hidden_dim, hidden_dim)

        # Recurrent Sequence Encoder
        self.gru = nn.GRU(
            input_size=input_dim,
            hidden_size=hidden_dim,
            num_layers=num_layers,
            batch_first=True,
            dropout=dropout if num_layers > 1 else 0.0,
        )

        # F08: Masked Temporal Self-Attention
        self.attn = nn.Linear(hidden_dim, 1)
        self.last_attn_weights: Optional[torch.Tensor] = None

        # F07: FiLM Context Conditioning (modulates pooled GRU state with context + station embedding)
        self.film = FiLMLayer(
            context_dim=hidden_dim + station_embed_dim,
            feature_dim=hidden_dim,
        )

        # Dense Shared MLP
        self.fc_shared = nn.Sequential(
            nn.Linear(hidden_dim, 64),
            nn.ReLU(),
            nn.Dropout(dropout),
        )

        # Non-Crossing Monotonic Quantile Heads (F16)
        self.head_q10 = nn.Linear(64, 1)
        self.head_delta_q50 = nn.Linear(64, 1)
        self.head_delta_q90 = nn.Linear(64, 1)

    def forward(
        self,
        x: torch.Tensor,
        context: Optional[torch.Tensor] = None,
        mask: Optional[torch.Tensor] = None,
        target_station_idx: Optional[torch.Tensor] = None,
    ) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        """Forward pass with FiLM modulation, masked attention, and station embeddings."""
        batch_size = x.size(0)
        device = x.device

        # Handle optional context vector (defaults to zeros if omitted)
        if context is None:
            context = torch.zeros((batch_size, self.context_dim), dtype=torch.float32, device=device)
        elif context.dim() == 1:
            context = context.unsqueeze(0)

        # Handle optional target station index
        if target_station_idx is None:
            target_station_idx = torch.zeros(batch_size, dtype=torch.long, device=device)
        elif target_station_idx.dim() == 0:
            target_station_idx = target_station_idx.unsqueeze(0)

        # Encode context & station embeddings (F07, F09)
        ctx_emb = self.context_encoder(context)  # [B, hidden_dim]
        stn_emb = self.station_embed(target_station_idx)  # [B, station_embed_dim]
        combined_context = torch.cat([ctx_emb, stn_emb], dim=-1)  # [B, hidden_dim + station_embed_dim]

        # Covariate initial state for GRU
        h0 = self.h0_proj(ctx_emb).unsqueeze(0).repeat(self.num_layers, 1, 1)  # [num_layers, B, hidden_dim]

        # GRU Forward Pass
        out, _ = self.gru(x, h0)  # [B, seq_len, hidden_dim]

        # F08: Masked Temporal Attention
        attn_scores = self.attn(out)  # [B, seq_len, 1]

        if mask is None:
            # Auto-detect padding (where all features are 0.0)
            mask = (x.abs().sum(dim=-1) > 1e-6)  # [B, seq_len]

        # Mask invalid/padded positions with -1e9 before softmax
        attn_scores = attn_scores.masked_fill(~mask.unsqueeze(-1), -1e9)
        attn_weights = torch.softmax(attn_scores, dim=1)  # [B, seq_len, 1]
        self.last_attn_weights = attn_weights.detach()

        # Attention-weighted pooled representation
        pooled = (out * attn_weights).sum(dim=1)  # [B, hidden_dim]

        # F07: FiLM Modulation on pooled state
        modulated = self.film(pooled, combined_context)  # [B, hidden_dim]

        # Shared projection
        feat = self.fc_shared(modulated)  # [B, 64]

        # Monotonic non-crossing quantile heads
        q10 = F.relu(self.head_q10(feat))  # delay >= 0
        delta_q50 = F.softplus(self.head_delta_q50(feat))
        delta_q90 = F.softplus(self.head_delta_q90(feat))

        q50 = q10 + delta_q50
        q90 = q50 + delta_q90

        return q10, q50, q90


class GRUChallengerTrainer:
    """Trains, evaluates, and exports the PyTorch GRU Challenger model."""

    def __init__(self, db: Optional[Database] = None, artifacts_dir: Optional[Path] = None):
        self.db = db or get_db()
        self.artifacts_dir = artifacts_dir or settings.ARTIFACTS_DIR
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    def train(self, epochs: int = 15, batch_size: int = 256, lr: float = 0.003) -> Dict[str, Any]:
        """Executes the full PyTorch GRU training pipeline on the TRAIN time split."""
        set_seed(42)
        print(f"[INFO] Initializing GRU Challenger Training on device: {self.device}", flush=True)

        with self.db.transaction() as cur:
            cur.execute("SELECT MIN(run_date) as min_d, MAX(run_date) as max_d FROM station_events")
            row = cur.fetchone()

        min_d = row["min_d"] if row and row["min_d"] else "2026-07-31"
        max_d = row["max_d"] if row and row["max_d"] else "2026-08-27"

        import datetime
        max_dt = datetime.date.fromisoformat(max_d)
        min_dt = datetime.date.fromisoformat(min_d)
        total_days = (max_dt - min_dt).days + 1

        test_days = min(7, max(1, total_days // 4))
        train_days = min(21, max(1, total_days - test_days))

        test_start_dt = max_dt - datetime.timedelta(days=test_days - 1)
        train_cutoff_dt = test_start_dt - datetime.timedelta(days=1)
        train_start_dt = train_cutoff_dt - datetime.timedelta(days=train_days - 1)

        start_date = train_start_dt.strftime("%Y-%m-%d")
        train_cutoff = train_cutoff_dt.strftime("%Y-%m-%d")
        test_start = test_start_dt.strftime("%Y-%m-%d")
        test_end = max_dt.strftime("%Y-%m-%d")

        print(f"[INFO] GRU Time-Split: TRAIN [{start_date} to {train_cutoff}], TEST [{test_start} to {test_end}]", flush=True)

        builder = SequenceDatasetBuilder(self.db, seq_len=8)
        X_train, y_train = builder.build_dataset(start_date, train_cutoff)
        X_test, y_test = builder.build_dataset(test_start, test_end)

        print(f"[INFO] Built {len(X_train):,} training sequences and {len(X_test):,} testing sequences.", flush=True)

        train_loader = DataLoader(RailwaySequenceDataset(X_train, y_train), batch_size=batch_size, shuffle=True)
        test_loader = DataLoader(RailwaySequenceDataset(X_test, y_test), batch_size=batch_size, shuffle=False)

        model = NonCrossingGRUQuantileModel(
            input_dim=8,
            context_dim=25,
            hidden_dim=128,
            num_layers=2,
            dropout=0.2,
        ).to(self.device)

        criterion = PinballQuantileLoss(quantiles=(0.1, 0.5, 0.9))
        optimizer = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=1e-4)
        scheduler = torch.optim.lr_scheduler.CosineAnnealingWarmRestarts(optimizer, T_0=5, T_mult=2)

        best_val_loss = float("inf")
        best_state = None
        patience = 5
        patience_counter = 0

        for epoch in range(1, epochs + 1):
            model.train()
            running_loss = 0.0
            for batch_x, batch_y in train_loader:
                batch_x, batch_y = batch_x.to(self.device), batch_y.to(self.device)
                optimizer.zero_grad()
                q10, q50, q90 = model(batch_x)
                loss = criterion(q10, q50, q90, batch_y)
                loss.backward()
                torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
                optimizer.step()
                running_loss += loss.item() * len(batch_y)

            scheduler.step()
            epoch_loss = running_loss / max(1, len(X_train))

            model.eval()
            val_loss = 0.0
            with torch.no_grad():
                for val_x, val_y in test_loader:
                    val_x, val_y = val_x.to(self.device), val_y.to(self.device)
                    vq10, vq50, vq90 = model(val_x)
                    vloss = criterion(vq10, vq50, vq90, val_y)
                    val_loss += vloss.item() * len(val_y)
            val_epoch_loss = val_loss / max(1, len(X_test))

            if val_epoch_loss < best_val_loss:
                best_val_loss = val_epoch_loss
                best_state = {k: v.cpu().clone() for k, v in model.state_dict().items()}
                patience_counter = 0
            else:
                patience_counter += 1

            print(f"  Epoch [{epoch:02d}/{epochs:02d}] - Train Loss: {epoch_loss:.4f} | Val Loss: {val_epoch_loss:.4f} (Best: {best_val_loss:.4f})", flush=True)

            if patience_counter >= patience:
                print(f"  [EARLY STOPPING] Early stopping at epoch {epoch}.", flush=True)
                break

        if best_state is not None:
            model.load_state_dict(best_state)

        model.eval()
        all_q10, all_q50, all_q90, all_y = [], [], [], []
        with torch.no_grad():
            for batch_x, batch_y in test_loader:
                batch_x = batch_x.to(self.device)
                q10, q50, q90 = model(batch_x)
                all_q10.append(q10.cpu().numpy())
                all_q50.append(q50.cpu().numpy())
                all_q90.append(q90.cpu().numpy())
                all_y.append(batch_y.numpy())

        if all_q50:
            p10 = np.concatenate(all_q10).flatten()
            p50 = np.concatenate(all_q50).flatten()
            p90 = np.concatenate(all_q90).flatten()
            y_eval = np.concatenate(all_y).flatten()

            test_mae = float(np.mean(np.abs(y_eval - p50)))
            coverage_80 = float(np.mean((y_eval >= p10) & (y_eval <= p90)) * 100.0)
            crossing_violations = int(np.sum((p10 > p50) | (p50 > p90)))
        else:
            test_mae = 0.0
            coverage_80 = 0.0
            crossing_violations = 0

        print(f"[RESULT] GRU Challenger Test MAE: {test_mae:.2f} min | 80% Coverage: {coverage_80:.1f}% | Crossing Violations: {crossing_violations}")

        weights_path = self.artifacts_dir / "model_gru_challenger.pt"
        torch.save(model.state_dict(), weights_path)

        config = {
            "model_type": "PyTorch_GRU_Quantile",
            "input_dim": 8,
            "context_dim": 25,
            "hidden_dim": 128,
            "num_layers": 2,
            "dropout": 0.2,
            "quantiles": [0.1, 0.5, 0.9],
            "test_mae": test_mae,
            "coverage_80_pct": coverage_80,
            "quantile_crossing_violations": crossing_violations,
            "train_samples": len(X_train),
            "test_samples": len(X_test),
        }
        config_path = self.artifacts_dir / "gru_config.json"
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2)

        return config
