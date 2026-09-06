import json
import lightgbm as lgb
from pathlib import Path

art_dir = Path("ml/artifacts")
models = {}
for q in [10, 50, 90]:
    p = art_dir / f"model_direct_q{q}.txt"
    if p.exists():
        bst = lgb.Booster(model_file=str(p))
        models[f"q{q}"] = bst.feature_name()

print("LightGBM Model Direct Feature Names:")
for k, v in models.items():
    print(f"{k} (count={len(v)}): {v}")

# Now inspect api/predictor.py and ml/snapshots.py to see what features are constructed
from api.predictor import get_predictor_service
ps = get_predictor_service()
print("\nPredictorService champion:", ps.champion_name)
print("PredictorService direct models loaded:", bool(ps._direct_models))
print("PredictorService GRU model loaded:", bool(ps._gru_model))

# Let's check how predictor builds features for a train
sample = ps.predict_train_eta("12301", "CNB")
print("\nSample prediction output keys:", list(sample.keys()) if sample else None)
print("Predicted delay p50:", sample.get("pred_delay_p50") or sample.get("predicted_delay_min"))
