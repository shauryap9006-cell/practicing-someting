# RailTwin-X Judge FAQ & Technical Defense Architecture
**SIH Problem Statement ID 26028**: Dynamic ETA Forecast for Coaching Trains  
**Target Audience**: Smart India Hackathon Grand Finale Judges, Domain Railway Experts, and Senior System Architects.

---

### Q1: What makes RailTwin-X fundamentally different from apps like NTES or "Where Is My Train"?
**Answer:**
Existing train apps are **reactive telemetry viewers**: they plot where a train was 30 seconds ago based on GPS or track circuits. When projecting future arrivals, they use static run-rates or frozen delay assumptions that ignore network physics.
RailTwin-X is a **predictive digital twin**:
1. **Calibrated Uncertainty Cones (D1)**: We output p10–p50–p90 quantiles rather than brittle single-point estimates.
2. **Deep Corridor Foresight (D2)**: We anticipate rake turnaround deficits, junction headway queueing, and speed restrictions hours before the train reaches them.
3. **Causal Delay Autopsy (D3)**: We break down delays into 7 physics buckets with exact-sum mathematical additivity.
4. **Network Ripple & Connection Custody (D4)**: We quantify downstream rake impacts and calculate passenger-hours saved by holding interchange connections.
5. **Tamper-Evident Ledger (D5)**: Every served forecast is cryptographically sealed in a SHA-256 hash chain before the train arrives.

---

### Q2: Why is your 1-hour MAE tied with the frozen baseline (5.88 vs 5.84 min)?
**Answer:**
Because within 90 km of a destination, physical momentum dominates corridor behavior. A train traveling at 110 km/h with 35 km remaining has almost no physical leeway to recover or compound delay.
Competitors who claim 50% improvements at 1 hour are almost certainly guilty of **temporal data leakage** or cherry-picked test splits. We disclose the physics tie honestly and demonstrate our real advantage where static trackers fail completely: **36.3% error reduction at 3 hours** and **51.7% error reduction at 6 hours**.

---

### Q3: How do you guarantee the 80% confidence interval actually covers 80% of arrivals?
**Answer:**
Our pinball loss quantile regression models are empirically calibrated using conformal prediction bounds. Across 25,203 test observations in `ml/artifacts/metrics.json`, our empirical coverage is **80.64%** (with a target of 80.0%). The Winkler score (which severely penalizes both overly wide intervals and out-of-band misses) stands at **57.94**, proving high information density.

---

### Q4: How do you prevent data leakage during model training?
**Answer:**
We strictly prohibit random K-fold splits. All model evaluation uses **Rolling-Origin Temporal Cross-Validation** across 6 sequential time windows. When predicting an event on day $T$, the feature snapshot only has access to telemetry, events, and weather recorded prior to time $t$. Features like downstream block occupancy are strictly time-bounded to the query instant.

---

### Q5: Can Section Controllers trust an algorithmic recommendation to hold a train?
**Answer:**
RailTwin-X is explicitly architected as an **Advisory Decision Support System (DSS)**. We never auto-dispatch. All custody advisories display a mandatory jurisdictional notice:
> *"Section Controller Decision Support — Advisory Only. Operational authority remains strictly with the Divisional Operations Manager."*
We provide the Section Controller with a transparent mathematical trade-off metric: **Net Passenger-Hours Saved**, allowing them to justify dispatch actions with hard data rather than gut instinct.

---

### Q6: What is the exact formula for Connection Custody net passenger-hours saved?
**Answer:**
$$\text{Net Pax-Hours Saved} = \frac{(P_{\text{transfer}} \times H_{\text{next}}) - (P_{\text{onboard}} \times M_{\text{hold}})}{60}$$
Where:
- $P_{\text{transfer}}$: Estimated passengers transferring between feeder and connecting service (default: 35 pax).
- $H_{\text{next}}$: Headway until the next available connection service (e.g. 300 minutes for a 5-hour wait).
- $P_{\text{onboard}}$: Passengers already onboard the departing train (e.g. 600 pax).
- $M_{\text{hold}}$: Recommended departure hold (e.g. 6 minutes).
Example: $\frac{(35 \times 300) - (600 \times 6)}{60} = \frac{10,500 - 3,600}{60} = +115.0\text{ passenger-hours saved}$.

