"""RailTwinGRUv3 Neural Network Architecture with RegimeMoE Head (Phase D).

Features:
1. StationVocab embedding (2048 nodes, dim=8, zero collisions).
2. FiLM context conditioning with identity initialization.
3. Interaction Cortex cross-attention across neighbor trains.
4. RegimeMoEHead: 3 MonotoneQuantileHead experts with convex quantile-vector mixing,
   gated on 6 observable regime signals with auxiliary load-balancing loss.
5. 100% Monotone Quantile Output Guarantee by construction (convex combination of monotone vectors).
"""
from __future__ import annotations

from typing import Dict, List, Optional, Tuple, Union
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch import Tensor

ALPHAS_V3: Tuple[float, ...] = (0.05, 0.10, 0.25, 0.50, 0.75, 0.90, 0.95)
GATE_CTX_INDICES: List[int] = [21, 11, 4, 2, 15, 18]  # fog_dawn, prio, sched_min, staleness_vel, occ_pct, rake_linked


class MonotoneQuantileHead(nn.Module):
    """Median-anchored non-crossing head. Monotone BY CONSTRUCTION for any input.

    Increments are cumsum(softplus(.)) >= 0 above and below the median.
    """

    def __init__(self, hidden_dim: int, alphas: Tuple[float, ...] = ALPHAS_V3):
        super().__init__()
        self.alphas = tuple(sorted(alphas))
        K = len(self.alphas)
        self.m = min(range(K), key=lambda i: abs(self.alphas[i] - 0.5))
        self.n_up = K - 1 - self.m
        self.n_dn = self.m
        self.center = nn.Linear(hidden_dim, 1)
        self.up = nn.Linear(hidden_dim, max(self.n_up, 1))
        self.dn = nn.Linear(hidden_dim, max(self.n_dn, 1))

    def forward(self, h: Tensor) -> Tensor:
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
        return torch.cat(parts, dim=-1)  # [B, K] ascending strictly monotone


class RegimeMoEHead(nn.Module):
    """3 experts, gate on OBSERVABLE regime signals.

    Quantile-vector mixing: convex combination of monotone vectors is monotone —
    non-crossing preserved by construction (same mathematical guarantee as the deep ensemble).
    """

    def __init__(
        self,
        hidden_dim: int,
        n_experts: int = 3,
        gate_dim: int = 6,
        alphas: Tuple[float, ...] = ALPHAS_V3,
    ):
        super().__init__()
        self.n_experts = n_experts
        self.alphas = alphas
        self.experts = nn.ModuleList([MonotoneQuantileHead(hidden_dim, alphas) for _ in range(n_experts)])
        self.gate = nn.Sequential(
            nn.Linear(gate_dim, 32),
            nn.ReLU(),
            nn.Linear(32, n_experts),
        )

    def forward(self, h: Tensor, gate_ctx: Tensor) -> Tuple[Tensor, Tensor, Tensor]:
        w = torch.softmax(self.gate(gate_ctx), dim=-1)  # [B, n_experts]
        expert_outputs = [self.experts[i](h) for i in range(self.n_experts)]
        q = sum(w[:, i:i+1] * expert_outputs[i] for i in range(self.n_experts))

        load = w.mean(dim=0)
        aux = (load * torch.log(load + 1e-9)).sum()  # load-balancing (Shazeer 2017)
        return q, w, aux


class FiLM(nn.Module):
    """Feature-wise Linear Modulation. gamma uses (1+g) => identity at init."""

    def __init__(self, ctx_dim: int, feat_dim: int, hidden: int = 64):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(ctx_dim, hidden),
            nn.ReLU(),
            nn.Linear(hidden, 2 * feat_dim),
        )
        nn.init.zeros_(self.net[-1].weight)
        nn.init.zeros_(self.net[-1].bias)

    def forward(self, x: Tensor, ctx: Tensor) -> Tensor:
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

    def forward(self, h: Tensor, mask: Tensor) -> Tensor:
        s = self.score(h).squeeze(-1) - (~mask).float() * 1e9
        a = torch.softmax(s, dim=-1)
        return (a.unsqueeze(-1) * h).sum(dim=1)


class NeighborInteraction(nn.Module):
    """Interaction Cortex cross-attention to K neighbor-train tokens."""

    def __init__(self, nbr_feat_dim: int, dim: int = 128, heads: int = 4):
        super().__init__()
        self.proj = nn.Linear(nbr_feat_dim, dim)
        self.attn = nn.MultiheadAttention(dim, heads, batch_first=True)
        self.norm = nn.LayerNorm(dim)

    def forward(self, own: Tensor, nbr: Tensor, nbr_mask: Tensor) -> Tuple[Tensor, Tensor]:
        k = self.proj(nbr)
        all_pad = (~nbr_mask).all(dim=-1)
        safe_mask = ~nbr_mask
        if all_pad.any():
            safe_mask = safe_mask.clone()
            safe_mask[all_pad, 0] = False

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


