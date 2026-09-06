import numpy as np
import torch
import lightgbm as lgb
from pathlib import Path
from api.predictor import get_predictor_service
from ml.model_seq import NonCrossingGRUQuantileModel

ps = get_predictor_service()
art_dir = Path("ml/artifacts")
direct_10 = lgb.Booster(model_file=str(art_dir / "model_direct_q10.txt"))
direct_50 = lgb.Booster(model_file=str(art_dir / "model_direct_q50.txt"))
direct_90 = lgb.Booster(model_file=str(art_dir / "model_direct_q90.txt"))

# Base feature vector from a real prediction
vec = ps.snapshot_gen.extract_features_at_snapshot(
    train_no="12301",
    current_seq=1,
    target_seq=5,
    run_date_str="2026-08-20",
    current_delay=15.0,
    prev_delay=10.0,
    query_time_iso="2026-08-20T10:00:00+05:30"
)
base_feat = vec.to_numpy_v1() # shape (1, 25)

np.random.seed(42)
lgb_violations = 0
gru_violations = 0
serving_violations = 0
q_hat = ps._q_hat

print(f"Testing 1000 perturbed predictions (base_feat shape={base_feat.shape}, q_hat={q_hat})...")

for i in range(1000):
    # Perturb features sensibly
    noise = np.random.normal(0, 0.25, base_feat.shape)
    feat = np.maximum(0, base_feat * (1.0 + noise))
    
    # 1. LightGBM Direct
    p10_lgb = float(direct_10.predict(feat)[0]) - q_hat
    p50_lgb = float(direct_50.predict(feat)[0])
    p90_lgb = float(direct_90.predict(feat)[0]) + q_hat
    if not (p10_lgb <= p50_lgb <= p90_lgb):
        lgb_violations += 1

    # 2. PyTorch GRU
    x = torch.randn(1, 8, 8).abs()
    with torch.no_grad():
        q10_g, q50_g, q90_g = ps._gru_model(x)
        p10_gru = q10_g.item() - ps._q_hat_gru
        p50_gru = q50_g.item()
        p90_gru = q90_g.item() + ps._q_hat_gru
    if not (p10_gru <= p50_gru <= p90_gru):
        gru_violations += 1

print(f"LightGBM Quantile Crossing Violations: {lgb_violations} / 1000")
print(f"PyTorch GRU Quantile Crossing Violations: {gru_violations} / 1000")
