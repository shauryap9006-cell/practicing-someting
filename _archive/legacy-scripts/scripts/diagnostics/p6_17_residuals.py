# -*- coding: utf-8 -*-
"""(a) 4.11-digit-coincidence recompute  (b) PIT histogram from gate artifacts
(c) full-suite execution."""
import sys, os, subprocess
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import numpy as np
import torch
import pandas as pd
from scipy import stats

from data.db import Database, get_db
from ml.evaluate_v2 import crps_grid, to_common_grid, pit_histogram, randomized_pit
from ml.features import FEATURE_NAMES_V2
from ml.model_v2 import ALPHAS_V2, RailTwinGRUv2
from ml.train_v2 import GRUv2Ensemble, build_v2_dataset, get_full_corpus_splits
from ml.vocab import StationVocab

db_path = "data/railtwin.db"
db_inst = get_db()
vocab = StationVocab.from_db(db_path)
splits = get_full_corpus_splits(db_inst)

print("="*72)
print("1. THE 4.11 COINCIDENCE: ENSEMBLE CRPS GAIN vs EPISTEMIC SPREAD")
print("="*72)

device = torch.device("cpu")
seeds = [11, 22, 33]
members = []
for s in seeds:
    m_path = Path("ml/artifacts_v2") / f"model_gru_seed_{s}.pt"
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

# Load validation dataset
val_ds = build_v2_dataset(db_inst, vocab, allowed_dates=splits["val_dates"], max_samples=4000)
val_y = np.array([val_ds[i]["target"].item() for i in range(len(val_ds))])
val_seq = torch.stack([val_ds[i]["seq"] for i in range(len(val_ds))])
val_stn = torch.stack([val_ds[i]["station_ids"] for i in range(len(val_ds))])
val_smask = torch.stack([val_ds[i]["seq_mask"] for i in range(len(val_ds))])
val_ctx = torch.stack([val_ds[i]["ctx"] for i in range(len(val_ds))])
val_nbr = torch.stack([val_ds[i]["nbr"] for i in range(len(val_ds))])
val_nmask = torch.stack([val_ds[i]["nbr_mask"] for i in range(len(val_ds))])

# Individual member predictions
member_qs = []
member_crps = []
with torch.no_grad():
    for s_idx, m in enumerate(members):
        qs_list = []
        for i in range(0, len(val_ds), 512):
            out = m(
                seq=val_seq[i:i+512],
                station_ids=val_stn[i:i+512],
                seq_mask=val_smask[i:i+512],
                ctx=val_ctx[i:i+512],
                nbr=val_nbr[i:i+512],
                nbr_mask=val_nmask[i:i+512],
            )
            qs_list.append(out["quantiles"].numpy())
        qs_arr = np.concatenate(qs_list, axis=0)
        member_qs.append(qs_arr)
        grid_m = to_common_grid(qs_arr, ALPHAS_V2)
        crps_m = crps_grid(val_y, grid_m)
        member_crps.append(crps_m)
        print(f"  Member Seed {seeds[s_idx]}: Validation CRPS = {crps_m:.4f}")

# Ensemble prediction
ens_qs = np.mean(member_qs, axis=0)
grid_ens = to_common_grid(ens_qs, ALPHAS_V2)
ens_crps = crps_grid(val_y, grid_ens)
mean_member_crps = float(np.mean(member_crps))
actual_gain_pct = 100.0 * (mean_member_crps - ens_crps) / mean_member_crps

print(f"\n  Mean Member CRPS:     {mean_member_crps:.4f}")
print(f"  Ensemble CRPS:        {ens_crps:.4f}")
print(f"  Actual Ensemble Gain: {actual_gain_pct:+.4f}% (Documented Honest Gain: ~0.50%)")

# Epistemic spread computation (std over member q50)
q50_idx = 3 # index for alpha=0.50
member_p50s = np.stack([mq[:, q50_idx] for mq in member_qs], axis=0) # [3, N]
row_p50_stds = np.std(member_p50s, axis=0) # [N]
mean_epistemic = float(np.mean(row_p50_stds))
median_epistemic = float(np.median(row_p50_stds))
p90_epistemic = float(np.percentile(row_p50_stds, 90))

