# Phase 0 — Forensic Pre-Flight Audit Report (v4.3)
**Generated:** 2026-08-29
**System:** RailTwin-X Neural Engine Overhaul v4.3 (PS 26028)
**Corridor:** NDLS -> DDU

---

## Executive Summary of Forensics (F1 - F6)

| Forensic ID | Check Area | Finding | Severity / Risk | Immediate Action |
|---|---|---|---|---|
| **F1** | Station Hash Determinism & Collision | Python salted hash() differs per process (PYTHONHASHSEED). Polynomial hash has **328 colliding buckets (585 pairs)** across 1,223 stations in 1,200 buckets. Serving path omitted 	arget_station_idx argument. | **P0 - SEVERE** | **T1 Mandatory**: Implement StationVocab with persistent vocab, >=2048 size, guaranteed 0 collisions. |
| **F2** | Feature Wiring Audit | TrainFeatureVector (25-dim) is missing critical causal signals: Upstream Rake Doom signals, TSR slowdowns, Festival multipliers, Bayesian Position entropy/mode, Recency latency. | **HIGH** | **T2**: Upgrade to FEATURE_VERSION = 2 with 34-dim schema wiring all disconnected subsystems. |
| **F3** | GRU Temporal Directionality | Current NonCrossingGRUQuantileModel uses unidirectional PyTorch GRU (idirectional=False). | **CONFIRMED / SAFE** | Keep unidirectional GRU in RailTwinGRUv2 (T4) with Masked Temporal Attention Pool. |
| **F4** | Spatial Index Construction Cost | DaySpatialIndex build time: Mean **9.84 ms**, p50 **10.61 ms**, p90 **10.84 ms**, p99 **11.05 ms** per full-day trajectory raster. | **MEDIUM** | **T10b**: Implement L1 in-process caching (TTL 60s, keyed on day + 5m window) to drop per-query latency to <0.1 ms. |
| **F5** | Stacking Weight Autopsy | B3_Lin linear regression benchmark has high calib MAE (**26.49 min**). Fallback weights allocate up to 35% to B3 on long horizon. | **MEDIUM** | **T7**: Implement rolling NNLS refit on trailing 90-day window with non-inferiority gate vs static weights. |
| **F6** | Conformal ACI State Persistence | AdaptiveConformalInference state (current_alpha, history) is stored in-memory only. Restarts reset coverage state. | **HIGH** | **T6**: Implement ConformalPIDCalibrator + SQLite persistence (conformal_pid_state table migration 008). |

---

## Detailed Forensic Evidence

### F1: Hash Determinism & Embedding Collision Analysis
1. **Process Salt Test**:
   - Running json.dumps({c: abs(hash(c)) % 1200 for c in codes}) across separate Python processes produced distinct bucket assignments due to PEP 456 hash randomization (PYTHONHASHSEED).
   - If hash() were relied on in serving across workers, embeddings would corrupt across process lifecycles.
2. **Bucket Collision Statistics** (1,223 station codes -> 1,200 buckets):
   - Total Distinct Station Codes in DB: **1,223**
   - Occupied Buckets: **777 / 1200** (423 empty buckets due to hash dispersion)
   - Colliding Buckets (depth >= 2): **328 buckets**
   - Total Colliding Pairs: **585 pairs**
   - Maximum Bucket Depth: **5 stations**
   - Sample Collisions:
     - Bucket 879: ['ABSA', 'TNGL']
     - Bucket 1045: ['ADH', 'FK', 'LKT', 'WSA']
     - Bucket 1046: ['ADI', 'FL', 'LKU']
     - Bucket 1133: ['AGC', 'BNY', 'CVP', 'GNT']
     - Bucket 887: ['AH', 'KRPP', 'RNC']
3. **Serving Path Vulnerability**:
   - pi/predictor.py line 266 called self._gru_model(t_in) without passing 	arget_station_idx or context, defaulting to index 0 and zeros context.
   - **Resolution**: StationVocab (T1) guarantees bijection ( 	o N$) with zero collisions and persistent ocab.json.

