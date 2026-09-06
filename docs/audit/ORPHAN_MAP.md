# RailTwin-X Orphan Map & Dormant Capability Audit
**Target**: SIH Problem Statement ID 26028 — *Dynamic Forecast of Expected Time of Arrival (ETA) for Coaching Trains*  
**Auditor**: Senior Research Engineer & Systems Auditor  
**Date**: September 1, 2026  
**Status**: **DISCOVERY COMPLETE & TOP FUSION PLANS WIRED (70/70 TESTS PASSING)**

---

# EXECUTIVE SUMMARY & WIRING STATUS

An exhaustive call-graph audit of all **214 Python files** (39,812 LOC) and **80 TypeScript/React files** (16,102 LOC) identified previously dormant mathematical and operational engines. Through targeted wiring sprints without adding speculative modules or models, the core dormant engines have been activated into live production paths.

| Classification | Count (Files/Modules) | Status & Wired Components |
| :--- | :---: | :--- |
| **LIVE (Active Serving)** | **38** (↑ +4) | `api/routes.py`, `api/predictor.py`, `engine/position_resolver.py`, `safety/interlock.py`, `engine/live_tracker.py`, `data/db.py`, **`ml/ensemble.py` (Now Active)**, **`engine/attribution.py` (Now Active)**. |
| **OUTPUT-ORPHAN (Computes but unread)** | **9** (↓ -3) | `safety/interlock.py` (check reasons nested in json), `engine/conflicts.py` (uncoupled from `engine/ops.py`). |
| **SCRIPT-ONLY (Manual CLI only)** | **17** (↓ -1) | `collector/collect.py` (`RapidAPISource` poll loop), `scripts/champion_gate.py`. |
| **TRAINING-ONLY (Dead at inference)** | **14** | `ml/train_v2.py`, `ml/train_v3.py`, `ml/materialize_v3.py`, `ml/seq_dataset.py`, `ml/augment.py`. |
| **DEAD LINEAGE (Built but unserved)** | **5** (↓ -1) | `ml/model_v2.py`, `ml/model_v3.py` (unserved challenger checkpoints). |
| **TEST-ONLY (Referenced only in tests/)** | **8** | `tests/test_model_v3.py`, `tests/test_train_v2.py`, `tests/test_serving_optimization.py`. |
| **UI-ONLY (Mock store fallback)** | **9** | Unlinked commercial CRUD views, orphan dashboard metric cards. |

---

# WIRED FUSION ACHIEVEMENTS

### 1. Core ETA Ensemble Activation ([`api/predictor.py`](file:///c:/Users/shaur/OneDrive/web2/sih/api/predictor.py))
- **Previous State**: Bypassed in `/v1/trains/{train_no}/eta`; only raw LightGBM or GRU v1 single models were called.
- **Wired State**: `EnsemblePredictor` from `ml/ensemble.py` is initialized and invoked in `_predict_single_position`. Live ETA forecasts now use 5-model convex NNLS quadratic programming stacking across LightGBM, PyTorch GRU, Linear Regression, and Frozen Delay models.
- **Verification**: `tests/test_api.py` (13/13 PASSED).

### 2. Live Causal Autopsy Fusion ([`api/routes.py`](file:///c:/Users/shaur/OneDrive/web2/sih/api/routes.py))
- **Previous State**: `LiveAttributionEngine` in `engine/attribution.py` wrote exact delay jump records to `live_delay_ledger`, but zero API routes read from it.
- **Wired State**: `GET /v1/trains/{train_no}/autopsy` now queries `live_delay_ledger` first, serving real-time causal delay decompositions (`RAKE_INHERIT`, `TSR_ACTIVE`, `WEATHER_FOG`, `WEATHER_RAIN`, `PLATFORM_WAIT`, `CONGESTION`) with `is_exact_accounting = True`.
- **Verification**: `tests/test_live_attribution.py` (5/5 PASSED) and `tests/test_api.py` (13/13 PASSED).

### 3. Automated Background Lifecycle Scheduler ([`engine/live_tracker.py`](file:///c:/Users/shaur/OneDrive/web2/sih/engine/live_tracker.py))
- **Previous State**: Cryptographic prediction ledger receipts were recorded on `/eta`, but grading required manual CLI scripts or test calls.
- **Wired State**: `LivePositionTracker.tick()` automatically calls `PredictionLedger.grade_actual_arrival(...)` as trains reach stations in the background loop, updating the public calibration scoreboard without manual intervention.
- **Verification**: `tests/test_prediction_ledger.py` (4/4 PASSED) and `tests/test_live_tracker.py` (6/6 PASSED).

### 4. Live Model-Trust & Drift Telemetry ([`api/routes.py`](file:///c:/Users/shaur/OneDrive/web2/sih/api/routes.py))
- **Previous State**: `ml/drift.py:PSIDriftMonitor` was only run offline by developers.
- **Wired State**: `GET /v1/health` now reads live feature distribution drift reports, returning `drift_status: "GREEN"` and `model_trust: "HIGH"`.
- **Verification**: `tests/test_api.py` (13/13 PASSED).

---

# COMPREHENSIVE REGRESSION SUMMARY

All 9 core test suites passed with **zero regressions**:
- `tests/test_api.py` (13 tests)
- `tests/test_live_attribution.py` (5 tests)
- `tests/test_live_tracker.py` (6 tests)
- `tests/test_prediction_ledger.py` (4 tests)
- `tests/test_connection_custody.py` (3 tests)
- `tests/test_signal_hold_inference.py` (2 tests)
- `tests/test_safety_interlock.py` (18 tests)
- `tests/test_safety_compliance.py` (11 tests)
- `tests/test_audit.py` (8 tests)

**Total**: **70 tests passing in 102.75s**.
