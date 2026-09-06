import json
from pathlib import Path

metrics_path = Path("ml/artifacts/metrics.json")
with open(metrics_path, "r", encoding="utf-8") as f:
    m = json.load(f)

print("Top-level keys in metrics.json:", list(m.keys()))
print("Canonical MAE:", m.get("canonical_mae"))
print("Canonical CRPS:", m.get("canonical_crps"))
print("Canonical Winkler:", m.get("canonical_winkler"))
print("Canonical Coverage:", m.get("canonical_coverage_80"))

cv = m.get("rolling_origin_cv", {})
folds = cv.get("folds", [])
print(f"\nRolling-origin CV folds count: {len(folds)}")
total_fold_samples = 0
for idx, fold in enumerate(folds):
    samples = fold.get("samples")
    print(f"  Fold {idx+1}: train={fold.get('train_window')} -> test={fold.get('test_window')}, samples={samples}, error={fold.get('error')}")
    if isinstance(samples, int):
        total_fold_samples += samples

print(f"Total samples across valid folds: {total_fold_samples}")

horizons = m.get("metrics_by_horizon", {})
print("\nMetrics by Horizon:")
for h_name, h_vals in horizons.items():
    print(f"  [{h_name}]:")
    for k, v in h_vals.items():
        print(f"    {k}: {v}")
