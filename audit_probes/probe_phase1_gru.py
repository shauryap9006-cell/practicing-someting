import torch
from pathlib import Path
from ml.model_seq import NonCrossingGRUQuantileModel

gru_path = Path("ml/artifacts/model_gru_challenger.pt")
print(f"Loading {gru_path}...")
state_dict = torch.load(gru_path, map_location="cpu", weights_only=True)
print(f"State dict keys ({len(state_dict)}):")
for k, v in state_dict.items():
    print(f"  {k}: shape {v.shape}, dtype {v.dtype}")

# Inspect model architecture
model = NonCrossingGRUQuantileModel(input_dim=8, hidden_dim=128, num_layers=2, dropout=0.2)
model.load_state_dict(state_dict)
model.eval()

# Check forward pass with dummy input [1, 8, 8]
x = torch.randn(1, 8, 8)
with torch.no_grad():
    q10, q50, q90 = model(x)
print(f"\nForward pass output shapes: q10={q10.shape}, q50={q50.shape}, q90={q90.shape}")
print(f"Values: q10={q10.item():.4f}, q50={q50.item():.4f}, q90={q90.item():.4f}")
print(f"Finite? q10={torch.isfinite(q10).item()}, q50={torch.isfinite(q50).item()}, q90={torch.isfinite(q90).item()}")
print(f"Monotonic? (q10 <= q50 <= q90): {q10.item() <= q50.item() <= q90.item()}")
