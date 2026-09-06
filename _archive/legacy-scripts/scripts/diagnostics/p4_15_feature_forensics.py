# -*- coding: utf-8 -*-
"""Per-feature forensics on the TRAINED v2 ensemble. NO RETRAINING.
Outputs control-room/23_DIAGNOSTICS/feature_forensics.csv + verdict table."""
import sys, os, warnings
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd
from scipy import stats, cluster
import torch
import torch.nn as nn
from torch.utils.data import DataLoader

from data.db import Database, get_db
from ml.evaluate_v2 import crps_grid, to_common_grid, COMMON_GRID
from ml.features import FEATURE_NAMES_V2
from ml.model_v2 import ALPHAS_V2, RailTwinGRUv2
from ml.train_v2 import GRUv2Ensemble, build_v2_dataset, get_full_corpus_splits
from ml.vocab import StationVocab

OUT = Path("control-room/23_DIAGNOSTICS"); OUT.mkdir(parents=True, exist_ok=True)
rng = np.random.default_rng(7)
N_PERM = 5

db_path = "data/railtwin.db"
db_inst = get_db()
vocab = StationVocab.from_db(db_path)
splits = get_full_corpus_splits(db_inst)

print("Loading TRAIN, VAL, BENCH splits...")
val_ds = build_v2_dataset(db_inst, vocab, allowed_dates=splits["val_dates"], max_samples=4000)
train_ds = build_v2_dataset(db_inst, vocab, allowed_dates=splits["train_dates"], max_samples=4000)
bench_ds = build_v2_dataset(db_inst, vocab, allowed_dates=splits["bench_fog_dates"], max_samples=2000)

val_ctx = np.array([val_ds[i]["ctx"].numpy() for i in range(len(val_ds))])
val_y = np.array([val_ds[i]["target"].item() for i in range(len(val_ds))])
val_seq = torch.stack([val_ds[i]["seq"] for i in range(len(val_ds))])
val_stn = torch.stack([val_ds[i]["station_ids"] for i in range(len(val_ds))])
val_smask = torch.stack([val_ds[i]["seq_mask"] for i in range(len(val_ds))])
val_nbr = torch.stack([val_ds[i]["nbr"] for i in range(len(val_ds))])
val_nmask = torch.stack([val_ds[i]["nbr_mask"] for i in range(len(val_ds))])

train_ctx = np.array([train_ds[i]["ctx"].numpy() for i in range(len(train_ds))])
train_y = np.array([train_ds[i]["target"].item() for i in range(len(train_ds))])
bench_ctx = np.array([bench_ds[i]["ctx"].numpy() for i in range(len(bench_ds))])

val_df = pd.DataFrame(val_ctx, columns=FEATURE_NAMES_V2)
val_df["y"] = val_y
train_df = pd.DataFrame(train_ctx, columns=FEATURE_NAMES_V2)
train_df["y"] = train_y
bench_df = pd.DataFrame(bench_ctx, columns=FEATURE_NAMES_V2)

print(f"Loaded: |val|={len(val_df):,}, |train|={len(train_df):,}, |bench|={len(bench_df):,}")

# Load Challenger Deep Ensemble
device = torch.device("cpu")
seeds = [11, 22, 33]
members = []
for s in seeds:
    m_path = Path("ml/artifacts_v2") / f"model_gru_seed_{s}.pt"
    assert m_path.exists(), f"Missing challenger seed checkpoint: {m_path}"
    m = RailTwinGRUv2(
        seq_feat_dim=8,
        station_emb_dim=8,
        ctx_dim=len(FEATURE_NAMES_V2),
        nbr_feat_dim=12,
        hidden_dim=128,
        gru_layers=2,
        dropout=0.0,
        vocab_size=len(vocab),
    )
    m.load_state_dict(torch.load(m_path, map_location=device, weights_only=True))
    m.eval()
    members.append(m)

ensemble = GRUv2Ensemble(members).to(device)
ensemble.eval()

def score_ctx_matrix(ctx_mat: np.ndarray) -> float:
    ctx_tensor = torch.tensor(ctx_mat, dtype=torch.float32)
    batch_size = 512
    all_qs = []
    with torch.no_grad():
        for i in range(0, len(ctx_tensor), batch_size):
            out = ensemble(
                seq=val_seq[i:i+batch_size],
                station_ids=val_stn[i:i+batch_size],
                seq_mask=val_smask[i:i+batch_size],
                ctx=ctx_tensor[i:i+batch_size],
                nbr=val_nbr[i:i+batch_size],
                nbr_mask=val_nmask[i:i+batch_size],
            )
            all_qs.append(out["quantiles"].numpy())
    qs_np = np.concatenate(all_qs, axis=0)
    qs_grid = to_common_grid(qs_np, ALPHAS_V2)
    return float(crps_grid(val_y, qs_grid))

base_crps = score_ctx_matrix(val_ctx)
print(f"\nBaseline Validation CRPS (49-pt grid) = {base_crps:.4f}")

def psi(expected, actual, bins=10, eps=1e-6):
    expected, actual = np.asarray(expected, float), np.asarray(actual, float)
    expected, actual = expected[~np.isnan(expected)], actual[~np.isnan(actual)]
    if len(expected) < 50 or len(actual) < 50: return float("nan")
    edges = np.unique(np.quantile(expected, np.linspace(0, 1, bins+1)))
    if len(edges) < 3: return float("nan")
    edges[0], edges[-1] = -np.inf, np.inf
    e = np.clip(np.histogram(expected, edges)[0]/len(expected), eps, None)
    a = np.clip(np.histogram(actual, edges)[0]/len(actual), eps, None)
    return float(np.sum((a-e)*np.log(a/e)))

