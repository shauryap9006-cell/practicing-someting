# PHASE 4 — SCORING & RANKING
**1–5 per dimension. Composite = (Novelty × Wow × Rubric) / (Effort weight).**

> **RE-SCORED 2026-09-05 after commit `f371ecb`.** Shipped items drop off the active list (effort spent); remaining items re-ranked by *remaining* effort. Two new entries: the TimeMachine mock-hash fix (a discovered liability, not an idea — scored on urgency) and the live-ledger remainder, which is now the highest-leverage open item because its backend is 100% done.

---

## Scoring Scale

- **NOVELTY** — post-validation uniqueness (1–5)
- **WOW** — jaw-drop factor of 60s demo (1–5)
- **RUBRIC** — which rubric lines moved (Novelty 15 / Impact 20 / UX 15) — 1–5
- **EFFORT** — S (<4h) / M (4h–1d) / L (1–2d) / XL (>2d or new data) — encoded as weight 1/2/4/8
- **DEFENSIBLE** — can team explain in 2 sentences + 1 file ref? — 1–5
- **RISK** — if unfinished: safe (1) / dangerous (5)

---

## SCORING TABLE

| ID | Idea | Nov | Wow | Rubric | Effort | Def | Risk | Composite |
|---|---|---|---|---|---|---|---|---|
| **C1** | **Honesty Scoreboard** | 5 | 5 | 5 (N+I+U) | S (1) — wire existing endpoint + 1 page | 5 | 1 (small surface, low risk) | **(5×5×5)/1 = 125** |
| **B1** | **What-If Intervention Lab** | 5 | 5 | 5 | L (4) — UI + sim comparison | 4 | 3 (medium surface) | (5×5×5)/4 = 31 |
| **H1** | **Causal Autopsy Waterfall** | 5 | 5 | 4 | S (1) — render existing AutopsyResult | 5 | 1 | (5×5×4)/1 = 100 |
| **D1** | **6-Hour Corridor Congestion Radar** | 5 | 5 | 5 | M (2) — extend spatial index forward 6h | 4 | 3 | (5×5×5)/2 = 62 |
| **G1** | **Refund Eligibility Detector** | 5 | 4 | 5 (I+U) | S (1) — query ledger, apply IR threshold | 5 | 1 | (5×4×5)/1 = 100 |
| **C2** | Per-Cause-Type Accuracy | 5 | 5 | 5 | S (1) — groupBy ledger by cause | 5 | 1 | 125 |
| **H3** | Cascade Ripple Animation | 5 | 5 | 4 | M (2) — animation layer | 4 | 2 | 50 |
| **A1** | Leave-Now Advisory | 4 | 4 | 3 | S (1) | 5 | 1 | 48 |
| **E1** | Model Regime Badge | 5 | 4 | 4 | S (1) | 5 | 1 | 80 |
| **F1** | Why Was My Train Late Last Tuesday? | 5 | 5 | 4 | S (1) — query 300k events | 5 | 1 | 100 |
| **B2** | Rake Doom Disclosure | 5 | 4 | 4 | S (1) — surface existing rake_status | 5 | 1 | 80 |
| **A5** | Connection Risk + HOLD | 4 | 5 | 5 | S (1) — surface existing engine | 4 | 1 | 80 |
| **H4** | Prediction Receipt Chain Visualization | 5 | 4 | 3 | M (2) | 5 | 2 | 60 |
| **H2** | Confidence Cone | 5 | 5 | 3 | M (2) — animation layer | 4 | 2 | 37 |
| **D3** | Position Certainty Heatmap | 3 | 4 | 3 | M (2) | 4 | 3 | 18 |
| **C3** | Tamper-Evident Audit Receipt | 5 | 3 | 4 | S (1) — receipt hash already returned | 5 | 1 | 60 |
| **C4** | Prediction Receipt Browser | 5 | 3 | 3 | S (1) | 5 | 1 | 45 |
| **C5** | Real-Time Self-Grade Ticker | 5 | 4 | 3 | S (1) | 5 | 1 | 60 |
| **A3** | Best/Worst/Likely Schedule | 4 | 4 | 3 | S (1) — already in API | 5 | 1 | 48 |
| **H5** | Drift Indicator Gauge | 4 | 4 | 3 | S (1) | 5 | 1 | 48 |
| **A2** | Confidence-Gated Alert | 4 | 3 | 3 | S (1) | 5 | 1 | 36 |
| **E3** | Coverage-By-Regime Decomposition | 5 | 4 | 3 | M (2) — join ledger + weather | 5 | 1 | 30 |
| **A4** | Punctuality Card | 4 | 4 | 3 | S (1) | 5 | 1 | 48 |
| **D2** | Junction Pressure Forecast | 3 | 4 | 3 | M (2) | 4 | 3 | 18 |
| **F2** | Corridor Historical Heatmap | 3 | 4 | 3 | M (2) | 4 | 2 | 18 |
| **F3** | Cause Frequency Leaderboard | 5 | 3 | 3 | S (1) | 5 | 1 | 45 |
| **B3** | Optimal Hold Calculator | 4 | 5 | 4 | M (2) | 4 | 2 | 40 |
| **G2** | Onward-Journey Cascade Planner | 4 | 4 | 4 | M (2) | 4 | 2 | 32 |
| **W1–W5** | Wild Cards | 4 | 3 | 3 | varies | varies | varies | <30 |

