# RailTwin-X — FLAWS_AND_FIXES.md
**Deep Technical Edition** · Derived from audit baseline `d074cc6` · Scope: engineering flaws only
Excluded by request: judge-facing polish, demo tips, park lists, cosmetic dead code.
Severity: **CRIT** (wrong results / broken build) · **HIGH** (materially wrong or degraded) · **MED** (risk / efficiency) · **LOW**
Verify column = the exact command/test that proves the fix.

---

## 0. EXECUTIVE PRIORITY MATRIX

| Rank | Flaws | Domain | Severity | Effort | Why first |
|---|---|---|---|---|---|
| 1 | F01, F02 | Calibration/eval | CRIT | 0.5 day | Every headline number is currently contaminated |
| 2 | F19, F20 | Position/truth-path | CRIT | 1 day | Root cause of "hardcoded" — the c_seq bug class |
| 3 | F15, F16 | Serving | CRIT | 0.5 day | Promoted champion benched; free accuracy unpaid |
| 4 | F21, F22 | Frontend truth | CRIT | 1 day | 12 core pages render mocks; UI can lie silently |
| 5 | F31, F32 | Performance | HIGH | 1 day | 945ms journey, 780ms board — per-request recompute |
| 6 | F39 | Wiring | HIGH | 0.5 day | 12 endpoint mismatches — codegen kills the class forever |
| 7 | F07–F10, F23–F25 | Brain + data | HIGH | 3–4 days | Context-blind NN, starved features, padded attention |
| 8 | F03, F04 | Calibration math | HIGH | 0.5 day | Blend-then-trust CQR is mathematically invalid |
| 9 | F43–F50 | MLOps | MED | 2 days | Drift does nothing; skew unmonitored; build broken |
| 10 | F33–F36, F26–F28 | Perf/data hygiene | MED | 1–2 days | |

Dependency-ordered execution plan: §12. Retrain decision: §11 — **recalibrate now, rewire now, retrain exactly once (after F07/F23/F25 land), never retrain to fix plumbing.**

---

## DOMAIN A — CALIBRATION & EVALUATION MATHEMATICS

### F01 · Calibration/test set contamination — every headline metric is partially in-sample
- **Severity:** CRIT · **Evidence:** Audit §1.6: held-out window (Aug 22–28) used simultaneously for CQR calibration, MAE backtest, and Wilcoxon gate. §1.4: coverage "80.1% / 81.1% / 99.1%" measured on the same residuals that set the conformal quantile.
- **Root cause:** One 7-day window playing three roles. Conformal guarantees are finite-sample valid only on data disjoint from calibration. Your 84.6% coverage and ">56% error reduction" are unproven as stated.
- **Advanced fix — Purged rolling-origin evaluation + 3-way disjoint split:**
  1. Split by time into **train / calibration / test** with an **embargo gap** (24–48h) between calibration and test to kill boundary leakage from rolling features (López de Prado purged-CV discipline).
  2. Replace the single split with **6-fold rolling-origin (prequential) CV**: folds anchored at monthly origins across the 18-month archive; report **mean ± std MAE** across folds. One lucky window becomes six windows — robustness a reviewer cannot argue with.
  3. Group folds by `(train_no, run_date)` so one physical run never straddles two folds.
  4. Report **Winkler interval score** and **CRPS** alongside coverage. Coverage alone hides over-width bands; Winkler = sharpness + coverage in one number: `W = (u−l) + (2/α)(l−y)·1{y<l} + (2/α)(y−u)·1{y>u}`.
- **Verify:** `pytest tests/test_eval_protocol.py` asserts cal∩test = ∅ by construction + folds span ≥6 origins; `make eval` emits per-fold table to `metrics.json`.

### F02 · Three unreconciled MAEs (7.4 / 5.82 / 3.81) — no single source of truth
- **Severity:** HIGH · **Evidence:** Audit claims C-01 (7.4 min), §1.1 gru_config (5.82), §8.2 money test (3.81).
- **Root cause:** Numbers hand-copied from different artifacts (GRU-only vs ensemble vs per-horizon) into prose. Any two documents will drift.
- **Advanced fix — Metrics-as-code registry:** define a canonical `metrics.json` schema (`{model, split, horizon, source_label, mae, winkler, crps, coverage, n}`); a generator script renders the one-pager and `07_METRICS.md` **from** it. CI job: regenerate → `git diff --exit-code` → docs drift fails the build. Humans are removed from the copying path entirely.
- **Verify:** CI job `make docs-check` passes; exactly one MAE exists per (model, horizon) tuple.

