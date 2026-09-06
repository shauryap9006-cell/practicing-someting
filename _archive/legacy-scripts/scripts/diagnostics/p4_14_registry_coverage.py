# -*- coding: utf-8 -*-
"""Registry coverage audit: Which of the 9 new T2 features are dead-on-arrival?"""
import json, sqlite3, gzip, shutil, sys
from pathlib import Path
from collections import Counter
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import numpy as np
import pandas as pd

db_path = "data/railtwin.db"
con = sqlite3.connect(db_path); con.row_factory = sqlite3.Row
lo, hi = con.execute("SELECT MIN(run_date), MAX(run_date) FROM station_events").fetchone()
print(f"Corpus event span: {lo} .. {hi}\n")

def check_dates(dates, label, unit):
    if not dates:
        print(f"  {label:32s} EMPTY REGISTRY")
        return 0, len(dates)
    dmin, dmax = min(dates), max(dates)
    inside = sum(1 for d in dates if lo <= d <= hi)
    status = "*** OUTSIDE CORPUS => FEATURE DEAD ***" if inside == 0 else f"{inside}/{len(dates)} inside"
    print(f"  {label:32s} {len(dates):>4} {unit:<7} | span: {dmin}..{dmax} | {status}")
    return inside, len(dates)

print("="*72)
print("1. SEED REGISTRY DATE & KEY COVERAGE")
print("="*72)

# Check festivals.json or holidays.json
p_fest = Path("data/seeds/festivals.json")
if p_fest.exists():
    data = json.loads(p_fest.read_text(encoding="utf-8"))
    items = data if isinstance(data, list) else data.get("festivals", [])
    dates = [str(it.get("date") or it.get("start_date") or "")[:10] for it in items if it.get("date") or it.get("start_date")]
    check_dates([d for d in dates if d], "data/seeds/festivals.json", "entries")
else:
    p_hol = Path("data/holidays.json")
    if p_hol.exists():
        data = json.loads(p_hol.read_text(encoding="utf-8"))
        dates = [str(k)[:10] for k in data.keys()] if isinstance(data, dict) else []
        check_dates([d for d in dates if d], "data/holidays.json", "dates")
    else:
        print("  festivals.json: MISSING")

# Check speed_restrictions.json
p_tsr = Path("data/seeds/speed_restrictions.json")
if p_tsr.exists():
    data = json.loads(p_tsr.read_text(encoding="utf-8"))
    items = data if isinstance(data, list) else data.get("restrictions", data.get("tsr", []))
    dates = [str(it.get("start_date") or it.get("from_date") or it.get("effective_from") or "")[:10] for it in items]
    check_dates([d for d in dates if d], "data/seeds/speed_restrictions.json", "entries")
else:
    tsr_count = con.execute("SELECT COUNT(*) FROM speed_restrictions").fetchone()[0]
    print(f"  speed_restrictions table in DB: {tsr_count} rows")

# Check rake_links.json
p_rake = Path("data/seeds/rake_links.json")
if p_rake.exists():
    data = json.loads(p_rake.read_text(encoding="utf-8"))
    links = data if isinstance(data, list) else data.get("links", [])
    trains_in_links = set()
    for it in links:
        for k in ("incoming_train", "outgoing_train", "train_no", "incoming", "outgoing"):
            if it.get(k): trains_in_links.add(str(it[k]))
    n_trains = con.execute("SELECT COUNT(DISTINCT train_no) FROM station_events").fetchone()[0]
    cov_pct = 100 * len(trains_in_links) / max(n_trains, 1)
    print(f"\n  {'data/seeds/rake_links.json':32s} {len(links):>4} links   | {len(trains_in_links)} distinct trains / {n_trains} corpus trains | coverage = {cov_pct:.1f}%")
else:
    rake_cnt = con.execute("SELECT COUNT(*) FROM rake_links").fetchone()[0]
    print(f"  rake_links table in DB: {rake_cnt} rows")

print("\n" + "="*72)
print("2. FEATURE FIRING RATES IN V2 SNAPSHOT PIPELINE")
print("="*72)
from data.db import get_db
from ml.vocab import StationVocab
from ml.train_v2 import build_v2_dataset
from ml.features import FEATURE_NAMES_V2

db_inst = get_db()
vocab = StationVocab.from_db(db_path)
ds_sample = build_v2_dataset(db_inst, vocab, max_samples=5000)
ctx_arr = np.array([ds_sample[i]["ctx"].numpy() for i in range(len(ds_sample))])

print(f"{'Feature':<36} {'Non-Default/Firing %':<22} {'Distinct Values':<16} {'Verdict'}")
print("-" * 88)
for i, f in enumerate(FEATURE_NAMES_V2):
    vals = ctx_arr[:, i]
    nonzero = np.count_nonzero(vals != 0.0)
    n_unique = len(np.unique(vals))
    pct_fire = 100.0 * nonzero / len(vals)
    
    if pct_fire == 0.0:
        verdict = "DEAD-ON-ARRIVAL (0% fired)"
    elif pct_fire < 5.0 or n_unique <= 2:
        verdict = "NEAR-DEAD (<5% fire or <=2 values)"
    else:
        verdict = "ALIVE"
    print(f"{f:<36} {pct_fire:>18.2f}% {n_unique:>15}    {verdict}")

con.close()
