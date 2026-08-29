# RailTwin-X v4 — Judge Q&A Cheat Sheet

> Quick answers to the most likely judge questions.

---

## ML & Model Questions

**Q: Why LightGBM + GRU? Why not just one model?**  
A: LightGBM is the 1–6 hour ensemble backbone with CQR calibration. The GRU adds temporal sequence memory across the station trajectory — a train's delay pattern evolves over time, not just at one snapshot. Our champion GRU beats LGB on MAE (7.29 vs 11.46). The 3-tier design gives graceful degradation: if GRU is offline, LGB fires; if LGB fails, historical lookup serves.

**Q: How do you avoid quantile crossing? (p10 > p50 is invalid)**  
A: We use a CQR Crossing Guard in `ml/ensemble.py` that enforces `p10 ≤ p50 ≤ p90` by clamping at predict time. Result: **0 crossing violations** in the test set.

**Q: What's CQR?**  
A: Conformal Quantile Regression — a post-hoc calibration technique. We compute residuals on a held-out calibration set and fit coverage factors per horizon bucket (1h/3h/6h). This guarantees the stated coverage % (e.g., 80%) holds empirically, not just in theory.

**Q: How do you prevent overfitting?**  
A: Strict time-series train/test split (21-day train, 7-day test) with no future leakage. The Wilcoxon promotion gate (p=0.0000) confirms the champion is statistically significantly better on the test week before promotion.

**Q: What's the Wilcoxon gate?**  
A: Before promoting any new model, we run a Wilcoxon signed-rank test comparing per-train MAE errors between old champion and new challenger on the held-out test set. p < 0.05 required for promotion. Our GRU passes at p=0.0000.

**Q: Why √hops in the CQR rollout?**  
A: Uncertainty compounds over hops. Empirically, uncertainty grows sub-linearly — closer to √hops than linearly. Using √hops scaling prevents the 6-hour band from being unrealistically wide while keeping 1-hour predictions tight.

**Q: What are Features F29/F30?**  
A: F29 = `rake_incoming_delay` (delay inherited from the physical rake's previous run, queried from rake_links). F30 = `crew_duty_pressure` (hours remaining in crew duty cap — fatigued crews halt more). Both are causal real-world signals for delay propagation.

---

## Data & Safety Questions

**Q: What data do you use? Is it real-time?**  
A: For the SIH demo, we generate 33,600 synthetic-but-realistic historical events across 28 days using probabilistic models calibrated to real Indian Railway delay patterns (chronic biases, weather effects, section variability). The architecture supports live NTES/Railtel feeds via the `/live_ingest_events` table and 3-tier data collector.

**Q: Is there ML in the safety layer?**  
A: **Zero.** The 5 deterministic safety interlock rules and 3 conflict scan types in `ConflictScanner` are pure if-then logic, no model weights. This is a hard architectural invariant — ML makes probabilistic predictions, safety rules make deterministic Go/No-Go calls.

**Q: What are the 5 safety rules?**  
A: (1) Minimum headway enforcement (5m/8m/14m by train class), (2) single-line opposing clearance (10m), (3) section follower catch-up, (4) platform occupancy, (5) rake-inherited departure delay. All output `human_ack_required: True`.

**Q: What happens if a train isn't in the DB?**  
A: Graceful degradation — the API returns the scheduled time with zero delay rather than crashing. The `tier_used` field tells the consumer it's a `Fallback_Schedule` response.

---

## DFC Freight Questions

**Q: How do you handle DFC freight trains differently?**  
A: (1) Separate WDFC/EDFC corridor routing in `seed.py`. (2) Freight-class-aware headways in `ConflictScanner` (14m coal, 8m container). (3) EMPTY_RETURN cascade events in `simulator.py` — when a loaded coal rake arrives late, its return empty train inherits the delay minus turnaround buffer. (4) `trailing_tonnage` and `is_dfc` fields in the DB schema.

**Q: What's WDFC/EDFC?**  
A: Western Dedicated Freight Corridor (Dadri → JNPT, 1,279 km) and Eastern Dedicated Freight Corridor (Dankuni → Sonnagar → DDU, 1,839 km). Both run at 100 km/h with no passenger trains, automated signaling, and 1.5km loop sidings.

---

## Engineering & Production Questions

**Q: Is this production-deployable?**  
A: Yes. `Dockerfile` + `docker-compose.yml` for containerization. `Makefile` for ops. Nightly pipeline runner (`scripts/nightly_pipeline.py`) for automated retraining. PSI drift monitor for data quality alerts. 78-test CI suite for regression protection.

**Q: How long does inference take?**  
A: Tier-2 LightGBM: ~2–5ms per train. Tier-3 GRU: ~15–30ms. The 5-second TTL response cache in `api/middleware.py` means the second request for the same train is sub-millisecond.

**Q: How do you prevent API abuse?**  
A: Token-bucket rate limiter in `api/middleware.py` — 60 requests/minute per IP, 10-token burst. Returns HTTP 429 with `Retry-After` header.

**Q: What's the database?**  
A: SQLite (single-file, zero-config) for the demo. The schema is designed to be PostgreSQL-compatible — swap the connection string in `config.py` for production scale.

**Q: How many trains/stations can this scale to?**  
A: The current seeded dataset: 150 trains, 110 stations, 33,600 events. The ML training (LightGBM + CQR + GRU) scales to 500k+ rows on a laptop in under 60 seconds thanks to Parquet snapshot caching. For all-India scale (~13,000 trains), partition by zone (NR/SR/ER etc.) and run one model per zone.

---

## Likely Follow-Up Challenge Questions

**Q: Your test MAE is 7.4 min at 1h. Is that good enough for dispatchers?**  
A: Indian Railways typically targets ±15 minutes as "on time." Our 7.4 min MAE with a p90 worst case of ~18 min covers 81% of trains correctly. More importantly, the *direction* of the prediction (getting worse vs recovering) is what matters for dispatcher decisions, and our GRU captures trajectory.

**Q: Can you prove no data leakage in the train/test split?**  
A: Yes — the split is strictly temporal. Training data ends at `max_date - 7 days`, test data starts at `max_date - 7 days`. All feature computations (historical averages, congestion counts) use only data available at the snapshot timestamp, not future data.

**Q: What's your deployment strategy for real-world use?**  
A: Phase 1: Shadow mode — RailTwin-X runs alongside existing systems, dispatchers see predictions but don't act on them; measure accuracy against actuals. Phase 2: Advisory mode — dispatchers see ACK-required advisories; human override always wins. Phase 3: Assisted mode — high-confidence automated holds for coal rakes on DFC with human override window.