rows = []
for idx, f in enumerate(FEATURE_NAMES_V2):
    if val_df[f].nunique() > 1:
        rho, pval = stats.spearmanr(val_df[f], val_df["y"])
        if not np.isfinite(rho): rho = 0.0
    else:
        rho = 0.0
    
    # Permutation importance (5 repeats)
    if val_df[f].nunique() > 1:
        perm_diffs = []
        for _ in range(N_PERM):
            shuffled_ctx = val_ctx.copy()
            shuffled_ctx[:, idx] = rng.permutation(shuffled_ctx[:, idx])
            perm_crps = score_ctx_matrix(shuffled_ctx)
            perm_diffs.append(perm_crps - base_crps)
        d_perm = float(np.mean(perm_diffs))
        
        zero_ctx = val_ctx.copy()
        zero_ctx[:, idx] = float(train_df[f].mean())
        d_zero = score_ctx_matrix(zero_ctx) - base_crps
    else:
        d_perm = 0.0
        d_zero = 0.0
    
    psi_val = psi(train_df[f], bench_df[f])
    
    rows.append({
        "feature": f,
        "variance": float(np.var(val_df[f])),
        "nunique": int(val_df[f].nunique()),
        "null_train": float(train_df[f].isna().mean()),
        "null_bench": float(bench_df[f].isna().mean()),
        "psi_train_bench": psi_val,
        "spearman": float(rho),
        "perm_dCRPS": d_perm,
        "perm_dCRPS_pct": 100.0 * d_perm / base_crps,
        "zero_dCRPS": d_zero,
        "zero_dCRPS_pct": 100.0 * d_zero / base_crps,
    })
    print(f"  {f:<35s} perm=+{100*d_perm/base_crps:6.2f}%  zero={100*d_zero/base_crps:+6.2f}%  "
          f"rho={rho:6.3f}  nuniq={val_df[f].nunique():>4}")

df = pd.DataFrame(rows).sort_values("perm_dCRPS_pct", ascending=False)

# Redundancy clustering on |Spearman| >= 0.90
active_feats = [f for f in FEATURE_NAMES_V2 if val_df[f].nunique() > 1]
corr_df = val_df[active_feats].corr(method="spearman").abs()
corr_mat = corr_df.to_numpy(copy=True)
np.fill_diagonal(corr_mat, 0.0)
D = 1.0 - corr_mat
redundant_kills = set()
try:
    link = cluster.hierarchy.linkage(cluster.hierarchy.squareform(D, checks=False), "average")
    lab = cluster.hierarchy.fcluster(link, t=0.10, criterion="distance")
    clusters = {}
    for f, l in zip(active_feats, lab): clusters.setdefault(l, []).append(f)
    print("\nRedundancy clusters (|rho| >= 0.90):")
    for l, fs in clusters.items():
        if len(fs) > 1:
            keep = df[df.feature.isin(fs)].iloc[0].feature
            kills = [x for x in fs if x != keep]
            redundant_kills.update(kills)
            print(f"  Cluster {l}: {fs} -> KEEP {keep}, KILL (redundant): {kills}")
except Exception as e:
    print(f"Clustering skipped: {e}")

# LightGBM cross-check
try:
    import lightgbm as lgb
    active_cols = [c for c in FEATURE_NAMES_V2 if train_df[c].nunique() > 1]
    Xt = train_df[active_cols]; yt = train_df["y"]
    m = lgb.train({"objective": "regression", "verbosity": -1, "num_leaves": 31},
                  lgb.Dataset(Xt, yt), num_boost_round=150)
    gain = pd.Series(m.feature_importance("gain"), index=active_cols)
    gain_share = 100.0 * gain / max(1.0, gain.sum())
    df["lgbm_gain_share_pct"] = df.feature.map(gain_share).fillna(0.0)
    print("\nLightGBM gain share (top 10):")
    print(gain_share.sort_values(ascending=False).head(10).to_string())
except Exception as e:
    print(f"LightGBM cross-check skipped: {e}")
    df["lgbm_gain_share_pct"] = 0.0

# Pre-committed verdicts
print("\n" + "="*72); print("PRE-COMMITTED VERDICTS"); print("="*72)
verdicts = []
for _, r in df.iterrows():
    f = r["feature"]
    if r["perm_dCRPS_pct"] > 15.0:
        v = "AUDIT-LEAK (suspiciously high importance - audit point-in-time computation)"
    elif f in redundant_kills:
        v = "KILL (redundant)"
    elif f in ("upstream_rake_delay_min", "upstream_rake_buffer_remaining_min", "rake_linked",
               "fog_flag_target", "rain_mm_target", "tsr_active_ahead_count", "tsr_max_slowdown_pct"):
        v = "UPGRADE (domain causal - fix registry/wiring)"
    elif r["variance"] < 1e-9 or r["nunique"] <= 2 or (r["perm_dCRPS_pct"] < 0.1 and r["lgbm_gain_share_pct"] < 0.5):
        v = "KILL (dead/uninformative)"
    else:
        v = "KEEP"
    verdicts.append(v)
    print(f"  {f:<35s} -> {v}")

df["verdict"] = verdicts
df.to_csv(OUT / "feature_forensics.csv", index=False)
print(f"\nfeature_forensics.csv saved to {OUT / 'feature_forensics.csv'}")
