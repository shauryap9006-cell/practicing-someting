# RailTwin-X Backend Repair Log

## Phase 0: Baseline & Safety Snapshot
- **Branch**: `backend-twin`
- **Pre-twin Commit**: `e256c73 pre-twin snapshot`
- **Baseline Pytest**: 271 passed, 118 warnings
- **LEDGER_BASELINE**: 5,134 blocks
- **Chain Integrity**: (True, 5134, None)
- **Scoreboard Baseline**:
```json
{
  "status": "OK",
  "scoreboard": {
    "total_served_predictions": 5134,
    "verified_arrivals_count": 613,
    "empirical_80pct_coverage": 30.5,
    "target_coverage_pct": 80.0,
    "mean_absolute_error_min": 20.18,
    "mean_winkler_score": 144.64,
    "chain_integrity_verified": true,
    "total_blocks_verified": 5134,
    "chain_tip_hash": "7f8233b41752836a87d8d3e8cf1e1acc3cac4641c4bfb71c2f7c37a9b8944a05",
    "as_of": "2026-09-06T22:18:30.951336+05:30"
  }
}
```

## Decision Gates Record
- **Gate 3.4 (Ledger Grading Repair)**: Branch A selected. Graded fields (`actual_delay`, `actual_timestamp`, `error_min`, `in_band`, `winkler_score`) are OUTSIDE the SHA-256 block hash. `scripts/regrade_ledger.py` resets 544 polluted rows to NULL; append-only block hash chain remains 100% verified.
- **Gate 5.1 (D03 Audit Chain Race)**: Clean path selected. Forensic audit confirmed 51 rows and 0 forks in `audit_log`. Migration `016_audit_log_index.sql` creates `idx_audit_prev` with critical section `threading.Lock()` + `BEGIN IMMEDIATE`.
- **Gate 2.1 (Ensemble vs LightGBM Quality Gate)**: Ensemble MAE (10.55) <= Direct LightGBM MAE (11.02) on holdout test set (`shootout_results.json`). Intent restored: 5-Model Convex NNLS Ensemble preserved as served champion.
- **Gate 2.4 (D08 CV Fold Repair)**: Derive folds from contiguous event window (2026-08-06 to 2026-09-02, 1,200 events/day) rather than empty 230-day span. Every fold achieves samples > 0 with computed metrics.

## Phase 1: Honesty Fabrications Removed
- Commit: `e539ab9`
- `api/demo_routes.py`: Deleted synthetic fallback `if count == 0: base_count = max(...)` and synthetic `tot_delay`. Deleted `max(len(live_trains), 14)` floor. Sanitized corrupted corridor strings and unicode minus characters to ASCII `"NCR Mainline (NDLS-LKO 440km)"`.
- `engine/live_tracker.py`: Implemented `LivePositionTracker.snapshot()` and `positions` property.
- `api/passenger_routes.py`: Deleted hardcoded `target_train_no == "12003"` and `is_completed = (12004)` fabrication blocks. Deleted `(int(target_train_no) % 4) + 1` platform assignment fabrication, replaced with `platform_assignments` lookup (null if unassigned). Supported both `q` and `query` parameters on `/v1/passenger/search`.
- `api/routes.py`: Removed duplicate shadowed `/passenger/search` route.
- `api/main.py`: Reconfigured stdout encoding to UTF-8 at startup.
- Documentation: Aligned corridor specifications in `README.md`, `DATA_PROVENANCE.md`, `DEMO_SCRIPT.md` with true 8-station NDLS-CNB-LKO route.

## Phase 2: ML Integrity & Dispatch Restructure
- `api/predictor.py`:
  - D01: Restructured dispatch so `self._ensemble.predict` is primary (`tier_used = "Tier2_Convex_Ensemble_NNLS"`), LightGBM direct/delta is reached only as fallback in exception handler.
  - D02: Gated GRU challenger with `self._gru_sequence_ready = False`, emitted boot notice, ensured `get_model_info()` reports active served ensemble without claiming unserved GRU.
  - Moved dynamic TSR kinematic penalty to the end as an additive post-adjustment to won model output.
- `scripts/migrations/015_route_cum_km.sql`: Created `route_cum_km` table and populated 1,205 entries from `route_stations` with distance monotonicity verified.
- `ml/features_v3.py`: Separated try/except blocks around `route_cum_km` and `route_stations` fallback with explicit warning logging.
- `ml/evaluate.py`: Derived CV window from data-dense window (`2026-08-06` to `2026-09-02`). Added determinism seeds (`random_state=42`, `deterministic=True`). Regenerated `ml/artifacts/metrics.json` with all 6 folds containing valid samples (>0) and computed MAEs (mean CV MAE: 10.63 min).
- `ml/train.py`: Added global determinism seeds and LightGBM parameters (`random_state=42`, `deterministic=True`).
- Tests: Added `tests/test_phase2_ml_integrity.py` asserting D01 ensemble serving, additive TSR penalty, D02 GRU gating, and D09 quantile monotonicity. Suite passed: 275/275 tests green. Cryptographic ledger verified: (True, 5622, None).

