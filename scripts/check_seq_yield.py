"""Check sequence yield per date range to find where sequences drop to zero."""
import sys, datetime
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from data.db import get_db
from ml.vocab import StationVocab
from ml.train_v2 import build_v2_dataset

db = get_db()
vocab = StationVocab.from_db()

# Check sequence counts for various windows
windows = [
    ("2026-03-20", "2026-06-08", "val-candidate-1"),
    ("2026-06-01", "2026-07-31", "val-candidate-2"),
    ("2026-07-01", "2026-08-14", "val-candidate-3"),
    ("2026-08-01", "2026-08-18", "train-recent-3weeks"),
    ("2026-08-01", "2026-08-22", "old-train-window"),
    ("2026-08-19", "2026-08-25", "val-window-alt"),
    ("2025-02-08", "2026-06-30", "train-full"),
    ("2025-02-08", "2026-07-31", "train-extended"),
]

for start, end, label in windows:
    ds = build_v2_dataset(db, vocab, start, end)
    print(f"  [{label}] {start} -> {end}: {len(ds):,} sequences")