---

## RANKED SHORTLIST — POST-COMMIT REMAINING WORK (top by composite of what's left)

| Rank | ID | Idea | Composite | Remaining Effort | Status |
|---|---|---|---|---|---|
| — | **FIX** | TimeMachine mock-hash remediation | n/a (liability) | **~30min — DO FIRST** | 🔴 URGENT |
| 1 | **C1b** | Live Ledger Scoreboard (UI for existing endpoints) | 125 | S (~2–3h) | OPEN |
| 2 | **H1** | Causal Autopsy Waterfall (strip upgrade + proof line) | 100 | S (~2h) | PARTIAL |
| 3 | **B2b** | Passenger Doom Card (reuse live ripple data) | 80 | S (~1–2h) | OPEN |
| 4 | **D1** | 6-Hour Corridor Congestion Radar | 62 | M (4h–1d) | OPEN |
| 5 | **F1** | Historical why-late date input | 100 | S (~1h) | OPEN (stretch) |
| 6 | **C2** | Per-Cause-Type Accuracy | 125 | S (~3h) | OPEN (cut for scope — C1b first) |
| 7 | **E1** | Model Regime Badge | 80 | S | OPEN (fold into scoreboard page) |
| 8 | **H3** | Cascade Ripple Animation | 50 | M | OPEN (cut — ripple board covers it) |

### BANKED (shipped in `f371ecb` — no longer on the slate)
- **C1a backtest scoreboard** — `/model-card` + Foresight banner (dynamic from `metrics.json`)
- **A5 connection HOLD advisories** — ripple board with passenger-hours math
- **B2a rake doom controller DSS** — turnaround buffer deficits, CRITICAL_DEFICIT
- **B1-lite shock injection** — comparator cone reaction vs frozen baselines
- **D2-lite honest horizon cards** — 1h tie / −36.3% 3h / −51.7% 6h

---

## KILL FILTER (one-line reasons)

| Idea | Verdict | Reason |
|---|---|---|
| All PARTIALLY-EXISTS (D2, D3, F2, G2, A5, B3) | **HOLD** | Keep A5 (Custody HOLD) because HDTI value is high; demote others. Verify D3 with domain expert before committing. |
| H2 Confidence Cone | **KILL** | Animation-only novelty; no rubric mover beyond UX. |
| C5 Real-Time Ticker | **KILL** | Subsumed by C1 (Honesty Scoreboard shows the same numbers statically). |
| A2 Confidence-Gated Alert | **KILL** | Subsumed by A1 (leave-now) and E1 (regime badge). |
| W1–W5 Wild Cards | **KILL** | Subsumed by ranked ideas (W1 = part of H1, W3 = part of C3). |
| F2, F3 | **HOLD for narrative** | Use as slide material, not code. |
| E3 Coverage-By-Regime | **KILL** | Subsumed by C1 (same data, different cut). |
| D2 Junction Pressure | **KILL** | Subsumed by D1 (radar covers junctions). |

---

## KILL FILTER AUTO-CHECK ON ANTI-PATTERNS

- **Generic chatbot:** not in this list ✓
- **"Blockchain":** we say "hash-chained audit ledger" ✓
- **Gamification:** not in this list ✓
- **Data we don't have:** all reuse existing repo data ✓
- **Not 60s demoable:** all are ✓
- **Tracker-app features:** none — every idea is a differentiator ✓

---

*Generated: Phase 4 — Scoring. Top 10 ranked, kill filter applied. C1, C2, G1, H1, F1 are the highest-leverage small ideas.*
