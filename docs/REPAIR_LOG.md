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

## Phase 3: The Physics Twin
- `engine/sim_clock.py`: Virtual IST clock implemented (`SimulatedClock`), supporting acceleration factor (1x to 60x), manual jump, and auto start hour detection (hour 11:00 with 66 concurrent active trains). Registered `/v1/meta/clock` and `/v1/demo/time`.
- `engine/twin.py`: Pure-math kinematic digital twin engine (`TwinEngine`) with 0.45 m/s² accel, 0.65 m/s² brake, sub-second stepping, TSR capping, signal hold, fog factor, dwell variance, and ARRIVAL/DEPARTURE event emissions. Monotonic distance strictly guaranteed.
- Gate 3.4 Branch A: Graded fields outside hash block. Executed `scripts/regrade_ledger.py` resetting 126 polluted rows. Cryptographic hash chain verified at 5,865 blocks.
- `engine/prediction_ledger.py`: Closed-loop touchdown auto-grading wired to `ConformalPIDController` (`ml/conformal.py`). Updates `conformal_pid_state` table outside transaction to eliminate SQLite lock contention.
- `engine/live_tracker.py`: Integrated `TwinEngine` into `tick()`. Orchestrates active corridor trains, generates 13-column `station_events` rows (`source="simulated"`), invokes touchdown ledger grading, dynamic section occupancy calculation, and async advisory lock against double-starts.
- `api/live_routes.py` & `api/passenger_routes.py`: Wrapped blocking tracker/DB calls in `asyncio.to_thread` for SSE stream generators.
- Tests: Created `tests/test_heartbeat.py` covering 300-min pure-math simulation, idempotent advisory lock, 13-column station_events integration, and SSE smoke frame validation. Ledger integrity verified: (True, 6142, None).
## Phase 4: Passenger Through ML Brain (D04)
- `api/passenger_routes.py`:
  - In `get_passenger_snapshot`:
    - Wired `get_predictor_service().predict_train_eta(target_train_no, selected_stop_code)`.
    - Returns calibrated quantiles `p10_min`, `p50_min`, `p90_min`, and `tier_used`.
    - Implemented 5-second per-train in-memory debounce cache (`_SNAPSHOT_CACHE`) to prevent redundant predictor computation and duplicate ledger writes on rapid polling.
    - Added additive-only keys `band` (`p10_min`, `p50_min`, `p90_min`, `p10_time`, `p90_time`) and `model` (`version`, `horizon_min`).
    - Handled float/int delta times safely in `_add_minutes_to_time`.
    - Preserved 404 response for unknown train numbers.
- `engine/prediction_ledger.py`:
  - Added `record_prediction(...)` alias method for API compatibility.
- Tests: Created `tests/test_passenger_ml.py` testing confidence band presence, cryptographic ledger block increment (+1 block), debounce caching behavior (single predictor call & single ledger receipt across rapid calls), and 404 status on unknown trains.
## Phase 5: Concurrency & Plumbing (D03, D11, D12, RC1)
- **Gate 5.1 (D03 Audit Chain Race)**:
  - `scripts/migrations/016_audit_log_index.sql`: Created unique index `idx_audit_prev` on `audit_log(prev_hash)`. Applied to database via `db.apply_migrations()`.
  - `data/audit.py`:
    - Added `_AUDIT_LOCK = threading.Lock()` around audit logging.
    - Used `BEGIN IMMEDIATE` transaction to guarantee process and connection isolation.
    - Added retry loop (up to 3 attempts with exponential backoff) on `sqlite3.IntegrityError`.
    - Added `append_audit_entry(*args, **kwargs)` supporting flexible calling patterns.
    - Added `verify_audit_log(db)` returning `(is_valid, fork_count, total_blocks)`.
  - Tests: Created `tests/test_audit_concurrency.py` writing 20 concurrent entries across 5 threads; verified `verify_audit_log()` returns `(True, 0, final_count)` and increments count by exactly 20.
- **SSE Async Plumbing**:
  - `api/board_routes.py:274`: Wrapped synchronous `get_live_board` call in `await asyncio.to_thread(...)` inside async generator.
- **Timezone Unification (D11, D12)**:
  - `engine/clocks.py`: Added `ZoneInfo("Asia/Kolkata")` import and centralized `ist_now()` helper returning current IST time honoring active clock mode (`live` vs `simulated`).
  - `api/board_routes.py`, `api/ops_routes.py`, `collector/weather.py`, `engine/ops.py`, `engine/live_tracker.py`: Replaced naive `datetime.now()` calls with clock methods (`clock.now_iso()`, `clock.today_str()`) or monotonic timing (`time.monotonic()`).
- **Route Collision RC1**:
  - Verified removal of shadowing duplicate `/passenger/search` route from `api/routes.py`.

## Phase 6: Hygiene (D10, D13, D14, D15, D16)
- **D10**: Added `numpy>=1.26.0` to `requirements.txt`.
- **D13**: Created `collector/__init__.py` making `collector` a recognized Python package.
- **D14**: Verified all package directories contain `__init__.py`.
- **D15 & D16**: Audited dependencies and clean import tree.

## Phase 7: Final Verification & Documentation
- **Test Suite**: 285 tests passed, 0 failed in 94.15s (`pytest -q tests/`).
- **Prediction Ledger Integrity**: Unbroken SHA-256 hash chain verified at 6,641 blocks (`(True, 6641, None)`).
- **Audit Log Integrity**: 0 forks, unbroken SHA-256 hash chain verified (`(True, 0, 71)`).
- **Forensic Grep Checks**:
  - 0 occurrences of synthetic fallback strings (`estimated_from_schedule`).
  - 0 hardcoded train bypasses in `passenger_routes.py` (`12003`, `12040`).
  - All position payloads carry explicit `source` (`live`, `deadreckoned`, `simulated`, `replay`).
  - All timestamps adhere to `Asia/Kolkata` via centralized clock architecture.
- **Documentation**: Created `docs/HEARTBEAT.md` covering twin physics equations, heartbeat rate, event emissions, touchdown conformal PID integration, and roadmap.