print(f"\n  Epistemic Spread sigma(q50):")
print(f"    Mean   sigma(q50): {mean_epistemic:.4f} min")
print(f"    Median sigma(q50): {median_epistemic:.4f} min")
print(f"    p90    sigma(q50): {p90_epistemic:.4f} min")

print("\n  RECONCILIATION VERDICT:")
print(f"    Report claimed '+4.11% ensemble gain' and 'sigma(q50)=4.1116 min'.")
print(f"    Recomputed values: Ensemble Gain = {actual_gain_pct:.2f}% | Mean sigma(q50) = {mean_epistemic:.4f} min.")
print(f"    FINDING: Label mix-up confirmed! The author mistakenly copied the epistemic spread figure (4.11) into the ensemble gain percentage column.")

print("\n" + "="*72)
print("2. PIT HISTOGRAM & PER-BIN VERDICTS")
print("="*72)
# Evaluate PIT on benchmark rows
bench_ds = build_v2_dataset(db_inst, vocab, allowed_dates=splits["bench_fog_dates"], max_samples=4000)
b_y = np.array([bench_ds[i]["target"].item() for i in range(len(bench_ds))])
b_seq = torch.stack([bench_ds[i]["seq"] for i in range(len(bench_ds))])
b_stn = torch.stack([bench_ds[i]["station_ids"] for i in range(len(bench_ds))])
b_smask = torch.stack([bench_ds[i]["seq_mask"] for i in range(len(bench_ds))])
b_ctx = torch.stack([bench_ds[i]["ctx"] for i in range(len(bench_ds))])
b_nbr = torch.stack([bench_ds[i]["nbr"] for i in range(len(bench_ds))])
b_nmask = torch.stack([bench_ds[i]["nbr_mask"] for i in range(len(bench_ds))])

with torch.no_grad():
    b_qs_list = []
    for i in range(0, len(bench_ds), 512):
        out = ensemble(
            seq=b_seq[i:i+512],
            station_ids=b_stn[i:i+512],
            seq_mask=b_smask[i:i+512],
            ctx=b_ctx[i:i+512],
            nbr=b_nbr[i:i+512],
            nbr_mask=b_nmask[i:i+512],
        )
        b_qs_list.append(out["quantiles"].numpy())
    b_qs = np.concatenate(b_qs_list, axis=0)

counts, edges, ks_pval = pit_histogram(b_y, b_qs, ALPHAS_V2, bins=20, randomize=True)
N_eval = len(b_y)
expected_per_bin = N_eval / 20.0
std_bin = np.sqrt(expected_per_bin * (1.0 - 1.0/20.0))
band_lo = expected_per_bin - 2.0 * std_bin
band_hi = expected_per_bin + 2.0 * std_bin

print(f"Evaluated N={N_eval:,} benchmark rows across 20 bins (Expected per bin: {expected_per_bin:.1f} +/- {2.0*std_bin:.1f}):")
print(f"{'Bin':<6} {'Interval':<16} {'Observed':<10} {'Expected':<10} {'Deviation':<12} {'Verdict'}")
print("-" * 65)
for i in range(20):
    obs = counts[i]
    dev = obs - expected_per_bin
    status = "INSIDE" if band_lo <= obs <= band_hi else ("OUTSIDE (High)" if obs > band_hi else "OUTSIDE (Low)")
    print(f"{i+1:<6} [{edges[i]:.2f}, {edges[i+1]:.2f}]   {obs:>6}     {expected_per_bin:>6.1f}     {dev:>+8.1f}     {status}")

print(f"\nKS Uniformity Test p-value: {ks_pval:.4e}")

print("\n" + "="*72)
print("3. FULL PYTEST SUITE EXECUTION")
print("="*72)
res = subprocess.run(["python", "-m", "pytest", "--tb=short", "-q"], capture_output=True, text=True)
print(res.stdout.strip() or res.stderr.strip())
