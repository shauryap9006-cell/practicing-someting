"""RailTwinGRUv2 ? Challenger Architecture for Champion-Gate Promotion.

NEVER served until gated.

Upgrades vs v1:
  1. StationVocab embedding (deterministic, zero collisions)      [T1]
  2. JourneyNorm: masked per-journey delay normalization (RevIN-style, Kim et al. ICLR 2022)
  3. FiLM with identity-init gamma
  4. Interaction Cortex: cross-attention over K=8 neighbor trains,
     attention weights exposed for per-train causal attribution
  5. Median-anchored 7-level monotone quantile head (0.05..0.95)
  6. CRPS-approx + Winkler training objective
"""
from __future__ import annotations

from typing import Dict, List, Optional, Tuple, Union
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch import Tensor

ALPHAS_V2: Tuple[float, ...] = (0.05, 0.10, 0.25, 0.50, 0.75, 0.90, 0.95)
IDX_Q10, IDX_Q50, IDX_Q90 = 1, 3, 5  # legacy interlock mapping indices


class MonotoneQuantileHead(nn.Module):
    """Median-anchored non-crossing head. Monotone BY CONSTRUCTION for any input.

    Increments are cumsum(softplus(.)) >= 0 above and below the median.
    Anchoring at the median (not q10 as v1) prevents low-tail error from
    contaminating every upper quantile.
    """

    def __init__(self, hidden_dim: int, alphas: Tuple[float, ...] = ALPHAS_V2):
        super().__init__()
        self.alphas = tuple(sorted(alphas))
        K = len(self.alphas)
        self.m = min(range(K), key=lambda i: abs(self.alphas[i] - 0.5))
        self.n_up = K - 1 - self.m
        self.n_dn = self.m
        self.center = nn.Linear(hidden_dim, 1)
        self.up = nn.Linear(hidden_dim, max(self.n_up, 1))
        self.dn = nn.Linear(hidden_dim, max(self.n_dn, 1))

    def forward(self, h: Tensor) -> Tensor:  # h [B, H]
        c = self.center(h)  # [B, 1]
        parts = [c]
        if self.n_up > 0:
            up_inc = torch.cumsum(F.softplus(self.up(h))[:, : self.n_up], dim=-1)
            parts.append(c + up_inc)
        if self.n_dn > 0:
            dn_inc = torch.flip(
                torch.cumsum(F.softplus(self.dn(h))[:, : self.n_dn], dim=-1),
                dims=[-1],
            )
            parts.insert(0, c - dn_inc)
        return torch.cat(parts, dim=-1)  # [B, K] ascending


class PinballCRPSLoss(nn.Module):
    """CRPS ~ 2 * mean_alpha pinball (Gneiting & Raftery 2007 identity), + small Winkler term."""

    def __init__(
        self,
        alphas: Tuple[float, ...] = ALPHAS_V2,
        w_pair: Tuple[float, float] = (0.05, 0.95),
        w_weight: float = 0.1,
    ):
        super().__init__()
        self.register_buffer("alphas", torch.tensor(alphas, dtype=torch.float32))
        self.i_lo = alphas.index(w_pair[0])
        self.i_hi = alphas.index(w_pair[1])
        self.alpha_w = w_pair[0] + (1.0 - w_pair[1])
        self.w = w_weight

    def forward(self, preds: Tensor, target: Tensor) -> Tuple[Tensor, Dict[str, float]]:
        err = target.unsqueeze(-1) - preds  # [B, K]
        a = self.alphas.view(1, -1)
        pin = torch.maximum(a * err, (a - 1.0) * err)
        crps = 2.0 * pin.mean()

        lo = preds[:, self.i_lo]
        hi = preds[:, self.i_hi]
        y = target

        under = torch.where(y < lo, (2.0 / self.alpha_w) * (lo - y), torch.zeros_like(y))
        over = torch.where(y > hi, (2.0 / self.alpha_w) * (y - hi), torch.zeros_like(y))
        winkler_term = (hi - lo + under + over).mean()

        total_loss = crps + self.w * winkler_term
        return total_loss, {"crps": crps.item(), "winkler": winkler_term.item()}


