import sys
from pathlib import Path
import torch

print("=== CHECKING CHAMPION MODEL IN ml/artifacts/ ===")
for p in Path("ml/artifacts").glob("*"):
    print(f"  {p.name} ({p.stat().st_size:,} bytes)")

champ_pt = Path("ml/artifacts/model_gru_champion.pt")
if champ_pt.exists():
    print(f"\nInspecting {champ_pt}:")
    sd = torch.load(champ_pt, map_location="cpu", weights_only=False)
    if isinstance(sd, dict):
        print("Keys in state_dict:")
        for k, v in sd.items():
            shape_str = str(v.shape) if hasattr(v, "shape") else type(v)
            print(f"  {k}: {shape_str}")
        
        # Check if bidirectional
        # Bidirectional GRU in PyTorch has keys with `_reverse` (e.g. weight_ih_l0_reverse)
        bidi_keys = [k for k in sd.keys() if "reverse" in k]
        print(f"\nBidirectional keys found: {bidi_keys}")
        if bidi_keys:
            print(">> CHAMPION IS BIDIRECTIONAL GRU <<")
        else:
            print(">> CHAMPION IS UNIDIRECTIONAL (CAUSAL) GRU <<")

print("\n=== CHECKING CHAMPION SOURCE CODE (ml/model_seq.py or similar) ===")
for py_file in Path("ml").glob("*.py"):
    txt = py_file.read_text(encoding="utf-8", errors="ignore")
    if "NonCrossingGRUQuantileModel" in txt or "champion" in txt.lower():
        print(f"Found champion references in {py_file.name}")
