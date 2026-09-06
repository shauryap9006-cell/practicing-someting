# RailTwin-X: Operational Intelligence & Autonomous Digital Twin for Indian Railways

## 1. System Overview & Core Pipelines (01 – 07)

RailTwin-X is an enterprise-grade cyber-physical operational twin and neural decision support platform engineered for Indian Railways' High-Density Network (HDN) corridor (New Delhi to Pt. Deen Dayal Upadhyaya, 785 KM).

### The 7 Core Pipelines
1. **Pipeline 01: Live Ingestion & Snapshot Telemetry** — 3-tier adapter failover (RapidAPI $\to$ Web Scraping $\to$ MockReplaySource), 4-rule QualityGate validation, UTC-to-IST normalization, and point-in-time snapshot archiving.
2. **Pipeline 02: Nightly MLOps & Champion Promotion** — Paired Wilcoxon signed-rank non-inferiority champion gate, Mondrian Conformal Quantile Calibration, PSI drift detection, and `metrics.json` F14 proof materialization.
3. **Pipeline 03: Real-Time Inference & Dynamic ETA** — Sub-2ms PyTorch GRU quantile inference ($p_{10}, p_{50}, p_{90}$), 5-rule safety interlock clamp, and marginalization over top-3 Bayesian spatial positions.
4. **Pipeline 04: Neural Brain & Multi-Channel Advisories** — Headway conflict perception, kinematic priority preemption formulation, WhatsApp alert dispatch, and cryptographic HMAC webhook ACK verification.
5. **Pipeline 05: Platform Gantt & Sub-50ms Self-Healing Re-Optimizer** — 24-hour platform occupancy timeline, pairwise interval collision detection, sub-50ms greedy local-search swap solver, and rollback management.
6. **Pipeline 06: Mechanistic Cascade What-If & Delay Autopsy** — Discrete-event corridor SimPy simulation, single-line priority preemption, active TSR delay impact, and 100% mathematically balanced causal delay ledger.
7. **Pipeline 07: Live Position Tracking, Context & Real Delay Attribution** — 30s master tracker loop, polyline dead-reckoning with exponential confidence decay ($\tau = 1800\text{s}$), 5-layer micro-operational context, 6-rule delay attribution, and 5s SSE real-time streaming.

---

## 2. Replay Demo Engine (`DEMO_MODE=1`)

RailTwin-X features a deterministic, network-free 3-minute stage replay demo engine:
- **Scenario Definition:** `data/seeds/demo_scenario.json`
- **Replay Driver:** `scripts/demo_replay.py`
  - CLI usage: `python scripts/demo_replay.py --fast` (instant test) or `python scripts/demo_replay.py --realtime` (3-minute stage pace).
  - Uses `TimeProvider` in REPLAY mode with virtual clock starting at `DEMO_SCENARIO_DATE` (`2026-01-15 08:00:00 IST`).
  - Disables real external network calls and executes real pipelines deterministically.
- **Determinism Test:** `tests/test_demo_replay.py` asserts byte-identical event sequences and headline metrics across repeated runs.

---

## 3. Database Schema & Tables

All persistent operational state is managed in SQLite with WAL journal mode and busy timeouts:
- `trains`, `stations`, `sections`, `route_stations`, `timetable_entries` — Static corridor infrastructure and schedule metadata.
- `station_events` — Point-in-time actual and scheduled arrival/departure events with collected timestamps.
- `weather`, `weather_hourly` — Micro-environmental atmospheric conditions (temperature, humidity, precipitation, visibility, fog).
- `speed_restrictions` — Active Temporary Speed Restrictions (TSRs) with speed limits, length, and delay penalties.
- `rake_links` — Same-rake pairing definitions for primary turnaround doom tracking and freight empty returns.
- `live_positions` — Real-time kinematic train state (lat/lng, speed, section, distance, confidence, staleness, ETA quantiles).
- `live_delay_ledger` — Append-only exact accounting causal delay attribution ledger ($\sum \text{causes} \equiv \Delta\text{delay}$).
- `sim_ledger` — Mechanistic cascade simulation causal records.
- `advisory_ack_log` — Section controller cryptographic accept/reject decisions.
- `brain_advisory_audit` — Neural brain perception log with input features, suggested actions, and safety interlock passes.

---

## 4. API Endpoints

- `GET /v1/meta/config` — Public frontend configuration tokens, color thresholds, and interval budgets.
- `GET /v1/health` — System liveness, DB event count, ML model status, live tracker tick age, and active SSE client count.
- `GET /v1/live/positions` — Snapshot of all active train kinematic positions on the corridor.
- `GET /v1/live/stream` — Real-time Server-Sent Events (SSE) stream broadcasting live train positions every 5s.
- `GET /v1/trains/{train_no}/live` — High-precision live position, confidence halo, and current section for a specific train.
- `GET /v1/trains/{train_no}/why-late` — Exact causal delay attribution breakdown and micro-operational context.
- `GET /v1/trains/{train_no}/eta` — Calibrated $p_{10}, p_{50}, p_{90}$ arrival and departure predictions.
- `POST /v1/stations/{code}/reoptimize` — 1-Click platform conflict resolution executing in $<50\text{ms}$.
- `POST /v1/stations/{code}/rollback` — Instant rollback to pre-optimization platform plan.
- `POST /v1/simulate/what-if` — SimPy discrete-event cascade perturbation simulation.

---

## 5. Verification & Test Suite

The comprehensive pytest test suite contains **243 automated tests** covering all pipelines, mathematical invariants, determinism, and safety interlocks:
```bash
pytest -v
```
To run the determinism suite:
```bash
pytest tests/test_demo_replay.py -v
```