class JourneyNorm(nn.Module):
    """Masked per-journey normalization of delay channels (RevIN-style, Kim et al. ICLR 2022).

    Stats use OBSERVED steps only => no future leak.
    Removes journey-level non-stationarity (chronic-late rakes, fog days).
    """

    @staticmethod
    def masked_stats(x: Tensor, mask: Tensor) -> Tuple[Tensor, Tensor]:  # x [B, T, C], mask [B, T]
        m = mask.unsqueeze(-1).float()
        cnt = m.sum(dim=1).clamp(min=1.0)
        mu = (x * m).sum(dim=1) / cnt  # [B, C]
        var = ((x - mu.unsqueeze(1)) ** 2 * m).sum(dim=1) / cnt
        sd = torch.sqrt(var + 1e-5).clamp(min=0.5)  # floor avoids collapse
        return mu, sd


class FiLM(nn.Module):
    """Feature-wise Linear Modulation. gamma uses (1+g) => identity at init."""

    def __init__(self, ctx_dim: int, feat_dim: int, hidden: int = 64):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(ctx_dim, hidden),
            nn.ReLU(),
            nn.Linear(hidden, 2 * feat_dim),
        )
        # Initialize final layer weights and biases for identity start
        nn.init.zeros_(self.net[-1].weight)
        nn.init.zeros_(self.net[-1].bias)

    def forward(self, x: Tensor, ctx: Tensor) -> Tensor:  # x [B, T, F], ctx [B, C]
        params = self.net(ctx)
        g, b = params.chunk(2, dim=-1)
        return (1.0 + g).unsqueeze(1) * x + b.unsqueeze(1)


class MaskedAttentionPool(nn.Module):
    """Temporal self-attention pool with -1e9 mask on padded positions."""

    def __init__(self, dim: int, hidden: int = 64):
        super().__init__()
        self.score = nn.Sequential(
            nn.Linear(dim, hidden),
            nn.Tanh(),
            nn.Linear(hidden, 1),
        )

    def forward(self, h: Tensor, mask: Tensor) -> Tensor:  # h [B, T, D], mask [B, T]
        s = self.score(h).squeeze(-1) - (~mask).float() * 1e9
        a = torch.softmax(s, dim=-1)
        return (a.unsqueeze(-1) * h).sum(dim=1)  # [B, D]


class NeighborInteraction(nn.Module):
    """Interaction Cortex.

    Cross-attention from own-journey summary to K neighbor-train tokens
    (permutation-invariant, variable-K via padding mask).
    Attention weights => per-train causal attribution for /eta provenance.
    """

    def __init__(self, nbr_feat_dim: int, dim: int = 128, heads: int = 4):
        super().__init__()
        self.proj = nn.Linear(nbr_feat_dim, dim)
        self.attn = nn.MultiheadAttention(dim, heads, batch_first=True)
        self.norm = nn.LayerNorm(dim)

    def forward(self, own: Tensor, nbr: Tensor, nbr_mask: Tensor) -> Tuple[Tensor, Tensor]:
        # own [B, D]; nbr [B, K, F_nbr]; nbr_mask [B, K] True=valid neighbor
        k = self.proj(nbr)
        # If all neighbors in a batch row are padded (~nbr_mask all True), handle gracefully
        all_pad = (~nbr_mask).all(dim=-1)
        safe_mask = ~nbr_mask
        if all_pad.any():
            safe_mask = safe_mask.clone()
            safe_mask[all_pad, 0] = False  # unmask 1 dummy slot to prevent NaN softmax

        ctx, w = self.attn(
            own.unsqueeze(1),
            k,
            k,
            key_padding_mask=safe_mask,
            need_weights=True,
            average_attn_weights=True,
        )
        ctx_sq = ctx.squeeze(1)
        if all_pad.any():
            ctx_sq = torch.where(all_pad.unsqueeze(-1), torch.zeros_like(ctx_sq), ctx_sq)
        return self.norm(own + ctx_sq), w.squeeze(1) if w is not None else torch.zeros((own.size(0), nbr.size(1)), device=own.device)


class SeqSchema:
    """Single source of truth for sequence feature channels and normalization schema (Bug 5)."""
    COLS = [
        "arr_delay",
        "dep_delay",
        "halt_min",
        "distance_km",
        "is_junction",
        "priority",
        "sched_hour",
        "dwell_delta",
    ]
    ARR_DELAY = 0
    DEP_DELAY = 1
    DELAY_CHANNELS = (0, 1)
    MAX_LEN = 32


