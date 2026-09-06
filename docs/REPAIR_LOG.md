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
