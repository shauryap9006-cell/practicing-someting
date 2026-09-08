# ml/experiments

This directory holds non-canonical, non-served model artifacts kept for
reproducibility and audit history only. **Nothing here is loaded by the
serving process** (`api/predictor.py` / `ml/ensemble.py` only read from
`ml/artifacts/`, pointed to by `settings.ARTIFACTS_DIR`).

- `v2_gated/` - RailTwinGRUv2 deep ensemble challenger. Status: `gated` in
  `ml/artifacts/registry.json` (never promoted to champion). Moved from the
  former `ml/artifacts_v2/`.
- `v3_gated/` - RailTwinGRUv3 RegimeMoE feature manifest. Never trained to a
  servable artifact. Moved from the former `ml/artifacts_v3/`.
- `candidates/` - `candidate0` (restored baseline) through `candidate3`
  outputs from `scripts/candidate_shootout.py`. `candidate0` won the
  shootout and its outputs are the live artifacts under `ml/artifacts/`
  (`model_direct_q*.txt`, `model_delta_q*.txt`); candidates 1-3 are kept
  here only as the losing comparison runs. Moved from `ml/artifacts/candidate{1,2,3}/`.

If you are looking for the models actually served in production, see
`ml/artifacts/` and `ml/artifacts/registry.json`.
