# -*- coding: utf-8 -*-
"""Decide: Branch A (champion integration bug) / Branch B (corrupt targets) /
Branch C (wrong DB lineage). HALT if Branch B."""
import sqlite3, gzip, shutil, json, os, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import numpy as np
import torch
import pandas as pd
from torch.utils.data import DataLoader

from data.db import Database, get_db
from ml.model_seq import NonCrossingGRUQuantileModel
from ml.vocab import StationVocab
from ml.train_v2 import build_v2_dataset, get_full_corpus_splits
from ml.seq_dataset import SequenceDatasetBuilder, RailwaySequenceDataset

def ensure_db():
    p = Path("data/railtwin.db")
    if not p.exists():
        gz = Path("data/railtwin.db.gz")
        assert gz.exists(), "neither railtwin.db nor railtwin.db.gz found"
        with gzip.open(gz, "rb") as fi, open(p, "wb") as fo: shutil.copyfileobj(fi, fo)
        print(f"[extracted] {gz} -> {p}")
    return str(p)

db_path = ensure_db()
con = sqlite3.connect(db_path); con.row_factory = sqlite3.Row

def cols(tbl): return [r["name"] for r in con.execute(f"PRAGMA table_info({tbl})")]
def find_col(tbl, candidates):
    have = set(cols(tbl))
    for c in candidates:
        if c in have: return c
    return None