class RailTwinGRUv3(nn.Module):
    """RailTwinGRUv3 with StationVocab, FiLM, Interaction Cortex, and RegimeMoEHead."""

    def __init__(
        self,
        seq_feat_dim: int = 8,
        station_emb_dim: int = 8,
        ctx_dim: int = 24,
        nbr_feat_dim: int = 12,
        hidden_dim: int = 128,
        gru_layers: int = 2,
        dropout: float = 0.0,
        vocab_size: int = 2048,
        n_experts: int = 3,
        gate_dim: int = 6,
        alphas: Tuple[float, ...] = ALPHAS_V3,
    ):
        super().__init__()
        self.alphas = alphas
        self.hidden_dim = hidden_dim
        self.seq_feat_dim = seq_feat_dim
        self.ctx_dim = ctx_dim
        self.nbr_feat_dim = nbr_feat_dim
        self.n_experts = n_experts

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
        self.gate_fuse = nn.Linear(3 * hidden_dim, hidden_dim)
        self.head = RegimeMoEHead(hidden_dim, n_experts=n_experts, gate_dim=gate_dim, alphas=alphas)

    def forward(
        self,
        seq: Tensor,
        station_ids: Tensor,
        seq_mask: Tensor,
        ctx: Tensor,
        nbr: Optional[Tensor] = None,
        nbr_mask: Optional[Tensor] = None,
        gate_ctx: Optional[Tensor] = None,
    ) -> Dict[str, Tensor]:
        B, T, _ = seq.shape
        stn_e = self.station_emb(station_ids)  # [B, T, E]
        x = torch.cat([seq, stn_e], dim=-1)   # [B, T, F+E]
        x_mod = self.film(x, ctx)             # [B, T, F+E]

        out, _ = self.gru(x_mod)              # [B, T, H]
        h_pool = self.pool(out, seq_mask)     # [B, H]

        if nbr is not None and nbr_mask is not None:
            h_inter, nbr_w = self.nbr(h_pool, nbr, nbr_mask)
        else:
            h_inter = h_pool
            nbr_w = torch.zeros((B, 1), device=seq.device)

        h_ctx = F.relu(self.ctx_proj(ctx))
        fused = F.relu(self.gate_fuse(torch.cat([h_pool, h_inter, h_ctx], dim=-1)))  # [B, H]

        if gate_ctx is None:
            if ctx.shape[-1] >= 24:
                gate_ctx = ctx[:, GATE_CTX_INDICES]
            else:
                gate_ctx = ctx[:, :6]

        q, w, aux = self.head(fused, gate_ctx)

        return {
            "quantiles": q,
            "gate_weights": w,
            "aux_loss": aux,
            "nbr_attn": nbr_w,
        }


class GRUv3Ensemble(nn.Module):
    """Uniform Deep Ensemble of RailTwinGRUv3 models."""

    def __init__(self, members: List[RailTwinGRUv3]):
        super().__init__()
        self.members = nn.ModuleList(members)

    def forward(
        self,
        seq: Tensor,
        station_ids: Tensor,
        seq_mask: Tensor,
        ctx: Tensor,
        nbr: Optional[Tensor] = None,
        nbr_mask: Optional[Tensor] = None,
        gate_ctx: Optional[Tensor] = None,
    ) -> Dict[str, Tensor]:
        outs = [
            m(
                seq=seq,
                station_ids=station_ids,
                seq_mask=seq_mask,
                ctx=ctx,
                nbr=nbr,
                nbr_mask=nbr_mask,
                gate_ctx=gate_ctx,
            )
            for m in self.members
        ]
        qs = torch.stack([o["quantiles"] for o in outs])  # [M, B, 7]
        gate_ws = torch.stack([o["gate_weights"] for o in outs]).mean(dim=0)
        aux_mean = torch.stack([o["aux_loss"] for o in outs]).mean()

        mean_q = qs.mean(dim=0)
        idx_q50 = len(ALPHAS_V3) // 2
        medians = qs[:, :, idx_q50]
        epistemic_std = medians.std(dim=0)

        return {
            "quantiles": mean_q,
            "gate_weights": gate_ws,
            "aux_loss": aux_mean,
            "epistemic_q50_std": epistemic_std,
            "member_spread": epistemic_std,
        }


class PinballCRPSLoss(nn.Module):
    """CRPS ~ 2 * mean_alpha pinball + load-balancing auxiliary loss."""

    def __init__(
        self,
        alphas: Tuple[float, ...] = ALPHAS_V3,
        w_pair: Tuple[float, float] = (0.05, 0.95),
        w_weight: float = 0.1,
        aux_weight: float = 0.01,
    ):
        super().__init__()
        self.register_buffer("alphas", torch.tensor(alphas, dtype=torch.float32))
        self.i_lo = alphas.index(w_pair[0])
        self.i_hi = alphas.index(w_pair[1])
        self.alpha_w = w_pair[0] + (1.0 - w_pair[1])
        self.w = w_weight
        self.aux_weight = aux_weight

    def forward(self, preds: Tensor, target: Tensor, aux_loss: Tensor) -> Tuple[Tensor, Dict[str, float]]:
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

        total_loss = crps + self.w * winkler_term + self.aux_weight * aux_loss
        return total_loss, {
            "crps": crps.item(),
            "winkler": winkler_term.item(),
            "aux": aux_loss.item(),
        }
