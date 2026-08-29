"""RailTwin-X Explainable AI (XAI) Engine (F13).

Provides:
1. Fast Exact TreeSHAP feature contributions for LightGBM models.
2. Integrated Gradients attribution for PyTorch Sequence GRU models.
3. Feature attribution explanation dictionaries for operational dispatchers and regulatory audits.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple
import lightgbm as lgb
import numpy as np
import pandas as pd
import torch

from ml.features import FEATURE_NAMES
from ml.model_seq import NonCrossingGRUQuantileModel


class ModelExplainer:
    """Computes mathematically grounded local feature contributions for predictions."""

    def __init__(
        self,
        gbm_booster: Optional[lgb.Booster] = None,
        gru_model: Optional[NonCrossingGRUQuantileModel] = None,
    ):
        self.gbm_booster = gbm_booster
        self.gru_model = gru_model

    def explain_lightgbm_shap(self, feature_row: pd.DataFrame) -> Dict[str, float]:
        """Calculates exact TreeSHAP feature attributions using LightGBM pred_contrib."""
        if self.gbm_booster is None:
            return {}

        df_in = feature_row[FEATURE_NAMES]
        # pred_contrib=True returns [1, num_features + 1] with the last column being expected value (bias)
        shap_values = self.gbm_booster.predict(df_in, pred_contrib=True)[0]
        feature_shaps = shap_values[:-1]
        bias = float(shap_values[-1])

        attributions = {}
        for name, val in zip(FEATURE_NAMES, feature_shaps):
            attributions[name] = float(np.round(val, 3))

        # Sort by absolute impact
        sorted_attributions = dict(sorted(attributions.items(), key=lambda item: abs(item[1]), reverse=True))
        return {
            "base_value": round(bias, 2),
            "feature_attributions": sorted_attributions,
            "top_drivers": list(sorted_attributions.keys())[:5],
        }

    def explain_gru_integrated_gradients(
        self,
        input_tensor: torch.Tensor,
        baseline: Optional[torch.Tensor] = None,
        steps: int = 20,
    ) -> Dict[str, Any]:
        """Approximates Integrated Gradients for PyTorch GRU:

        IG_i(x) = (x_i - x'_i) * integral_0^1 (d F(x' + alpha(x - x')) / d x_i) d alpha
        """
        if self.gru_model is None:
            return {}

        self.gru_model.eval()
        device = next(self.gru_model.parameters()).device
        x = input_tensor.to(device).clone().detach()

        if baseline is None:
            baseline = torch.zeros_like(x)
        else:
            baseline = baseline.to(device)

        # Generate interpolated inputs
        alphas = torch.linspace(0.0, 1.0, steps, device=device)
        delta = x - baseline
        interpolated = baseline + alphas[:, None, None, None] * delta.unsqueeze(0)  # [steps, B, seq, feat]

        total_grads = torch.zeros_like(x)

        for step in range(steps):
            interp_x = interpolated[step].clone().requires_grad_(True)
            _, q50, _ = self.gru_model(interp_x)
            q50.sum().backward()
            if interp_x.grad is not None:
                total_grads += interp_x.grad

        avg_grads = total_grads / steps
        integrated_grads = (delta * avg_grads).detach().cpu().numpy()[0]  # [seq_len, feat_dim]

        return {
            "integrated_gradients": integrated_grads.tolist(),
            "sequence_feature_importance": np.abs(integrated_grads).mean(axis=0).tolist(),
        }
