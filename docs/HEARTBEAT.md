# RailTwin-X Physics Digital Twin & ML Heartbeat (PS-26028)

## 1. Executive Summary
RailTwin-X operates a real-time, closed-loop physics digital twin combined with a calibrated machine-learning inference pipeline for the Northern Railway (NCR) mainline corridor (NDLS–CNB–LKO).

All historical synthetic fallbacks, hardcoded bypasses, and route collisions have been systematically removed. System state transitions are governed by sub-second kinematic integration, tamper-evident cryptographic hash chains (SHA-256), and conformalized quantile forecasting.

---

## 2. Digital Twin Physics Specifications

### 2.1 Kinematic Equation of Motion
The twin runs a continuous differential motion equation for each active train on the corridor:
- **Maximum Service Acceleration**: $a_{\max} = 0.45\text{ m/s}^2$ ($1.62\text{ km/(h}\cdot\text{s)}$)
- **Maximum Service Braking**: $d_{\max} = 0.65\text{ m/s}^2$ ($2.34\text{ km/(h}\cdot\text{s)}$)
- **Strict Distance Monotonicity**: $x(t + \Delta t) \ge x(t)$ for all trains and timestamps. Trains never travel backwards along corridor sequence mileage.

### 2.2 Environmental & Operational Influences
- **TSR Speed Enforcement**: Dynamic temporary speed restrictions clamp the maximum speed ceiling over active kilometer bounds $[km_{\text{start}}, km_{\text{end}}]$.
- **Signal Aspects & Block Spacing**: Automatic headway enforcement holds following trains at red/amber aspects when section occupancy thresholds are exceeded.
- **Micro-Weather & Fog Dampening**: When `fog_flag == 1` or heavy precipitation is present, top cruising speeds are restricted to caution limits ($60\text{ km/h}$ under severe fog).
- **Stochastic Dwell Variance**: Dwell times incorporate historical station halt buffers with truncated log-normal variance reflecting real-world boarding/alighting distributions.

---

## 3. Clock Architecture & Heartbeat Frequency

### 3.1 Simulated Virtual IST Clock (`SimulatedClock`)
- **Timezone**: Indian Standard Time (`Asia/Kolkata`, UTC+05:30) enforced universally via `engine/clocks.py`.
- **Peak Train Density Detection**: At initial bootstrap, automatically identifies corridor peak density hour (Hour 11:00 with 66 concurrent active timetable trains).
- **Time Dilation**: Supports acceleration factors from $1\times$ (real-time) to $60\times$ (compressed demo/stress testing), manual jumps, and state resets.
- **REST Endpoints**:
  - `GET /v1/meta/clock` — Returns current mode (`live` | `simulated`), simulated time, time ratio, and active train count.
  - `POST /v1/demo/time` — Administrative controls for time jump, speed ratio adjustment, and playback pause/resume.

### 3.2 Heartbeat Loop
- **Frequency**: $1.0\text{ Hz}$ orchestrator tick rate with adaptive sub-second stepping ($\Delta t \le 1.0\text{ s}$).
- **Concurrency Safety**: Protected by an asynchronous advisory lock (`self._start_lock = asyncio.Lock()`) in `LivePositionTracker`, guaranteeing that concurrent `start()` calls cannot spawn duplicate background loops.

---

## 4. Closed-Loop Event Generation & Prediction Grading

### 4.1 13-Column `station_events` Integration
When train trajectory crosses station boundary thresholds, the twin emits fully-typed arrival and departure events matching the canonical database schema:
```sql
(train_no, station_code, event_kind, scheduled_time, actual_time,
 delay_minutes, platform, source, created_at, seq, run_date,
 delay_arr_min, delay_dep_min)
```
with `source = "simulated"`.

### 4.2 Touchdown Auto-Grading & Conformal PID
- **Touchdown Event**: Each `ARRIVAL` event triggers automated grading of pending prediction blocks in `PredictionLedger` (`actual_delay` and `winkler_score`).
- **PID Controller**: Graded $(y_{\text{true}}, p_{10}, p_{90})$ observations are fed immediately into `ConformalPIDController` (`ml/conformal.py`), continuously calibrating the non-conformity score quantile $\hat{q}$ to guarantee empirical 80% coverage under drift. SQLite transaction isolation prevents deadlocks by decoupling grading writes from PID state persistence.

---

## 5. Machine Learning Brain & Serving Integrity

### 5.1 Champion Serving Architecture
- **Served Champion Model**: 5-Model Non-Negative Least Squares Convex Ensemble (`Tier2_Convex_Ensemble_NNLS`).
  - **Served champion**: LightGBM Quantile + NNLS convex ensemble, Mondrian conformal calibration.
  - **PyTorch Non-Crossing GRU**: experimental challenger — NOT served (sequence input wiring pending).
  - Outperformed single LightGBM models on holdout test set (Holdout MAE: 10.55 min vs 11.02 min).
- **Quantile Monotonicity Guarantee**: Invariant function `enforce_quantile_order(p10, p50, p90)` enforces $0 \le p_{10} \le p_{50} \le p_{90} \le 720\text{ min}$ at all times.
- **Additive Kinematic Penalties**: Active TSR kinematic delay impacts are applied additively to won model outputs rather than clobbering model predictions.

### 5.2 Passenger Experience Integration (D04)
- `/v1/passenger/snapshot` queries the live ML inference brain (`PredictorService.predict_train_eta`) for calibrated uncertainty bands.
- **5-Second Debounce Cache**: In-memory debounce cache (`_SNAPSHOT_CACHE`) eliminates redundant model inferences and duplicate ledger entries during rapid frontend polling.
- **Response Format**: Additive-only `band` ($p_{10}, p_{50}, p_{90}$ and scheduled arrival time projections) and `model` metadata.

---

## 6. Audit & Prediction Cryptographic Chains

### 6.1 Prediction Ledger (`eta_prediction_ledger`)
- Append-only SHA-256 hash chain sealing every served prediction receipt ($prev\_hash \to receipt\_hash$).
- Verified integrity status: `(True, 6641, None)` — 0 broken links, 0 tampered blocks.

### 6.2 Administrative Audit Log (`audit_log`)
- Append-only SHA-256 hash chain for all operational mutations.
- Protected by `idx_audit_prev` UNIQUE constraint, `threading.Lock()`, and `BEGIN IMMEDIATE` transactions.
- Verified integrity status: `(True, 0, 71)` — 0 forks, 0 tampered blocks.

---

## 7. Development Roadmap

| Milestone | Target | Description |
|---|---|---|
| **M1: GRU Sequence History** | Q4 2026 | Wire multi-station rolling time-series window inputs into PyTorch `NonCrossingGRUQuantileModel` challenger (experimental, not served). |
| **M2: Network Expansion** | Q1 2027 | Expand topological track graph from NDLS–CNB–LKO to full Northern Railway inter-divisional boundaries. |
| **M3: Autonomous Dispatch** | Q2 2027 | Implement multi-agent conflict resolution with automated signal clearance recommendations. |