### F03 · CQR applied per-model then blended — coverage guarantee does not survive blending
- **Severity:** HIGH · **Evidence:** Audit §1.3 (blend weights) + §1.4 (CQR per direct/delta model). Order of operations not reconciled; if blended outputs are trusted as conformal, the guarantee is void.
- **Root cause (the math):** Conformal coverage is not preserved under convex mixing. If each model's interval has P(y∈[l_m,u_m]) ≥ 0.8, the blended interval `q = Σ w_m q_m` satisfies **no** coverage guarantee — quantile functions only compose under comonotonic coupling, which independent models do not satisfy.
- **Advanced fix — Calibrate the ensemble as one model:** treat `f_ens` (the final blended predictor) as the single regression function; compute nonconformity scores `S_i = max(q10^ens − y, y − q90^ens)` **on ensemble outputs** from the calibration window only. Then upgrade to:
  - **Mondrian Conformal:** partition calibration by `(hops bucket × train class)`; per-cell finite-sample quantile `ceil((n_c+1)(1−δ))/n_c`. Sharpens short-horizon bands (your 1h band) and stops the 6h over-coverage.
  - **Adaptive Conformal Inference (ACI, Gibbs & Candès 2021) for production:** online level `α_{t+1} = α_t + γ(α − err_t)` where `err_t = 1{y_t ∉ [l_t,u_t]}`. Conformal that self-heals under non-stationarity — exactly rail data. Quantile taken over a sliding nonconformity window; no retraining needed to maintain coverage.
- **Verify:** Property test — on a fresh test window, empirical coverage ∈ [0.75, 0.85] per Mondrian cell; ACI simulation on replayed stream holds coverage through an injected regime shift.

### F04 · 6-hour coverage 99.1% vs 80% target — bands ~2× too wide, and a linear model holds 25% of the weight there
- **Severity:** HIGH · **Evidence:** Audit §1.4 (99.1%), §1.3 (LR weight 0.25 at long horizon).
- **Root cause:** Global conformal quantile dominated by the hardest slice + delta-model weakness at 6h patched by the LR benchmark. Wide bands are a *defect*: they're useless for planning and they announce model weakness.
- **Advanced fix:** (a) Mondrian per-horizon cells (F03) directly shrink the 6h band to its slice's difficulty; (b) **learned stacking via non-negative least squares per horizon bucket**: fit `w* = argmin Σ ρ_τ(y, Σ w_m q_m)` s.t. `w ≥ 0, Σw = 1` (scipy `nnls` on the pinball objective, refit on a rolling window) — replaces hand-set 0.65/0.35/0.25 with data-chosen weights, guaranteed convex; (c) select band construction by **minimum Winkler**, not maximum coverage; (d) if LR remains non-negative-weighted after NNLS, that is a measurement that the delta model must be retrained on longer history (F25), not a permanent 25% crutch.
- **Verify:** 6h Winkler score improves ≥30% vs current; LR stack weight < 0.10 after v3 retrain; NNLS weights versioned in `metrics.json`.

---

## DOMAIN B — NEURAL ARCHITECTURE

### F07 · The GRU is context-blind — it cannot see weather, congestion, or train class
- **Severity:** HIGH · **Evidence:** Audit §1.1: GRU input = 8 sequential features only (`delay_arr…dwell_delta`). The 25 tabular features feed LightGBM exclusively.
- **Root cause:** Architectural split: the neural net models only the *temporal* signal; all *context* lives in trees. The NN's plausible deniability on "deep learning" is thin — it's a sequence encoder, not the brain.
- **Advanced fix — Context-conditioned GRU via FiLM (Feature-wise Linear Modulation):**
  - Encode the 25-feature context vector `c` through a small MLP producing per-unit scale/shift: `γ, β = MLP(c)`; apply `h' = γ ⊙ h + β` before the shared projection (FiLM layers).
  - Alternative/plus: **DeepAR-style covariate init** — `h0 = encoder(c)` instead of zeros, so the recurrence starts from a context-informed state.
  - Keep parameter growth tiny: context MLP 25→64→2×128 ≈ 18k params. Total model stays <200k params, still CPU-trivial.
- **Verify:** Ablation: v2 (current) vs v3 (FiLM) on the same purged folds — v3 must win ≥10% MAE at 3h; GRU feature-attribution (integrated gradients) shows nonzero mass on `fog`, `trains_ahead`, `hist_avg_delay`.

### F08 · Zero-padding attended without masking — early-journey predictions are diluted
- **Severity:** HIGH (silent accuracy tax) · **Evidence:** Audit §1.1: `seq_len=8, zero-padded for short histories`; attention code shows no mask.
- **Root cause:** A train 2 stations out of 12 has 6/8 steps as padding; softmax attention spreads mass over fake steps. The model is *worst exactly where short-horizon accuracy matters most* — plausibly why the 1-hop direct GBM dominates and why early-journey ETAs feel flat.
- **Advanced fix:** masked attention — `attn_scores = scores.masked_fill(~valid_mask, −inf)` before softmax, plus a **padding embedding** (learned "no-event" vector) instead of literal zeros for the GRU itself. One-line-class fix, real effect.
- **Verify:** Stratified eval on journeys with ≤3 realized events: MAE improves vs v2; property test: attention mass on padded positions == 0.

### F09 · Station identity compressed to booleans — `is_junction`/`is_terminus` carry ~0% gain
- **Severity:** MED · **Evidence:** Audit §1.2 importance table (0.00% / 0.02%).
- **Root cause:** Station-specific effects (geometry, platform count, chronic congestion at that node) cannot live in two bits.
- **Advanced fix — Learned embeddings with cold-start fallback:** `nn.Embedding(n_stations≈1.2k, dim=8)` for target station + dim-4 section embeddings in the sequence. Unseen stations at inference: fall back to a hashed station bucket + static features (embedding dropout during training teaches this). +~12k params.
- **Verify:** Embedding nearest-neighbor sanity (junction hubs cluster); ablation ≥5% MAE improvement at junction targets.