class RailTwinGRUv2(nn.Module):
    """Unidirectional GRU with StationVocab embeddings, JourneyNorm, FiLM, Interaction Cortex, and monotone head."""

    def __init__(
        self,
        seq_feat_dim: int = 8,
        station_emb_dim: int = 8,
        ctx_dim: int = 34,
        nbr_feat_dim: int = 12,
        hidden_dim: int = 128,
        gru_layers: int = 2,
        dropout: float = 0.2,
        vocab_size: int = 2048,
        alphas: Tuple[float, ...] = ALPHAS_V2,
    ):
        super().__init__()
        self.alphas = alphas
        self.hidden_dim = hidden_dim
        self.seq_feat_dim = seq_feat_dim
        self.ctx_dim = ctx_dim
        self.nbr_feat_dim = nbr_feat_dim

        in_dim = seq_feat_dim + station_emb_dim
        self.station_emb = nn.Embedding(vocab_size, station_emb_dim, padding_idx=0)
        self.film = FiLM(ctx_dim, in_dim)
        self.gru = nn.GRU(
            in_dim,
            hidden_dim,
            num_layers=gru_layers,
            batch_first=True,
            dropout=dropout if gru_layers > 1 else 0.0,
        )
        self.pool = MaskedAttentionPool(hidden_dim)
        self.nbr = NeighborInteraction(nbr_feat_dim, hidden_dim)
        self.ctx_proj = nn.Linear(ctx_dim, hidden_dim)
        self.gate = nn.Linear(3 * hidden_dim, hidden_dim)
        self.head = MonotoneQuantileHead(hidden_dim, alphas)

    def forward(
        self,
        seq: Tensor,
        station_ids: Tensor,
        seq_mask: Tensor,
        ctx: Tensor,
        nbr: Optional[Tensor] = None,
        nbr_mask: Optional[Tensor] = None,
    ) -> Dict[str, Tensor]:
        # seq [B, T, F] raw; station_ids [B, T]; seq_mask [B, T] bool;
        # ctx [B, C]; nbr [B, K, F_nbr]; nbr_mask [B, K] bool
        assert seq.shape[-1] == len(SeqSchema.COLS), (
            f"Seq feature dim mismatch: expected {len(SeqSchema.COLS)}, got {seq.shape[-1]}"
        )
        batch_size = seq.size(0)
        device = seq.device

        if nbr is None:
            nbr = torch.zeros((batch_size, 8, self.nbr_feat_dim), dtype=torch.float32, device=device)
        if nbr_mask is None:
            nbr_mask = torch.zeros((batch_size, 8), dtype=torch.bool, device=device)

        ch_arr = SeqSchema.ARR_DELAY
        ch_delays = list(SeqSchema.DELAY_CHANNELS)
        mu, sd = JourneyNorm.masked_stats(seq[..., ch_delays], seq_mask)
        xn = seq.clone()
        xn[..., ch_delays] = torch.where(
            seq_mask.unsqueeze(-1),
            (seq[..., ch_delays] - mu.unsqueeze(1)) / sd.unsqueeze(1),
            torch.zeros_like(seq[..., ch_delays]),
        )

        stn_e = self.station_emb(station_ids)
        x = torch.cat([xn, stn_e], dim=-1)
        x = self.film(x, ctx)
        h, _ = self.gru(x)  # [B, T, H]
        h_own = self.pool(h, seq_mask)
        h_int, nbr_w = self.nbr(h_own, nbr, nbr_mask)
        g = torch.sigmoid(self.gate(torch.cat([h_own, h_int, self.ctx_proj(ctx)], dim=-1)))
        h_fused = g * h_int + (1.0 - g) * h_own
        q_norm = self.head(h_fused)  # [B, K] normalized
        # De-normalize explicitly using arrival delay stats (Bug 5)
        q = q_norm * sd[:, ch_arr:ch_arr+1] + mu[:, ch_arr:ch_arr+1]
        return {
            "quantiles": q,
            "nbr_attn": nbr_w,
            "fusion_gate": g.detach().mean(0),
        }

    @staticmethod
    def legacy_view(q: Tensor) -> Tuple[Tensor, Tensor, Tensor]:
        """Maps 7-quantile output to the interlock's (q10, q50, q90) contract."""
        return q[:, IDX_Q10], q[:, IDX_Q50], q[:, IDX_Q90]