print("="*72); print("PART A -- DB LINEAGE & TARGET DISTRIBUTION BY ERA"); print("="*72)
tables = [r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
print("tables:", tables)

# Documented vs actual corpus size
for t in ("station_events", "route_stations", "trains", "stations", "weather"):
    if t in tables:
        n = con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
        print(f"{t:18s}: {n:>10,} rows")

dcol = find_col("station_events", ["delay_arr_min", "delay_min", "arr_delay", "delay", "arrival_delay",
                                   "actual_arr_delay", "delay_minutes"])
tcol = find_col("station_events", ["train_no", "train_number"])
rcol = find_col("station_events", ["run_date", "run_dt", "date"])
print(f"\ndetected columns: delay={dcol} train={tcol} run_date={rcol}")
assert dcol and tcol and rcol, "column detection failed"

print("\nTarget (delay) distribution by era in station_events:")
for r in con.execute(f"""
    SELECT CASE WHEN {rcol} < '2025-07-01' THEN 'recovered_2025' ELSE 'recent_2026' END era,
           COUNT(*) n, MIN({dcol}) mn, AVG({dcol}) av, MAX({dcol}) mx,
           AVG(CASE WHEN {dcol} > 600 OR {dcol} < -120 THEN 1.0 ELSE 0.0 END) oob
    FROM station_events GROUP BY era"""):
    print(f"  {r['era']:15s} n={r['n']:>10,}  min={r['mn']:>12.1f}  avg={r['av']:>9.2f}  "
          f"max={r['mx']:>14.1f}  frac_out_of_bounds={r['oob']:.4%}")
    if r["oob"] > 0.01:
        print(f"  *** P0 FLAG: >1% of {r['era']} targets outside [-120,600] -- Branch B evidence ***")

print("\nMonthly target means (unit-drift detector -- 2025 vs 2026 scale check):")
for r in con.execute(f"""
    SELECT substr({rcol},1,7) mon, COUNT(*) n, AVG({dcol}) av, MIN({dcol}) mn, MAX({dcol}) mx
    FROM station_events GROUP BY mon ORDER BY mon"""):
    print(f"  {r['mon']}  n={r['n']:>9,}  avg_delay={r['av']:>10.2f}  min={r['mn']:>8.1f}  max={r['mx']:>10.1f}")

print("\n" + "="*72)
print("PART B -- CHAMPION INFERENCE AUDIT & CONTROL EXPERIMENTS")
print("="*72)

device = torch.device("cpu")
champ_pt = Path("ml/artifacts/model_gru_challenger.pt")
assert champ_pt.exists(), f"Champion checkpoint missing: {champ_pt}"

champion_model = NonCrossingGRUQuantileModel(
    input_dim=8,
    context_dim=25,
    hidden_dim=128,
    num_layers=2,
    dropout=0.2,
)
state = torch.load(champ_pt, map_location=device, weights_only=False)
champion_model.load_state_dict(state)
champion_model.eval()

# Experiment 1: Exact champion_gate.py execution path on benchmark rows
db_inst = get_db()
vocab = StationVocab.from_db(db_path)
splits = get_full_corpus_splits(db_inst)
fog_dates = splits["bench_fog_dates"]

eval_ds = build_v2_dataset(db_inst, vocab, allowed_dates=fog_dates, max_samples=2000)
eval_loader = DataLoader(eval_ds, batch_size=256, shuffle=False)

champ_gate_q50 = []
champ_gate_y = []
champ_isolated_q50 = [] # When context and target_station_idx are None (as during training)

with torch.no_grad():
    for b in eval_loader:
        # EXACT champion_gate.py line 194-198 call:
        seq_8 = b["seq"][:, -8:, :]
        ctx_25 = b["ctx"][:, :25]
        mask_8 = b["seq_mask"][:, -8:]
        stn_idx = b["station_ids"][:, -1] % champion_model.num_stations
        q10_c, q50_c, q90_c = champion_model(seq_8, ctx_25, mask_8, stn_idx)
        champ_gate_q50.append(q50_c.squeeze(-1).numpy())
        champ_gate_y.append(b["target"].numpy())

        # Isolated call (as trained in model_seq.py: model(batch_x)):
        q10_iso, q50_iso, q90_iso = champion_model(seq_8)
        champ_isolated_q50.append(q50_iso.squeeze(-1).numpy())

gate_q50 = np.concatenate(champ_gate_q50)
iso_q50 = np.concatenate(champ_isolated_q50)
y_bench = np.concatenate(champ_gate_y)

print(f"Benchmark sample size: {len(y_bench):,} rows")
print(f"Targets y: min={y_bench.min():.1f}, p50={np.median(y_bench):.1f}, p99={np.percentile(y_bench, 99):.1f}, max={y_bench.max():.1f}, mean={y_bench.mean():.2f}")

print("\n--- 1. CHAMPION_GATE.PY INFERENCE (with ctx_25 and stn_idx passed) ---")
print(f"Predictions q50: min={gate_q50.min():.1f}, p1={np.percentile(gate_q50, 1):.1f}, p50={np.median(gate_q50):.1f}, p99={np.percentile(gate_q50, 99):.1f}, max={gate_q50.max():.1f}")
gate_mae = float(np.abs(y_bench - gate_q50).mean())
print(f"MAE on benchmark: {gate_mae:,.2f} min")

print("\n--- 2. CHAMPION AS TRAINED (model(seq_8) without random context) ---")
print(f"Predictions q50: min={iso_q50.min():.1f}, p1={np.percentile(iso_q50, 1):.1f}, p50={np.median(iso_q50):.1f}, p99={np.percentile(iso_q50, 99):.1f}, max={iso_q50.max():.1f}")
iso_mae = float(np.abs(y_bench - iso_q50).mean())
print(f"MAE on benchmark: {iso_mae:,.2f} min")

print("\n" + "="*72)
print("--- 3. CONTROL EXPERIMENT: OLD VAL WINDOW (2026-08-19..2026-08-22) ---")
print("="*72)

# Build dataset on old test window using SequenceDatasetBuilder (the champion's original builder)
builder = SequenceDatasetBuilder(db_inst, seq_len=8)
X_old, y_old = builder.build_dataset("2026-08-19", "2026-08-22")
print(f"Old validation window sequences: {len(X_old):,}")
if len(X_old) > 0:
    X_old_sub = torch.tensor(X_old[:1000], dtype=torch.float32)
    y_old_sub = y_old[:1000]
    with torch.no_grad():
        q10_old, q50_old, q90_old = champion_model(X_old_sub)
        old_mae = float(np.abs(y_old_sub - q50_old.squeeze(-1).numpy()).mean())
    print(f"Champion MAE on Old Val Window (as trained): {old_mae:.4f} min (documented: ~5.90 min)")
else:
    print("Old validation dates not present in current DB slice.")

# Control experiment on old val window using champion_gate slice
old_ds_v2 = build_v2_dataset(db_inst, vocab, start_date="2026-08-19", end_date="2026-08-22", max_samples=1000)
if len(old_ds_v2) > 0:
    loader_old = DataLoader(old_ds_v2, batch_size=256, shuffle=False)
    old_gate_q50, old_iso_q50, old_y = [], [], []
    with torch.no_grad():
        for b in loader_old:
            seq_8 = b["seq"][:, -8:, :]
            ctx_25 = b["ctx"][:, :25]
            mask_8 = b["seq_mask"][:, -8:]
            stn_idx = b["station_ids"][:, -1] % champion_model.num_stations
            q10_c, q50_c, q90_c = champion_model(seq_8, ctx_25, mask_8, stn_idx)
            q10_i, q50_i, q90_i = champion_model(seq_8)
            old_gate_q50.append(q50_c.squeeze(-1).numpy())
            old_iso_q50.append(q50_i.squeeze(-1).numpy())
            old_y.append(b["target"].numpy())
    old_gate_q50 = np.concatenate(old_gate_q50)
    old_iso_q50 = np.concatenate(old_iso_q50)
    old_y = np.concatenate(old_y)
    print(f"Old val window with champion_gate call (ctx passed): MAE = {np.abs(old_y - old_gate_q50).mean():,.2f} min")
    print(f"Old val window with champion native call (no ctx):   MAE = {np.abs(old_y - old_iso_q50).mean():.4f} min")

print("\n" + "="*72)
print("--- 4. INPUT AUDIT: VECTOR COMPARISON ---")
print("="*72)
b0 = eval_ds[0]
print("b0['ctx'][:25] values passed to champion in champion_gate.py:")
print(b0["ctx"][:25].numpy())
print("\nChampion FiLM context weights norm:", champion_model.film.fc_gamma.weight.norm().item())
print("Champion h0_proj weights norm:", champion_model.h0_proj.weight.norm().item())

con.close()
