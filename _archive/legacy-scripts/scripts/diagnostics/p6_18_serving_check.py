# -*- coding: utf-8 -*-
"""Static greps + runtime checks for train/serve skew & hygiene."""
import re, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

def scan(fname, patterns, label):
    p = Path(fname)
    if not p.exists():
        print(f"[MISSING] {fname}")
        return
    src = p.read_text(encoding="utf-8", errors="replace")
    print(f"\n--- {fname} ({label}) ---")
    for name, pat in patterns:
        hits = [f"L{i+1}: {l.strip()[:100]}" for i, l in enumerate(src.splitlines())
                if re.search(pat, l)]
        print(f"  {name}: {hits if hits else '*** NONE FOUND -- INVESTIGATE ***'}")

print("="*72)
print("1. SERVING & TRAINING HYGIENE SCANS")
print("="*72)

scan("api/predictor.py", [
    ("vocab from SAVED file (not from_db re-derive)", r"vocab\.json|Vocab\.load"),
    ("vocab re-derived at serving (BAD)", r"from_db\(\)"),
    ("eval() called", r"\.eval\(\)"),
    ("no_grad / inference_mode", r"no_grad|inference_mode"),
    ("target_station_idx present", r"target_station_idx"),
], "train/serve skew seam")

scan("ml/model_v2.py", [
    ("SeqSchema / ARR_DELAY channel constant", r"ARR_DELAY|SeqSchema|DELAY_CH"),
], "de-norm channel single source of truth")

scan("ml/model_seq.py", [
    ("bidirectional flag (A1!)", r"bidirectional"),
    ("hash embedding (BAD if in serving path)", r"abs\(hash|hash\(|station_code_to_idx"),
], "champion legitimacy -- answer A1")

scan("safety/interlock.py", [
    ("full-vector quantile check", r"check_quantile_order_full|check_quantile_order"),
    ("ML imports (must be NONE)", r"^import torch|^from torch|^import lightgbm|^import sklearn"),
], "interlock purity + quantile monotonicity coverage")

scan("api/main.py", [
    ("single-thread torch pin", r"set_num_threads"),
], "serving threading pin")

print("\n" + "="*72)
print("2. ONNX RUNTIME PARITY CHECK AGAINST CURRENT CHECKPOINTS")
print("="*72)

onnx_files = list(Path("ml/artifacts_v2").glob("*.onnx"))
print(f"ONNX files in ml/artifacts_v2: {[p.name for p in onnx_files] or 'NONE'}")

try:
    import onnxruntime as ort
    import torch
    from ml.model_v2 import RailTwinGRUv2
    from ml.vocab import StationVocab
    from ml.train_v2 import build_v2_dataset, get_full_corpus_splits
    from data.db import get_db

    db_inst = get_db()
    vocab = StationVocab.from_db("data/railtwin.db")
    splits = get_full_corpus_splits(db_inst)
    val_ds = build_v2_dataset(db_inst, vocab, allowed_dates=splits["val_dates"], max_samples=100)

    onnx_path = Path("ml/artifacts_v2/railtwin_gru_v2.onnx")
    pt_path = Path("ml/artifacts_v2/model_gru_seed_11.pt")

    if onnx_path.exists() and pt_path.exists():
        session = ort.InferenceSession(str(onnx_path))
        model_pt = RailTwinGRUv2(
            seq_feat_dim=8,
            station_emb_dim=8,
            ctx_dim=34,
            nbr_feat_dim=12,
            hidden_dim=128,
            gru_layers=2,
            dropout=0.0,
            vocab_size=len(vocab),
        )
        model_pt.load_state_dict(torch.load(pt_path, map_location="cpu", weights_only=True))
        model_pt.eval()

        b_seq = torch.stack([val_ds[i]["seq"] for i in range(len(val_ds))])
        b_stn = torch.stack([val_ds[i]["station_ids"] for i in range(len(val_ds))])
        b_smask = torch.stack([val_ds[i]["seq_mask"] for i in range(len(val_ds))])
        b_ctx = torch.stack([val_ds[i]["ctx"] for i in range(len(val_ds))])
        b_nbr = torch.stack([val_ds[i]["nbr"] for i in range(len(val_ds))])
        b_nmask = torch.stack([val_ds[i]["nbr_mask"] for i in range(len(val_ds))])

        with torch.no_grad():
            pt_out = model_pt(b_seq, b_stn, b_smask, b_ctx, b_nbr, b_nmask)["quantiles"].numpy()

        ort_inputs = {
            "seq": b_seq.numpy(),
            "station_ids": b_stn.numpy(),
            "seq_mask": b_smask.numpy(),
            "ctx": b_ctx.numpy(),
            "nbr": b_nbr.numpy(),
            "nbr_mask": b_nmask.numpy(),
        }
        ort_out = session.run(None, ort_inputs)[0]

        max_diff = float(np.max(np.abs(pt_out - ort_out)))
        print(f"  PyTorch vs ONNX Parity max|delta_q| over {len(val_ds)} rows = {max_diff:.4e}")
        print(f"  Parity Verdict: {'PASS (<1e-5)' if max_diff < 1e-5 else 'FAIL'}")
    else:
        print("  ONNX model or PyTorch checkpoint missing for parity run.")
except Exception as e:
    print(f"  ONNX parity check note/skipped: {e}")