---

### Q7: How does the Causal Delay Autopsy guarantee mathematical additivity?
**Answer:**
Traditional heuristic attribution engines produce percentages that add up to 130% or 80%.
RailTwin-X enforces an exact additivity invariant:
$$\sum_{i=1}^{7} \Delta t_i \equiv \Delta t_{\text{total}}$$
Where components include:
1. `RAKE_TURNAROUND_INHERIT`
2. `TSR_SPEED_RESTRICTION`
3. `SIGNAL_HOLD`
4. `PLATFORM_OCCUPANCY_CONFLICT`
5. `WEATHER_FOG`
6. `LOCO_PILOT_RECOVERY` (negative minutes)
7. `RESIDUAL_FRICTION`
If the sum deviates by even 0.1 minutes, the automated test suite raises an assertion error (`tests/test_live_attribution.py`).

---

### Q8: Why use a SHA-256 hash-chained ledger instead of standard database rows?
**Answer:**
In government and railway procurement, third-party audits are critical. If prediction logs sit in a normal mutable database, a vendor could retrospectively overwrite old predictions after a train arrives late to artificially deflate reported MAE.
With our SHA-256 hash-chained ledger:
1. Every prediction generates a block hash sealed with the timestamp and previous block's hash.
2. Altering a single minute in block #29 invalidates the hashes of all subsequent 1,933 blocks.
3. Anyone can verify ledger integrity in 50 milliseconds via `verify_chain_integrity()`.

---

### Q9: What happens if real-time telemetry drops or sensors go offline?
**Answer:**
RailTwin-X employs a graceful degradation cascade:
1. **Full Telemetry**: Live position + corridor block occupancy + weather sensors → full quantile cone.
2. **Telemetry Packet Drop**: Kinematic Dead-Reckoning Engine computes estimated speed and distance based on last known velocity and track gradient. Confidence score degrades smoothly ($\tau = 300\text{s}$).
3. **Total Sensor Outage**: Fallback to historical baseline run-rates with an expanded uncertainty cone (p10–p90 spread widens to reflect uncertainty).

---

### Q10: How does the system scale to the full Indian Railways network (13,000+ trains daily)?
**Answer:**
- **FastAPI Async Architecture**: Python async route handlers with threadpool offloading.
- **SQLite / Postgres Connection Pooling**: Read replicas for passenger queries; serialized transaction queues for ledger writes.
- **Micro-caching**: 5-second TTL on advisory calculations; 4-second TTL on live position coordinates.
- **Inference Latency**: Under 25ms per prediction request using quantized LightGBM and ONNX runtime models.

---

### Q11: How are extreme weather conditions (e.g. Gangetic winter fog) incorporated?
**Answer:**
The Context Engine ingests ambient temperature, humidity, visibility, and precipitation. Under winter fog conditions (humidity > 90%, temperature < 15°C, visibility < 200m), Indian Railways signaling rules mandate a maximum speed of 60 km/h with detonator fog signaling. RailTwin-X automatically applies the fog-dawn penalty factor, widening the p90 arrival estimate to protect against station platform congestion.

---

### Q12: What is the primary business and passenger impact of RailTwin-X?
**Answer:**
- **For Passengers**: Replaces false "Right Time" certainty with calibrated arrival windows, eliminating platform anxiety and missed onward connections.
- **For Station Controllers**: Proactively identifies turnaround rake deficits and offers quantified hold trade-offs, saving hundreds of passenger-hours per junction daily.
- **For Indian Railways (CRIS / IRCTC)**: Enhances trust and operational transparency through mathematically auditable performance metrics and zero-mock integrity.