### F10 · No monotonicity constraints on the trees — the GBM can learn physically absurd directions
- **Severity:** MED · **Evidence:** Audit §1.3: LightGBM params show no `monotone_constraints`; the smoke-test ratio (~0.94) is GRU-side; nothing pins GBM behavior.
- **Advanced fix:** LightGBM native `monotone_constraints`: `current_delay:+1`, `delay_velocity:+1`, `hist_avg_delay_train_target:+1`, `km_remaining:+1`, `hops_remaining:+1`, `sched_halt_target_min:+1`, and **quantile Huber loss** (`quantile_huber`-style robust pinball) to blunt NTES rounding/label noise outliers. Also `min_data_in_leaf` up + `lambda_l2` to stop overfit micro-splits on 21 days of data.
- **Verify:** Property test (Hypothesis): `predict(delay=d+ε).p50 ≥ predict(delay=d).p50` sampled over the input domain — passes for both GBM and GRU paths.

### F11 · GRU latency "0.016 ms/sample" is not credible — benchmark methodology flaw
- **Severity:** MED · **Evidence:** Audit §1.3 registry latency vs a 2-layer GRU(128) + attention + heads on CPU (~0.5–2 ms/sample realistic).
- **Root cause:** Batch-amortized or per-token arithmetic presented as per-sample. A judge load-testing this sees 100× worse and trust evaporates.
- **Advanced fix:** re-benchmark honestly: single-sample p50/p95 and batch-64 p50/p95, `torch.set_num_threads(1)` in server context (thread thrash under FastAPI concurrency is the hidden killer), and publish both numbers. If per-sample p95 > 50 ms, quantize heads to fp16 or export the encoder to ONNX with dynamic batch.
- **Verify:** `make bench-model` writes a latency table to `metrics.json` (methodology string included).

### F12 · Freight and coaching trains share one model — PS is coaching-only
- **Severity:** MED · **Evidence:** Audit §3.3: 537 trains mixed classes; no class stratification in eval.
- **Advanced fix:** add `train_class` embedding (or separate Mondrian cells F03); report metrics **stratified by class**; tune/coach-weight the loss toward coaching runs (the PS target population).
- **Verify:** per-class metrics table in `metrics.json`; coaching MAE reported as the headline.

### F13 · Explainability by attention weight — scientifically shaky, and it will be poked
- **Severity:** LOW (credibility) · **Evidence:** Audit §1.1 attention design; §8.4 Q1–Q10 leans on "attention" for why-answers.
- **Advanced fix:** keep attention for *modeling*, not for *explanation*. Serve explanations from **TreeSHAP** for the GBM path (exact, fast) and **integrated gradients** for the GRU path; cache top-3 drivers per prediction in the response (`drivers: [{feature, contribution}]`). Same UX, defensible method.
- **Verify:** explanation endpoint returns contribution-signed drivers; spot-check: fog-heavy input shows weather in top-3.

---

## DOMAIN C — ENSEMBLE & SERVING

### F15 · Promoted champion is benched — registry says GRU, traffic gets LightGBM
- **Severity:** CRIT · **Evidence:** Audit §1.3 (GRU won promotion, MAE 5.82 vs 8.36, p<0.05) vs §2.1 API response `"tier_used": "Tier2_LightGBM_CQR"`. §10.1 then claims GRU "executes live" — the report contradicted itself instead of flagging serving drift.
- **Root cause:** Promotion gate writes `registry.json`; serving path never reads it. Governance exists on paper only.
- **Advanced fix — Registry-enforced serving + shadow mode:**
  - Predictor loads `registry.champion` (name + **artifact sha256**) at startup; refuses to boot on mismatch; exposes `GET /api/system/model-info` `{served_model, version, sha, loaded_at}`.
  - **Shadow evaluation:** every production predict also runs the challenger, logging `(p50_chall, p50_served, |Δ|, latency)` to a `shadow_log` table (sampled 10%). Weekly promotion gate consumes shadow data — champion-challenger becomes a continuous, evidence-producing loop instead of an event.
  - CI test pins: `assert predictor.served == registry.champion` and artifact hash match.
- **Verify:** `pytest tests/test_serving_pinning.py` green; `curl /api/system/model-info` shows the GRU; shadow_log accumulating rows.

### F16 · Ensemble clamping happens, but crossing can still be produced upstream of it
- **Severity:** MED · **Evidence:** Audit §1.3 post-clamp formula; no property test that the *serving path* (blend + clamp + conformal widening) preserves ordering.
- **Advanced fix:** one `enforce_quantile_order()` pure function applied as the final serving step (post-conformal); property-based test with Hypothesis over adversarial inputs (NaN → sanitized, ±1e9 delays, empty history) asserting `0 ≤ p10 ≤ p50 ≤ p90 ≤ cap` always. Move the guarantee from "architecture happens to" to "tested invariant."
- **Verify:** `pytest tests/test_quantile_property.py` (Hypothesis, 500 examples) green.

