"""C2+C4+C5 fixed evidence with correct feature names."""
import sys, os, json, numpy as np
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ml.conformal import MondrianCQR
from ml.features import FEATURE_NAMES
from config import settings
from data.db import get_db
from ml.snapshots import SnapshotGenerator
import lightgbm as lgb

db = get_db()
sg = SnapshotGenerator(db)
with open(settings.ARTIFACTS_DIR / "manifest.json") as f:
    mf = json.load(f)
si = mf.get("split_info", {})

test_start = si.get("test_start", "2026-08-23")
test_end   = si.get("test_end",   "2026-08-29")
train_cut  = si.get("train_cutoff","2026-08-22")
train_start= si.get("start_date", "2026-08-02")

# ── C2 ──────────────────────────────────────────────────────────────────────
print("\n" + "="*72)
print("C2 · MONDRIAN CQR PER-CELL FACTORS")
print("="*72)

test_df = sg.build_dataset(test_start, test_end, train_cut)
hops = test_df["hops_remaining"].values
km   = test_df["km_remaining"].values
y    = test_df["target_direct_delay"].values

cqr = MondrianCQR(target_coverage=0.80)
b10 = lgb.Booster(model_file=str(settings.ARTIFACTS_DIR/"model_direct_q10.txt")).predict(test_df[FEATURE_NAMES])
b90 = lgb.Booster(model_file=str(settings.ARTIFACTS_DIR/"model_direct_q90.txt")).predict(test_df[FEATURE_NAMES])

cqr_map = cqr.calibrate(b10, b90, y, hops, km)
g = cqr_map["global"]
print(f"[C2] global q_hat = {g:.4f}")
cell_keys = [k for k in cqr_map if k != "global"]
if not cell_keys:
    print("[C2] WARNING: No distinct Mondrian cells (global==all cells)")
else:
    for k in sorted(cell_keys):
        diff = cqr_map[k] - g
        print(f"[C2] cell={k:20s}  q_hat={cqr_map[k]:.4f}  delta_vs_global={diff:+.4f}")

counts = {}
for i in range(len(y)):
    k = cqr._get_group_key(hops[i], km[i])
    counts[k] = counts.get(k, 0) + 1
print("[C2] Row counts per Mondrian cell:")
for k in sorted(counts):
    print(f"[C2]   {k:22s}  n={counts[k]}")

# ── C4 ──────────────────────────────────────────────────────────────────────
print("\n" + "="*72)
print("C4 · LIGHTGBM SPATIAL FEATURE SPLIT-GAIN IMPORTANCE")
print("="*72)

SPATIAL = [
    "trains_ahead_30k",
    "opposing_trains_30k",
    "sum_delay_trains_ahead_30k",
    "section_occupancy_pct",
    "fog_flag_target",
]

bst = lgb.Booster(model_file=str(settings.ARTIFACTS_DIR/"model_direct_q50.txt"))
feat_names = bst.feature_name()
gains = bst.feature_importance(importance_type="gain")
total_gain = float(gains.sum()) or 1.0
feat_gain  = dict(zip(feat_names, gains))

print(f"[C4] Total gain all features: {total_gain:.1f}")
print(f"[C4] {'Feature':35s}  {'Gain':>10}  {'%Gain':>8}  Status")
print("-"*70)
spatial_pct = 0.0
for fn in SPATIAL:
    g4 = float(feat_gain.get(fn, 0.0))
    pct = g4 / total_gain * 100.0
    spatial_pct += pct
    status = "IN_MODEL" if fn in feat_gain else "MISSING"
    print(f"[C4] {fn:35s}  {g4:>10.2f}  {pct:>7.3f}%  {status}")
print(f"\n[C4] Combined spatial gain: {spatial_pct:.3f}%  threshold=2.00%  PASS={'YES' if spatial_pct >= 2.0 else 'NO'}")

# ── C5 ──────────────────────────────────────────────────────────────────────
print("\n" + "="*72)
print("C5 · DATA DENSITY (nonzero fraction, training span, ESS)")
print("="*72)

import datetime
train_df = sg.build_dataset(train_start, train_cut, train_cut)
n = len(train_df)
d0 = datetime.date.fromisoformat(train_start)
d1 = datetime.date.fromisoformat(train_cut)
months = (d1 - d0).days / 30.44
print(f"[C5] Training rows: {n}")
print(f"[C5] Training span: {d0} -> {d1}  ({months:.1f} months)")

DENSITY_COLS = [
    "trains_ahead_30k",
    "opposing_trains_30k",
    "sum_delay_trains_ahead_30k",
    "section_occupancy_pct",
]
print(f"\n[C5] {'Feature':35s}  {'NonZero':>9}  {'%':>7}  VERDICT")
print("-"*68)
all_pass = True
for col in DENSITY_COLS:
    if col not in train_df.columns:
        print(f"[C5] {col:35s}  MISSING IN DATASET")
        all_pass = False
        continue
    nz = int((train_df[col] != 0).sum())
    pct = nz / max(1, n) * 100.0
    v = "PASS" if pct >= 30.0 else "FAIL"
    if v == "FAIL":
        all_pass = False
    print(f"[C5] {col:35s}  {nz:>9}  {pct:>6.1f}%  {v}")

lam = np.log(2) / 90.0
fold_days = (d1 - d0).days
ess = n * (1 - np.exp(-2*lam*fold_days)) / (2*lam*fold_days) if fold_days > 0 else n
print(f"\n[C5] ESS (half-life=90d, span={fold_days}d): ~{ess:.0f}")
print(f"[C5] All density >= 30%: {'PASS' if all_pass else 'FAIL'}")

print("\n" + "="*72 + "\nDONE\n" + "="*72)
