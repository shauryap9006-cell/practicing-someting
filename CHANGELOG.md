# Changelog

All notable changes to the RailTwin-X project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [4.0.0] - 2026-08-28

### Changed
- **Architectural Separation**: Relocated high-frequency Track-Exact multi-sensor fusion modules (`track_exact/`) to `docs/v4_architecture/` as the long-term production roadmap.
- **Topology Simplification**: Cleaned 2D polyline coordinate geometry from `engine/track_graph.py`.
- **Deterministic Interlock**: Streamlined `safety/interlock.py` to 5 pure deterministic safety rules.
- **Conflict Scanning**: `engine/conflicts.py` now uses freight-aware dynamic headways (5m/8m/14m by train class).
- **API Simplification**: Removed dead middleware; replaced with 5s TTL response cache and token-bucket rate limiter.
- **seed.py**: Unified route generation handles passenger (NDLS–LKO) and DFC freight (WDFC/EDFC) corridors in a single pass.

### Added — Phase 4 (DFC Freight Pivot)
- 5 new train classes: `container`, `coal_rake`, `auto_rake`, `steel_rake`, `empty_freight`.
- `data/seeds/dfc_sections.json`: WDFC (Dadri → JNPT) and EDFC (DDU → Dankuni) track sections.
- `data/seeds/stations.json`: 10 DFC stations (110 total).
- `data/seeds/train_templates.json`: 5 freight train templates (19 total, 30 freight trains generated).
- `engine/conflicts.py`: `_headway_for_class()` dispatch — 14.0m coal, 8.0m standard freight, 5.0m passenger.
- `engine/simulator.py`: `EMPTY_RETURN` cascade event — loaded rake arrival delay propagates to return empty rake after turnaround buffer.
- `data/schema.sql`: `advisory_ack_log` table; `EMPTY_RETURN` added to `sim_ledger` CHECK constraint.

### Added — Phase 5 (API Hardening)
- `api/middleware.py`: `ResponseCacheMiddleware` (5s TTL GET cache for `/v1/advise`) + `TokenBucketRateLimiter` (60 req/min per IP).
- `POST /v1/advise/{adv_id}/ack`: Dispatcher acknowledgement endpoint with audit log persistence.
- `api/schemas.py`: `DispatcherAckRequest` / `DispatcherAckResponse` Pydantic models.
- 3 new ACK contract tests in `tests/test_api.py`.

### Added — Phase 7 (MLOps)
- `ml/drift.py`: PSI (Population Stability Index) feature drift monitor across 7 key features. GREEN/AMBER/RED thresholds. Saves `artifacts/drift_report.json`.
- `scripts/nightly_pipeline.py`: Full pipeline orchestrator (seed → snapshot → lgbm → gru → ensemble → eval → drift).
- `Dockerfile`: Production Docker image (`python:3.11-slim`, libgomp, health check, 2 uvicorn workers).
- `docker-compose.yml`: Single-service stack with persistent volumes for DB, artifacts, and Parquet cache.
- `Makefile`: 20+ targets for developer ops (`seed`, `train`, `eval`, `drift`, `nightly`, `test`, `api`, `docker-*`).

### Added — Phase 8 (Judge Prep)
- `docs/judge_onepager.md`: System summary, architecture diagram, held-out test results table.
- `docs/demo_runbook.md`: 12-minute demo script with exact API calls, talking points, and error recovery.
- `docs/judge_qa.md`: 20+ likely judge questions with sharp technical answers.

### Test Suite
- **78/78 tests green** (up from 75 after Phase 5 ACK contract tests added).

---


## [3.5.0] - 2026-08-27

### Added
- **Dual-Model ML Architecture**:
  - **GRU Champion**: Recurrent neural network for sequential temporal delay propagation across train itineraries.
  - **LightGBM Quantile Trees**: Gradient boosted trees trained on pinball loss ($p_{10}, p_{50}, p_{90}$) for calibrated uncertainty estimation.
- **23-Feature Leakage-Safe Pipeline**:
  - Temporal & Schedule: `sched_hour`, `day_of_week`, `is_weekend`, `month`, `distance_from_origin`, `dwell_time_sched_min`, `km_remaining`, `hops_remaining`.
  - Dynamic Running: `current_delay`, `rolling_delay_3_stops`, `delay_accel`, `speed_ratio`.
  - Static Train & Route: `train_priority`, `train_class_cat`, `is_junction_stop`, `corridor_speed_limit`.
  - Weather: `temp`, `humidity`, `precip_mm`, `fog_flag`.
  - Network Graph: `trains_ahead_30k`, `trains_behind_30k`, `opposing_trains_30k`, `min_predicted_headway_next_station`, `sum_delay_trains_ahead_30k`, `section_occupancy_pct`.
- **Deterministic Conflict Scanner**: Station headway buffers and single-line opposing train meets with actionable advisories (`hold_at_loop`, `proceed`, `stop_train_advisory`, `controller_review`).
- **REST API Suite**: 10 high-performance endpoints covering live ETA, journey timelines, root-cause autopsy, corridor state, platform Gantt allocation, 1-click self-healing reoptimization, cascade simulation, and crew duty breach monitoring.
- **Synthetic Data Generator & Historical Curated Parquet**: High-fidelity Indian Railways telemetry corpus across NDLS-CNB-DDU corridor.