---

### F2: Feature Wiring Audit
Cross-referencing ml/features.py (25-dim) against engine subsystems revealed disconnected signals:

| Signal Name | Target Feature in v2 | Source Subsystem | Current Status in v1 |
|---|---|---|---|
| Upstream Rake Delay | upstream_rake_delay_min | engine/rakes.py (turnaround resolver) | **Disconnected** (only raw naive delay was read) |
| Upstream Rake Buffer | upstream_rake_buffer_remaining_min | engine/rakes.py (scheduled turnaround buffer - consumed) | **Missing** |
| Rake Link Flag | 
ake_linked (0/1) | data/seeds/rake_links.json | **Missing** |
| TSR Count Ahead | 	sr_active_ahead_count | data/seeds/speed_restrictions.json | **Missing** |
| TSR Max Slowdown | 	sr_max_slowdown_pct | data/seeds/speed_restrictions.json | **Missing** |
| Festival Multiplier | estival_load_multiplier | data/seeds/festivals.json | **Missing** |
| Position Belief Entropy | position_belief_entropy | engine/position_resolver.py P(seq=k) | **Missing** |
| Position Mode Prob | position_p_mode | engine/position_resolver.py P(seq=k) | **Missing** |
| Recency Latency | minutes_since_last_obs | station_events ({as\_of} - t_{last\_event}$) | **Missing** |

---

### F3: GRU Directionality Verification
- Inspected ml/model_seq.py: 
n.GRU(input_size=8, hidden_size=128, num_layers=2, batch_first=True, dropout=0.2).
- Directionality is **unidirectional** (idirectional=False by PyTorch default).
- Unidirectionality ensures no future temporal leakage occurs along the journey sequence.
- **T4 Plan**: RailTwinGRUv2 will strictly retain unidirectional GRU combined with MaskedAttentionPool and NeighborInteraction cross-attention.

---

### F4: DaySpatialIndex Performance Benchmarking
Benchmarking 10 full days of train trajectories on the NDLS-DDU corridor:
- Trajectory raster build: **1440 minute-grid**
- Mean build latency: **9.84 ms**
- Median (p50): **10.61 ms**
- p90: **10.84 ms**
- p99 / Max: **11.05 ms**
- **Conclusion**: A full rebuild per API ETA call introduces ~10ms latency. Implementing the L1 in-process time-bucket cache (T10b) will reduce query-time overhead to <0.1 ms.

---

### F5: Stacking Weight Autopsy
- Inspected ml/artifacts/manifest.json:
  - 3_linear_regression_calib_mae: **26.49 min** (severe baseline error).
- Stacking fallback weights in ml/ensemble.py:
  - Short ( \le 90$): [GBM: 0.05, GRU: 0.05, LR: 0.00, B1: 0.85, B3: 0.05]
  - Medium ( < km \le 250$): [GBM: 0.40, GRU: 0.20, LR: 0.10, B1: 0.20, B3: 0.10]
  - Long ( > 250$): [GBM: 0.35, GRU: 0.15, LR: 0.10, B1: 0.05, B3: 0.35]
- **Observation**: B3_Lin receives 35% weight in the long horizon fallback despite 26.49 min MAE.
- **Remedy (T7)**: Rolling weekly NNLS calibration on 90-day trailing observed data with Wilcoxon non-inferiority gating.

---

### F6: Conformal ACI State Persistence Audit
- Inspected ml/conformal.py::AdaptiveConformalInference:
  - self.current_alpha and self.history reside solely in RAM.
  - On application restart / container deploy, current_alpha reverts to initial 0.20, losing empirical error tracking.
- **Remedy (T6)**: Implement ConformalPIDCalibrator with SQLite table conformal_pid_state (migration 008) and ICML 2023 PID control dynamics.