### F17 · Missing provenance stamps on ETA responses
- **Severity:** MED · **Evidence:** Audit §2.5: no `model_version`, `feature_version`, `data_freshness_seconds` on core endpoints.
- **Advanced fix:** every prediction response carries `{model: {name, sha}, feature_version, as_of_ts, position: {seq, confidence, basis}}` — this is what makes a prediction *auditable* and kills the "hardcoded" perception structurally (a static number can't carry live provenance).
- **Verify:** schema test on 3 endpoints; UI renders "model v3 · data 12s old".

### F18 · In-memory cache only on `/v1/advise` (5s TTL) — hot paths hit SQLite raw
- **Severity:** MED · **Evidence:** Audit §2.3, §7.1.
- **Advanced fix — Compute-on-write snapshot cache:** board/ETA responses cached under key `(last_snapshot_id, feature_version, model_sha)`; invalidated by the collector tick, not by TTL. Reads become O(1) dict lookups between ticks; correctness is version-pinned, not time-hoped. Add **ETag/If-None-Match** on board responses so polling costs bytes, not CPU, and a **SSE stream** (`/api/board/stream`) as the push path (polling as fallback) — this is the "dynamically updates" requirement done properly.
- **Verify:** k6: 50 concurrent board readers, p95 < 100ms, origin CPU flat between ticks.

---

## DOMAIN D — POSITION RESOLUTION & TRUTH-PATH

### F19 · The `c_seq` falsy-default bug — the system does not know where the train IS
- **Severity:** CRIT · **Evidence:** Audit §2.4: `c_seq = current_seq or max(1, target_seq − 1)` (predictor.py:97). External queries assume 1-hop-from-destination; upstream delays ignored; flat ~10-min answers. Root cause of C2/C3.
- **Root cause:** A default parameter papering over a missing subsystem: **train position estimation**. The model was never the problem — its *state input* was fictional.
- **Advanced fix — Probabilistic Position Resolver (soft position):**
  - Maintain per-run state: `last_event (seq, ts, delay)` + schedule + section run-times.
  - Compute a posterior over candidate positions: `P(seq=k) ∝ exp(−Δt_since_k/τ_k) · SchedPrior(k | t_now) · SpeedPrior(section_k)` — dead-reckoning between the last event and next scheduled stop, decayed by event recency.
  - **Marginalize the ETA over the posterior:** `E[ETA] = Σ_k P(k) · ETA(seq=k)`; band = mixture band; report `position: {mode_seq, confidence}`. This is strictly better than a point guess: it propagates honest uncertainty about *where the train is* into the ETA band, and degrades gracefully when the feed is stale.
  - Fuse `ad_events` (set-in/set-out actuals) as hard evidence when present — human confirmations dominate the posterior.
- **Verify:** replay test: 75-min-delayed train at seq 2 queried for seq 8 returns multi-hop-delay-cascaded p50 (≈86-min class, not ~10); `position.confidence` present; unit tests for posterior normalization.

### F20 · No reconciliation between feed position, schedule, and actuals — silent staleness
- **Severity:** HIGH · **Evidence:** Audit §3.4: RapidAPI fails → MockReplayAdapter fallback; §2: board reads `station_events` without age checks.
- **Advanced fix:** position record carries `source, age_s, basis`; resolver refuses inputs older than a configurable horizon and reports `position.basis = "last_event|dead_reckoning|schedule_only|human_confirmed"`. UI shows basis. No silent downgrade paths anywhere.
- **Verify:** kill the feed in a test; ETA band widens and basis degrades visibly instead of numbers freezing.

### F21 · 12 core pages import `mockStore` directly — the demo face is disconnected from the brain
- **Severity:** CRIT · **Evidence:** Audit §5.1: Overview, Trains, TrainDetail, Gantt, Advisories, Crew, Maintenance, Audit, Model, CorridorMap, Kiosk, Landing all read `@/mock/store`.
- **Root cause:** The mock was the original scaffold; pages were never migrated. Backend excellence is invisible by construction.
- **Advanced fix:** migrate via the typed client (F39) so each page swap is mechanical: replace `mockStore.x` with `useQuery(api.x)`; **delete the mock import path from the dashboard bundle** (`webpack/vite alias` error on `@/mock/store` inside `pages/dashboard/**` — make regression impossible at build time). Mocks survive only behind `?demo=1` with a visible DEMO ribbon.
- **Verify:** build fails if any dashboard page imports mockStore; E2E: TrainDetail shows backend `p50` matching `curl` of the same endpoint.

### F22 · Silent mock fallback on API failure — the UI lies about its data source
- **Severity:** CRIT · **Evidence:** Audit §4.4/§5.1: `web/src/lib/api.ts:45-48` catches fetch failure → mockStore, no banner.
- **Advanced fix — Data-source state machine:** every query resolves to `LIVE | STALE(age) | OFFLINE | DEMO`; a global `StatusBar` chip + per-page banner renders the state and age; fallback to mock only in explicit demo mode. The "updated Ns ago" pulse is the *liveliness contract* — absence of freshness is displayed, never simulated.
- **Verify:** stop backend → UI flips to OFFLINE with timestamp; restart → LIVE within one poll; no silent content swap at any point.

---

## DOMAIN E — DATA & FEATURES

### F23 · Spatial congestion features: correctly computed, 0% gain — starved by sparse seeds
- **Severity:** HIGH · **Evidence:** Audit §1.2: `trains_ahead_30k`, `opposing_trains_30k`, `sum_delay_trains_ahead`, `section_occupancy_pct` all 0.00% gain, "sparse in seed DB."
- **Root cause:** Feature variance ≈ 0 in training data → trees never split on them → your congestion narrative has zero learned evidence (and F03-style judge claims collapse under one importance table).
- **Advanced fix — Density-aware corpus construction:** regenerate seeds at realistic corridor density (your ASSETS.md §3 spec: peak-hour clustering, freight+coaching mixing, opposing traffic) **and** ingest the 300K parquet corpus as training rows (source-labeled). Target: >30% nonzero on all spatial features. Then retrain (single retrain, §11). Additionally prune any feature that still shows 0 gain post-density — smaller feature surface = less drift to monitor (F46).
- **Verify:** `SELECT` nonzero fraction ≥ 0.3 per spatial feature; post-retrain importance table shows spatial gain > 2%.

### F24 · Weather features encode "weather now at target" — fog gain 0.01%
- **Severity:** HIGH · **Evidence:** Audit §1.2: `fog_flag_target 0.01%`, `rain 0.30%`.
- **Root cause:** Fog matters **along the remaining route at predicted passage time**, not at the destination at query time. The feature as built is nearly information-free.
- **Advanced fix — Forecast-aligned weather (as-of joins):** build `weather_grid(section, valid_at, issued_at)`; training joins the forecast **issued ≤ snapshot time** (leakage-safe); serving joins latest issued forecast per remaining section, weighted by the ETA distribution (F19 posterior gives passage-time weights). This is the "join forecast to ETA, not to now" pattern — and it makes the fog demo real instead of theatrical.
- **Verify:** fog-hour stratified MAE improves; integrated gradients (F13) shows weather mass on foggy days only.

### F25 · 3-week training window; 17.5 months relegated to lookup priors
- **Severity:** HIGH · **Evidence:** Audit §1.6: trained on Aug 1–21 only; 216k events used as `hist_*` lookups.
- **Root cause:** Non-stationarity fear handled by discarding history — backwards. History is handled by *weighting*, not deletion; 21 days cannot learn seasonal structure (fog season, monsoon, festivals).
- **Advanced fix — Exponential time-decay training on the full archive:** `w_i = exp(−λ · age_days_i)`, λ = ln2/90 (90-day half-life); report **effective sample size** Σw²/(Σw)² alongside. Pairs with rolling-origin CV (F01). Seasonal patterns enter through data; recency dominance enters through weights.
- **Verify:** v3 trained on 18 months w/ decay beats v2 on 6-fold CV mean MAE; ESS reported in metrics.json.

### F26 · Train/serve feature skew is unmonitored — `hist_*` computed over different windows in the two paths
- **Severity:** HIGH (latent) · **Evidence:** Audit §1.2 vs §2.1: training features from `SnapshotGenerator` with point-in-time masking; serving recomputes over the live DB including post-cutoff rows.
- **Root cause:** Two code paths assembling "the same" features = the classic source of models that tested well and serve worse.
- **Advanced fix — Feature store + replay hash test:** materialize `feature_snapshots(fv_hash, train_no, station, ts, features_json, input_version)` from the nightly pipeline; serving reads point-in-time joins from it. CI **replay test**: push 1,000 historical snapshots through the serving path, hash each feature vector, diff against training hashes — any skew fails the build. This permanently kills the "defined but not fed" defect class.
- **Verify:** replay-hash test green; `feature_version` stamped on responses (F17).

### F27 · Data provenance unlabeled at the row level — "real NTES corpus" is an unverified claim
- **Severity:** HIGH (integrity) · **Evidence:** Audit §1.6: `curated_real_events.parquet` used for seeds/training with no source verification path.
- **Advanced fix:** `source TEXT NOT NULL CHECK(source IN ('rapidapi','ntes_curated','synthetic','human','inferred'))` on all event tables + adapter-enforced labeling (ASSETS.md §11); eval reports **per-source** metrics; no benchmark mixes sources silently. If the parquet's realness can't be evidenced, it ships labeled `synthetic` — an honest label costs nothing; a false one costs everything.
- **Verify:** schema check constraint live; `metrics.json` rows carry `source_label`.

### F28 · Simulation clock anchored to absolute future dates (2026) — provenance ambiguity
- **Severity:** MED · **Evidence:** Audit baseline dates + seed windows in 2026.
- **Advanced fix:** make the simulation timeline *relative* (T+0 anchored, `clock_mode: SIM|LIVE` already exists — extend seeds to generate relative offsets, render `SIM +14d` in UI). Absolute fake dates read as fabricated data; relative sim time reads as a deliberate test harness.
- **Verify:** seeds regenerate relative; UI displays sim anchor.

### F29 · PSI monitors 7 features and does nothing on breach; threshold drift between code (0.25) and docs (0.20)
- **Severity:** HIGH · **Evidence:** Audit §1.4 (CLI print + log only) + §8.4 Q9 overclaim ("automated retraining alerts").
- **Advanced fix — Drift → action pipeline with sequential detection:**
  - Keep PSI for feature marginals; add **Page-Hinkley / CUSUM change detection on the rolling residual stream** (outcome drift, which PSI cannot see) and **ADWIN** on prediction-error rate — research-grade online detectors, cheap to implement.
  - Wire: any detector firing → (1) notification-center event, (2) auto-created backlog task, (3) **ACI already self-corrects coverage in the interim** (F03), (4) nightly job auto-runs CQR recalibration (calibration is cheap; retraining stays human-gated).
  - Thresholds live in one config; docs generate from it (F02 pattern).
- **Verify:** fault-injection test: shift `current_delay` distribution in a replay → detector fires → task created → recalibration job runs → coverage restored without retrain.

---

## DOMAIN F — PERFORMANCE

### F31 · `get_train_journey` 945 ms — `PredictorService` rebuilt per request, historical baselines recomputed per request
- **Severity:** HIGH · **Evidence:** Audit §7.2: routes.py:90 instantiates a new service per request; `_compute_historical_baselines()` scans 333,600 rows / 7,741 pairs **every call**; contradicts §3.2's lazy-singleton claim — two instantiation patterns coexist.
- **Advanced fix:** (a) single DI-provided singleton everywhere (FastAPI `Depends(get_predictor_service)`); (b) **materialize baselines**: `hist_baselines(train_no, station, avg_delay, p90_delay, chronic, updated_at)` refreshed by the nightly pipeline — serving is an indexed point lookup (O(1)), not a scan; (c) baselines versioned + stamped (F26). Expected: 945 ms → <25 ms.
- **Verify:** benchmark before/after table in `metrics.json`; test asserts zero full-table scans in journey path (query log assertion).

### F32 · Board N+1: 50 trains × (snapshot query + predict) sequentially = 780 ms
- **Severity:** HIGH · **Evidence:** Audit §7.2 board_routes.py:123-128.
- **Advanced fix — vectorized batch board:** one SQL pass with window functions assembling all per-train states → in-memory TrackGraph batch feature build → **single vectorized predict** (`lgbm.predict(X)` on the 50×25 matrix; GRU batch forward) → conformal + clamp vectorized → snapshot cache (F18). Latency becomes O(batch) ≈ 10–20 ms; also *is* the scalability proof for R4 — the same code path serves 10,000 trains.
- **Verify:** board p95 < 100 ms at 50 trains; same endpoint benchmarked at N=1,000 and N=10,000 synthetic trains — publish the scaling curve.

### F33 · Event-loop blocking risk: async endpoints + sync SQLite unverified
- **Severity:** MED (unverified) · **Evidence:** Audit §3.2 lifespan/async claims; no concurrency check performed.
- **Advanced fix:** audit each route: if `async def` + sync DB → wrap in `run_in_threadpool` (or keep routes plain `def` so FastAPI's threadpool applies); cap `torch` threads (F11); add a **k6/locust load profile** (50 concurrent, mixed endpoints) as a recurring benchmark, not a one-off.
- **Verify:** k6 p95 < 300 ms across mixed endpoints at 50 VUs; no endpoint regresses >20% under concurrency vs solo.

### F34 · 1.4 MB WebGL eye-candy on the landing path (three/r3f/drei/gsap/lenis) — main thread locked ~1.8 s on low-spec laptops
- **Severity:** MED · **Evidence:** Audit §7.4.
- **Advanced fix:** route-level code-splitting with `React.lazy`; `dynamic-import` the 3D scene only when `(hover|click)` on "Enter 3D" or on high-capability devices (`navigator.hardwareConcurrency`, `prefers-reduced-motion` honored); static poster fallback. Dashboard routes must not share a chunk with three.js.
- **Verify:** Lighthouse on landing: TTI < 2.5 s on "Slow 4G / 4× CPU"; dashboard bundle contains zero three.js bytes.

### F35 · No HTTP compression or cache headers on JSON APIs
- **Severity:** LOW · **Advanced fix:** GZip/Brotli middleware; `Cache-Control: private, max-age=5` + ETag (F18) on board; immutable long-cache for artifacts/assets.
- **Verify:** response headers present; board transfer size ≥60% smaller.

### F36 · Gzip of SQLite hot path fine, but WAL single-writer under collector + ops writes untested
- **Severity:** MED (unverified) · **Evidence:** Audit §3.3 WAL confirmed; concurrent write behavior untested.
- **Advanced fix:** single-writer queue in `db.py` (all mutations funnel through one writer task/thread); `busy_timeout`, `mmap_size`, `journal_size_limit` tuned; stress test collector-tick + ops mutations concurrently; document the Postgres+TimescaleDB migration trigger (write latency p95 > X ms) as a measured, not aspirational, threshold.
- **Verify:** stress test green (zero `SQLITE_BUSY` after queueing); trigger documented in runbook.

---

## DOMAIN G — FRONTEND STATE & WIRING

### F37 · TanStack Query installed, zero `useQuery` — state lives in `useState`/mockStore; no invalidation graph
- **Severity:** CRIT (UX math: mutations can never update views) · **Evidence:** Audit §5.4: zero `useQuery`/`invalidateQueries` repo-wide; §4.4 vs §5.4 contradiction inside the audit itself (dependency present ≠ used).
- **Advanced fix — derive invalidation from the resource graph, not per-page memory:**
  - Query-key factory: `qk.board(station)`, `qk.train(no)`, `qk.gantt(date)`, `qk.map(corridor)`.
  - Mutation→invalidation map in ONE module: `setin/out → [board, gantt, train(no), kpi]`; `assign → [gantt, board]`; `tsr.create → [map, board, train]`; ACK → optimistic update + rollback on error.
  - `staleTime: 10s, refetchInterval: 10–15s` on live views, `refetchOnWindowFocus: false`; SSE subscription (F18) replaces polling where available.
  - This is the difference between a page that *updates* and a page that *exists*.
- **Verify:** E2E: set-in → board shows ARRIVED ≤2 poll cycles; ACK flips advisory state optimistically; mutation map unit-tested (every mutation key has ≥1 invalidation).

### F38 · Data-freshness UI absent (ties to F22) — no age rendering anywhere
- **Advanced fix:** every live view binds the query's `dataUpdatedAt` → "updated 4s ago" chip; STALE > 30s turns amber; >120s turns red + OFFLINE banner. Zero new backend work; pure trust UI.
- **Verify:** manual freeze test on 3 views.

### F39 · 12 endpoint mismatches (`/infra` vs `/infrastructure`, POST vs GET, hyphen drift) — symptom of hand-written clients
- **Severity:** HIGH · **Evidence:** Audit §5.2 register (requestCrewRelief, liftTSR, startSOPRun, submitHandover, createBackup, generateAnnouncement, 4× infra prefix, ackCorridorHandoff, getDFCPrecedence).
- **Advanced fix — Kill the class, not the instances: OpenAPI codegen.** FastAPI's `openapi.json` → `openapi-typescript` (+ `openapi-fetch` or orval) generates the typed client; frontend imports generated methods only; CI step: regenerate → `git diff --exit-code` → any backend contract change that breaks the frontend **fails CI before humans meet it**. Hand-written URL strings are deleted from the codebase; the 12 mismatches become structurally impossible.
- **Verify:** codegen CI gate green; `grep -r "fetch(" web/src` returns only the generated client module; the 12 endpoints resolve via generated types.

### F40 · Hardcoded `http://localhost:8000` in mock/auth.ts:177; auth token handling unverified
- **Severity:** MED · **Advanced fix:** single `API_BASE` from env; auth storage audit — prefer **httpOnly Secure cookie + CSRF token**, or memory access token + refresh rotation; never localStorage for long-lived JWTs; 401 interceptor → single re-auth path, no silent mock auth.
- **Verify:** grep clean; auth flow E2E; expired-token test redirects once, not loops.

### F41 · Two auth stacks (mock/auth.ts vs backend JWT) — demo risk of showing the fake one
- **Advanced fix:** delete `web/src/mock/auth.ts` from the authenticated graph (same build-error aliasing trick as F21); demo mode uses real backend + seeded users (`sm_demo / viewer_demo`), which also demonstrates RBAC — a feature, not a mock.
- **Verify:** login as both roles; 403s visible where expected.

---

## DOMAIN H — MLOPS, RELIABILITY & SECURITY

### F42 · `requirements.txt` missing `torch`, `scipy`, `PyJWT`, `joblib` — Docker build fails; audit rated it MEDIUM
- **Severity:** CRIT (build) · **Advanced fix:** lock-file discipline (`uv lock` / `pip-compile` with hashes); CI matrix: `pip install -r requirements.txt` + `docker build` + `pytest` as merge gates — the class of "works on my machine" dies in CI, not in judging.
- **Verify:** clean-venv install + docker build green in CI.

### F43 · No retraining orchestration — `nightly_pipeline.py` exists but unwired; promotion is a one-off event
- **Advanced fix — scheduled brain loop:** nightly: materialize features (F26) → decay-weighted eval (F25) → shadow challenger vs champion on recent window (F15) → **CUSUM/ADWIN drift check (F29)** → report to `model_runs` table. Promotion only via the Wilcoxon + Winkler gate on *fresh* window; rollback trigger = champion residual CUSUM firing post-deploy. The brain becomes a loop with an audit trail, not a memory.
- **Verify:** `make nightly --dry-run` produces a full report; `model_runs` rows versioned with data window + git SHA.

### F44 · CQR calibration is one-time — staleness guaranteed
- **Advanced fix:** calibration job on schedule **and** on drift trigger (F29); ACI covers inter-job drift online (F03). Calibration artifacts versioned with window dates.
- **Verify:** recalibration job idempotent; coverage restored in fault-injection test.

### F45 · Flaky external-timeout test (OpenWA offline) — sync network in unit tests
- **Advanced fix:** stub the transport (respx/httpx MockTransport); the test asserts *escalation logic*, not DNS. Network tests move to a marked nightly integration suite.
- **Verify:** `pytest -m "not integration"` is deterministic (run 20×, zero flakes).

### F46 · Mutation idempotency — set-in/ACK retries can double-log
- **Advanced fix:** `Idempotency-Key` header (client-generated UUID) + unique constraint on `(key)` for mutating endpoints; replay returns the original result. Standard for flaky mobile/radio environments — which railway field ops are.
- **Verify:** double-POST test → one row, same response.

### F47 · Public kiosk/PIDS surface — rate limit + payload minimization unverified
- **Advanced fix:** per-IP token bucket (exists globally — confirm kiosk exempted/sized), response field whitelist (no internal IDs), `Cache-Control` public short TTL, and schema-snapshot contract test so the public API can't leak fields accidentally in future refactors.
- **Verify:** contract test green; kiosk payload < 20 KB.

### F48 · No property-based testing anywhere — the strongest bugs (c_seq class) evade example tests
- **Advanced fix:** Hypothesis suites: quantile ordering (F16), delay-monotonicity (F10), journey temporal monotonicity (**isotonic projection via PAVA across stations respecting dwell/run-time floors** — the ETA sequence along a route must satisfy `arr_{i+1} ≥ dep_i + run_min`; enforce with a pool-adjacent-violators projection weighted by inverse band width — mathematically principled, judge-visible), position-posterior normalization (F19), idempotency (F46).
- **Verify:** `pytest tests/test_properties.py` green; the c_seq regression class is now structurally covered.

### F49 · Secrets/config: mock secrets fine, but no env schema enforcement
- **Advanced fix:** pydantic-Settings with `extra="forbid"` — the app refuses to boot on unknown/missing env; `.env.example` generated from the schema (F02 pattern: one source of truth again).
- **Verify:** boot with a typo'd env var → hard fail with message.

### F50 · Repo hygiene (mechanical): `temp_resultshield/` (60 files), `graphify-out/` (138 files — audit missed it), duplicate 8.2 MB CSV, `Skeleton.tsx`, audit's own size contradictions (parquet 1.88 vs 1.1 MB; sim_ledger 2,201 vs 2,113) — the report needs a fact-check pass too
- **Advanced fix:** delete/gitignore the cruft; single `make factcheck` script emitting row counts/sizes to `control-room/facts.json` (the F02 pattern applied to the audit itself); dead-code sweep with `vulture` + `knip` quarterly, results filed as tasks.
- **Verify:** `make factcheck` committed; repo tree clean; audit discrepancies resolved with query outputs.

---

## 11. RETRAIN DECISION (final, flaw-linked)

| Trigger | Verdict |
|---|---|
| "Feels hardcoded / laggy / dumb" (F19, F21, F22, F31, F32, F37) | **NO retrain.** Plumbing. Retraining a disconnected brain yields a better disconnected brain. |
| Contaminated calibration (F01, F03) | **NO retrain — recalibrate now.** Purged splits + calibrate-the-ensemble + Mondrian/ACI. Hours, not days. |
| Champion benched (F15) | **NO retrain — serve it.** 5.82 vs 8.36 MAE already paid for. |
| Spatial/weather features starved (F23, F24) + context-blind/padded GRU (F07, F08) | **YES — exactly one retrain (Brain v3), after F07/F08/F23/F24 land.** 18 months, time-decay, rolling-origin, monotone constraints, per-source labels, Winkler+CRPS reporting. |
| After v3 | Future retrains are nightly-loop events (F43), never heroics. |

---

## 12. EXECUTION ORDER (dependency graph, session-sized)

```
S0 (day 1)   F42 → F01+F02 → F15 → F19/F20 → F21/F22/F38
S1 (perf)    F31 → F32/F18 → F33/F36 → F34/F35
S2 (wiring)  F39 → F37/F40/F41 → F46/F47
S3 (brain v3)F23/F24 → F07/F08/F09/F10/F12 → retrain → F03/F04 (Mondrian+ACI+NNLS) → F13
S4 (mlops)   F26/F27/F29 → F43/F44/F48/F49 → F28/F50
```
Every fix closes with its Verify command green + `08_SESSIONS.md` entry. No task without a verify command — same rule as the backlog.

---

## 13. META — FLAWS IN THE AUDIT ITSELF (so the report is trusted, not worshipped)

| # | Inconsistency | Resolution action |
|---|---|---|
| M1 | §4.4 "state managed via TanStack Query v5" vs §5.4 "zero useQuery" | Dependency installed ≠ used; F37 assumes §5.4 |
| M2 | Parquet size 1.88 MB (§1.6) vs 1.1 MB (§6.3); sim_ledger 2,201 (§1.6) vs 2,113 (§3.3) | `make factcheck` (F50) — one query output, no hand counts |
| M3 | §10.1 claims GRU serves live; §2.1 shows LightGBM tier | F15 resolves; report should have flagged, not reconciled silently |
| M4 | §1.6 lists held-out triple-use without flagging contamination | F01 — the report's most consequential omission |
| M5 | §8.1 renumbers R1–R20 differently from §0.3 R1–R7 | Cosmetic; fixed by generating registers from one schema (F02 pattern) |
| M6 | Dead-code sweep found 1 component across 56 .tsx + 120 .py; `graphify-out/` (138 files) unexamined | F50 mechanical sweep |
| M7 | Async/sync DB concurrency unexamined; CORS origin match unverified | F33/F47 VERIFY items |

**One-line verdict: the audit found the murder weapon (c_seq) and the mockStore smoking gun — but missed that its own hero metrics are contaminated, its own champion is benched, and its own congestion story has zero learned evidence. This file closes all three.**
