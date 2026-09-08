# RailTwin-X Architecture & Model Engineering Roadmap

## 1. Executive Summary
This document outlines technical specifications and prerequisites for upcoming engineering milestones in RailTwin-X, focusing on transitioning experimental research challengers into production-grade served models.

---

## 2. Milestone M1: Wiring Real Sequence History for PyTorch Non-Crossing GRU Challenger

### 2.1 Current Architecture & Runtime Reality
- **Served Champion**: LightGBM Quantile + NNLS Convex Ensemble (`Tier2_Convex_Ensemble_NNLS`), calibrated via Mondrian Conformal Quantile Regression (CQR).
- **Experimental Challenger**: PyTorch `NonCrossingGRUQuantileModel` (checkpoint `model_gru_challenger.pt`), currently gated behind `_gru_sequence_ready = False` in `api/predictor.py`.
- **Reason for Gating**: The live runtime hydrates snapshot point-in-time tabular vectors (`TrainFeatureVector` with 25/34 scalar features). In contrast, a recurrent network (GRU) requires an ordered, temporal, multi-station sequence tensor ($[B, T, F]$ where $T \approx 8$ historical stops and $F$ sequential delay features). Without a verified streaming sequence aggregator, feeding synthetic or degenerate sequences to the GRU at runtime would degrade prediction reliability.

### 2.2 Requirements for Production Serving

Wiring the PyTorch GRU challenger to real operational history requires three foundational engineering deliverables:

#### A. Rolling Multi-Station History Tensors
1. **Dynamic Historical Window Extraction**:
   - Query the `station_events` and `ad_events` tables for the trailing $T=8$ passed stations of the specific train instance.
   - For trains with fewer than $T$ passed stations (e.g. newly departed from origin), construct a zero-padded / mask-padded prefix with a binary padding mask tensor ($[B, T]$) matching the `-1e9` attention mask convention implemented in `ml/model_seq.py`.
2. **Station Identity Embeddings**:
   - Map historical station sequence codes to the 1,200-station embedding vocabulary lookup table (`station_vocab.json`).
3. **Temporal Feature Vector ($[B, T, F_{seq}]$)**:
   - For each time step $t \in [1..T]$, extract:
     - `actual_delay_arr_min` and `actual_delay_dep_min`
     - `dwell_overrun_min`
     - `inter_station_transit_time_min`
     - `section_speed_kmph`
     - `weather_fog_flag` and `precipitation_mm`

#### B. Preprocessing Parity Between Training and Inference
1. **Feature Normalization Rigor**:
   - Ensure the exact feature scaling statistics (robust quantile scalers, z-score normalizers) stored during offline training in `ml/artifacts/` are applied to online sequence tensors with bitwise parity.
2. **Context Modulator Alignment**:
   - The GRU utilizes Feature-wise Linear Modulation (FiLM) conditioned on a 25-dimensional static/snapshot context vector (train priority, class, destination distance, network section occupancy). Ensure runtime context vectors match training time feature ordering identically.
3. **Quantile Monotonicity Verification**:
   - Softplus projection heads guarantee non-crossing output intervals ($q_{10} \le q_{50} \le q_{90}$); verify that torch inference adheres to post-processing bounds and interlock checks.

#### C. Rigorous Shadow Evaluation & Safe Promotion Gate
1. **Continuous Shadow Evaluation**:
   - Stream predictions through the `shadow_log` table concurrently alongside the served champion without serving GRU outputs directly to end users.
   - Collect $\ge 10,000$ consecutive real-world prediction receipts with subsequent actual arrival timestamps.
2. **Statistical Non-Inferiority Verification**:
   - Run two-sided paired Wilcoxon signed-rank test against the served champion (`scripts/champion_gate.py`).
   - Criteria for promotion:
     - Statistically significant error reduction ($p < 0.05$)
     - Coverage maintained within target interval ($78\% \le \text{Coverage}_{80} \le 84\%$)
     - Strict latency SLA: Single-item inference CPU latency $p_{95} \le 8.0\text{ ms}$
3. **Zero-Downtime Hot-Swapping**:
   - Once all gates pass, flip `_gru_sequence_ready = True` via configuration toggle without service restarts.

---

## 3. Milestone M2: Topological Track Graph Expansion (Q1 2027)
- Expand topological route stations and interlock networks beyond the initial NDLS–CNB–LKO trunk corridor to all inter-divisional boundaries across Northern Railway (NR) and North Central Railway (NCR).
- Integrate automated block section signaling states from CMS and COA into the spatial feature builder.

---

## 4. Milestone M3: Autonomous Dispatch & Advisory DSS (Q2 2027)
- Multi-agent conflict resolution engine with automated signal clearance and loop-siding priority recommendations.
- Connection custody optimizer evaluating real-time passenger delay savings across connecting trains at major junction hubs.
