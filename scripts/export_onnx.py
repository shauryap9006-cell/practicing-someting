"""ONNX Export and Numerical Parity Verification for RailTwinGRUv2 (Task T10)."""
from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np
import torch
import torch.nn as nn

from ml.model_v2 import RailTwinGRUv2, ALPHAS_V2
from ml.vocab import StationVocab


class RailTwinGRUv2ExportWrapper(nn.Module):
    """Wrapper that outputs only the quantiles tensor for ONNX graph compatibility."""

    def __init__(self, model: RailTwinGRUv2):
        super().__init__()
        self.model = model

    def forward(
        self,
        seq: torch.Tensor,
        station_ids: torch.Tensor,
        seq_mask: torch.Tensor,
        ctx: torch.Tensor,
        nbr: torch.Tensor,
        nbr_mask: torch.Tensor,
    ) -> torch.Tensor:
        out = self.model(
            seq=seq,
            station_ids=station_ids,
            seq_mask=seq_mask,
            ctx=ctx,
            nbr=nbr,
            nbr_mask=nbr_mask,
        )
        return out["quantiles"]


def export_model_to_onnx(
    checkpoint_path: Path,
    output_onnx_path: Path,
    vocab_size: int = 2048,
) -> None:
    """Exports RailTwinGRUv2 PyTorch model to ONNX with dynamic batch axes."""
    output_onnx_path.parent.mkdir(parents=True, exist_ok=True)

    model = RailTwinGRUv2(
        seq_feat_dim=8,
        station_emb_dim=8,
        ctx_dim=34,
        nbr_feat_dim=12,
        hidden_dim=128,
        gru_layers=2,
        dropout=0.0,  # 0.0 for inference
        vocab_size=vocab_size,
    )

    if checkpoint_path.exists():
        state_dict = torch.load(checkpoint_path, map_location="cpu", weights_only=True)
        model.load_state_dict(state_dict)
        print(f"[INFO] Loaded weights from {checkpoint_path}")

    model.eval()
    wrapper = RailTwinGRUv2ExportWrapper(model)
    wrapper.eval()

    B, T, K = 2, 8, 8
    dummy_seq = torch.randn(B, T, 8, dtype=torch.float32)
    dummy_station_ids = torch.randint(0, vocab_size, (B, T), dtype=torch.long)
    dummy_seq_mask = torch.ones((B, T), dtype=torch.bool)
    dummy_ctx = torch.randn(B, 34, dtype=torch.float32)
    dummy_nbr = torch.randn(B, K, 12, dtype=torch.float32)
    dummy_nbr_mask = torch.ones((B, K), dtype=torch.bool)

    with torch.no_grad():
        pt_out = wrapper(dummy_seq, dummy_station_ids, dummy_seq_mask, dummy_ctx, dummy_nbr, dummy_nbr_mask)

    print(f"[INFO] Exporting TorchScript model to {output_onnx_path.with_suffix('.pt')}...")
    try:
        traced_model = torch.jit.trace(
            wrapper,
            (dummy_seq, dummy_station_ids, dummy_seq_mask, dummy_ctx, dummy_nbr, dummy_nbr_mask),
        )
        torch.jit.save(traced_model, str(output_onnx_path.with_suffix('.pt')))
        print(f"[SUCCESS] Exported TorchScript model -> {output_onnx_path.with_suffix('.pt')}")
    except Exception as e:
        print(f"[WARN] TorchScript export failed: {e}")

    print(f"[INFO] Exporting ONNX model to {output_onnx_path}...")
    try:
        torch.onnx.export(
            wrapper,
            (dummy_seq, dummy_station_ids, dummy_seq_mask, dummy_ctx, dummy_nbr, dummy_nbr_mask),
            str(output_onnx_path),
            input_names=["seq", "station_ids", "seq_mask", "ctx", "nbr", "nbr_mask"],
            output_names=["quantiles"],
            dynamic_axes={
                "seq": {0: "batch_size"},
                "station_ids": {0: "batch_size"},
                "seq_mask": {0: "batch_size"},
                "ctx": {0: "batch_size"},
                "nbr": {0: "batch_size"},
                "nbr_mask": {0: "batch_size"},
                "quantiles": {0: "batch_size"},
            },
            opset_version=17,
            dynamo=False,
        )
        print(f"[SUCCESS] Exported ONNX model successfully.")
    except Exception as e:
        print(f"[INFO] Torch.onnx.export encountered {e.__class__.__name__}: {e}. TorchScript artifact available.")

    # Numerical Parity Check
    try:
        import onnxruntime as ort
        session = ort.InferenceSession(str(output_onnx_path))
        ort_inputs = {
            "seq": dummy_seq.numpy(),
            "station_ids": dummy_station_ids.numpy(),
            "seq_mask": dummy_seq_mask.numpy(),
            "ctx": dummy_ctx.numpy(),
            "nbr": dummy_nbr.numpy(),
            "nbr_mask": dummy_nbr_mask.numpy(),
        }
        ort_out = session.run(None, ort_inputs)[0]
        max_diff = np.max(np.abs(pt_out.numpy() - ort_out))
        print(f"[VERIFY] PyTorch vs ONNX Max Absolute Difference: {max_diff:.6e}")
        assert max_diff < 1e-4, f"Parity violation: {max_diff} >= 1e-4"
        print(f"[VERIFY] Numerical parity verified (PASS < 1e-4)!")
    except ImportError:
        print("[WARN] onnxruntime not installed, skipping ONNX runtime parity test.")


if __name__ == "__main__":
    ckpt = Path("ml/artifacts_v2/model_gru_seed_11.pt")
    out_onnx = Path("ml/artifacts_v2/railtwin_gru_v2.onnx")
    export_model_to_onnx(ckpt, out_onnx)
