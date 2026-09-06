# PHASE 5 — FINAL RECOMMENDATIONS
**RailTwin-X · SIH 2026 PS 26028 · What to actually build.**

> **⚠️ UPDATED — post-commit `f371ecb` + working tree (2026-09-05).**
> The team shipped a major batch of demo surfaces: `api/demo_routes.py` (comparator, shock injection, cascade ripple), `web/src/pages/foresight/ForesightConsolePage.tsx`, `ComparatorPage`, `TimeMachinePage`, `RippleBoardPage`, `HonestModelCardPage`, plus `/v1/model/performance` in `api/routes.py:66`. Status of each recommendation is now tagged: **[SHIPPED]** / **[PARTIAL]** / **[STILL-OPEN]**. Kill-list reasons unchanged unless noted.

---

## 1. TOP 5 RANKED IDEAS

### #1 — HONESTY SCOREBOARD (C1 + C3 + C5 merged) — **[PARTIAL: backtest metrics shipped; live hash-chained ledger NOT surfaced]**
- **What shipped:** `HonestModelCardPage` (`/model-card`) + `ForesightConsolePage` banner display canonical MAE 10.72, coverage 80.64%, Winkler 57.94, horizon cards with honest 1h tie — all read dynamically from `metrics.json` via `/v1/model/performance` (`api/routes.py:66`). This is the **backtest scoreboard**: real, honest, and judge-ready.
- **What's still missing — THE critical gap:** the **live hash-chained ledger** endpoints `/ledger/scoreboard` and `/ledger/verify` (`api/routes.py:874-897`) still have **zero UI consumers** (verified: no references in `web/src/pages` or `components`). The backtest numbers prove the model; the ledger proves the *serving*. Those are different claims, and the ledger one is the world-first nobody else can make.
- **Remaining work (S, ~2–3h):** one `api.getLedgerScoreboard()` client function + one card/page. Show: "verified_arrivals_count N (LIVE, not backtest) · chain_integrity_verified ✓ · tip hash" and the `/ledger/verify` button re-hashing the chain.
- **Q&A defense (2 sentences):** "Every ETA we serve is sealed into a SHA-256 hash chain and auto-graded when the train actually arrives; the scoreboard is just that ledger aggregated. It lives in `engine/prediction_ledger.py` and is served at `/ledger/scoreboard` — the data is already there; we're only surfacing it."

### #2 — CAUSAL AUTOPSY WATERFALL (H1) — **[STILL-OPEN, smaller than before]**
- **One-liner:** A waterfall chart decomposing any train's total delay into exact cause buckets — each step labeled with evidence pointers, summing to the total exactly.
- **Status:** `AutopsyStrip` component exists and renders on `TrainDetailPage.tsx:212`; the `/v1/trains/{no}/why-late` route returns full causes with `integrity_checks`. What's missing is the **waterfall visual with the additivity proof line** ("Σ causes = total, always ✓" from `engine/attribution.py:724`).
- **Remaining work (S, ~2h):** upgrade `AutopsyStrip` to stepped waterfall (SVG or echarts — already installed) + render `integrity_checks.additivity_pass` as a visible checkmark. Small diff on an existing page.
- **Q&A defense:** "Every delay minute is attributed to an evidenced cause and the sum equals the total by construction — the additivity invariant is asserted in `engine/attribution.py:724`. We just render it."

### #3 — WHY WAS MY TRAIN LATE LAST TUESDAY? (F1) — **[STILL-OPEN, ~1h]**
- **Status:** backend accepts `run_date` today (`api/live_routes.py:196`); `TrainDetailPage` never sends one (verified: no `run_date`/date input in the page). The 300k-event archive stays invisible to passengers.
- **Remaining work (S, ~1h):** a date input on TrainDetailPage (or PassengerTrackerPage) that passes `run_date` to the existing queries. Cheapest item on the whole slate.
- **Q&A defense:** "We store point-in-time events for every station stop; the autopsy engine decomposes any historical run the same way it does live ones. Same engine, `engine/attribution.py`, just queried by date."

### #4 — RAKE DOOM DISCLOSURE (B2) — **[SHIPPED as "ripple board", reframe remaining work]**
- **What shipped:** `RippleBoardPage` (`/cascade`) + `/v1/cascade/ripple` (`api/demo_routes.py:352+`) now expose rake turnaround buffer deficits, `CRITICAL_DEFICIT`/`AT_RISK` statuses, projected outgoing delays, and ConnectionCustody hold advisories with net passenger-hours — including the "ADVISORY ONLY" jurisdiction framing, which is exactly right.
- **What's still missing:** the **passenger-facing doom card** — the "⚠️ 12556 DOOMED · NTES says ON TIME" contradiction framing on the passenger tracker. The controller DSS shipped; the passenger disclosure didn't. This was the part NTES *cannot* answer.
- **Remaining work (S, ~1–2h):** reuse `rake_turnarounds` from `/v1/cascade/ripple` (already in `web/src/lib/api.ts:920`); render a doom card on PassengerTrackerPage when `buffer_deficit_min > 15`.
- **Q&A defense:** "Same physical rake, turnaround constraint, simple arithmetic — the ripple endpoint computes it from the rake_links table. No competitor surfaces this because they don't model rake links."

### #5 — 6-HOUR CORRIDOR CONGESTION RADAR (D1) — **[STILL-OPEN, now the slate's medium]**
- **Status:** nothing network-level shipped in the new pages. `DaySpatialIndex` (`engine/spatial_context.py:152`) and its cache still feed only ML features.
- **Remaining work (M, 4h–1d):** aggregation endpoint rolling `DaySpatialIndex` forward with predicted delays per section + ECharts heatmap. Unchanged from original plan.
- **Q&A defense:** "The spatial index already computes minute-resolution positions for every train on the corridor; we project each train's predicted delay forward and aggregate per section. `engine/spatial_context.py`, plus the same ETA engine that beats the official method at long horizons."

---

## 2. THE BUILD SLATE (constraint: 3 smalls + 1 medium, OR 1 large + 1 small)

### UPDATED POST-COMMIT SLATE: **3 smalls + 1 medium** (B2's controller half already shipped)

| Slot | Idea | Effort | Post-commit status |
|---|---|---|---|
| **SMALL 1** | Live Ledger Scoreboard (C1 remainder) | S (~2–3h) | Wire `/ledger/scoreboard` + `/ledger/verify` into UI (endpoints exist, zero consumers). Highest-leverage remaining item — it's the claim no competitor can make. |
| **SMALL 2** | Causal Autopsy Waterfall (H1) | S (~2h) | Upgrade existing `AutopsyStrip` + render additivity checkmark. |
| **SMALL 3** | Passenger Doom Card (B2 remainder) | S (~1–2h) | Reuse live `/cascade/ripple` response (already in `web/src/lib/api.ts:920`); render on PassengerTrackerPage. |
| **MEDIUM** | 6-Hour Congestion Radar (D1) | M (4h–1d) | Unchanged — new aggregation endpoint + ECharts heatmap. |
| **stretch** | Historical why-late date input (F1) | S (~1h) | Route already accepts `run_date`; add a date field. |

**What the commit already banked (no longer costs slate slots):** comparator + shock injection (`ComparatorPage`, `/v1/demo/inject-event` — this partially delivers the B1 intervention *narrative* now), cascade ripple board with HOLD advisories and passenger-hours math (the controller half of B2/A5), Honest Model Card with dynamic `metrics.json` benchmarks (the backtest half of C1), and `TimeMachinePage` (D2 foresight storytelling).

**Demo arc (updated 5 beats):**
1. ForesightConsole → "here's the honest backtest: 51.7% better at 6h, and we publish the 1h tie" (shipped) →
2. Comparator → inject a 30-min signal-hold shock → "watch the cone widen live while B1/B2 stand still" (shipped) →
3. RippleBoard → "here's the doom and the hold advisory with passenger-hours math" (shipped) →
4. NEW: radar → "the network's next 6 hours, like rain radar" →
5. NEW: live ledger scoreboard → "**and here's the LIVE hash-chained ledger** — not backtest, every prediction sealed as served." ← the closing credibility beat is now the *differentiator between us and every other honest-looking dashboard*: we can prove serving-time integrity.

---

## 3. ONE SUPER-BIG STRATEGIC BET (optional) — **PARTIALLY SHIPPED, keep as narrative**

### "The Counterfactual Control Room" (What-If Intervention Lab, B1)
- **Status upgrade post-commit:** the comparator's **shock injection** (`/v1/demo/inject-event` → cone widens live, `ComparatorPage.tsx:45` + `ForesightConsolePage.tsx:61`) already demonstrates *system reaction to interventions*. What remains narrative-only is the **full counterfactual A/B** ("simulate WITH vs WITHOUT the hold, diff the ripple").
- **Exact slide/answer language (updated):**
  > "You just watched the cone react to an injected shock in real time. Under the hood, the same system runs a mechanistic SimPy simulation of the entire corridor (`engine/simulator.py`) — crossings, priority preemption, TSRs, rake inheritance — with exact per-minute causal accounting. The next release surfaces that as a full counterfactual lab: a controller drags a 10-minute hold at Kanpur and watches the six-hour ripple before deciding. The engine is what you saw today; the lab is a slider in front of it."
- If pressed "why not demo it now": "The simulator runs in `/v1/simulate/what-if` today — try it live. We froze scope on rubric-critical surfaces first."

---

## 4. THE KILL LIST (never relitigate)

| Idea | One-line reason |
|---|---|
| Generic LLM chatbot | Every team has one; only acceptable if 100% grounded in attribution — none here were. |
| H2 Confidence Cone animation | Pretty UX polish, no rubric line moved; subsumed by the band UI that exists. |
| C5 Self-Grade Ticker (standalone) | Subsumed by Honesty Scoreboard — same data, one surface. |
| A2 Confidence-Gated Alerts | Subsumed by scoreboard + regime badge; adds notification complexity for judges to question. |
| E1 Regime Badge (standalone) | Honest, but tiny; fold into scoreboard page as a chip if time remains. |
| D3 Position Certainty Heatmap | PARTIALLY-EXISTS risk (Bayesian tracking literature); weakest defensibility. |
| D2 Junction Pressure Forecast | Subsumed by congestion radar (same data, same page). |
| G2 Onward-Journey Cascade Planner | PARTIALLY-EXISTS in delay-management literature; A5-style HOLD advisory is the stronger cut and it's cut for scope. |
| B3 Optimal Hold Calculator | Controller-facing what-if; subsumed by the super-bet narrative. |
| F2 Corridor Historical Heatmap | Internal CRIS-style analytics; not passenger-defensible in 60s. |
| F3 Cause Frequency Leaderboard | Slide material, not code. |
| E3 Coverage-by-Regime | Subsumed by scoreboard (same ledger, different GROUP BY). |
| G1 Refund Eligibility Detector | Scored 100 BUT killed on rule-verification risk: IR refund/TDR rules change and a judge who knows them turns our crown feature into a liability. Revisit only if rules are verified in writing. |
| H4 Receipt Chain Visualization | Crypto block-explorer aesthetic is novel but the verify badge delivers the same rubric value in 10 lines. |
| H5 Drift Gauge | MLOps-internal; judges score passengers and controllers, not model dashboards. |
| W1–W5 Wild Cards | All subsumed by slate items. |
| Mobile app / PNR chat | Banned by PRD scope law; commodity tracker direction. |

---

## 5. BUILD ORDER (post-commit, dependencies first, demo-critical first)

1. **First — Live Ledger Scoreboard (C1 remainder, ~2–3h).** It is now the *only* unclaimed part of our #1 idea, it anchors the demo's closing beat, and the endpoints already exist (`api/routes.py:874`, `:886`). **Verify graded rows exist first** — see integration check: if `verified_arrivals_count` is 0 the scoreboard silently shows fallback defaults.
2. **Second — Causal Autopsy Waterfall (H1, ~2h).** Upgrade `AutopsyStrip`; render the additivity checkmark. Same data TrainDetailPage already polls.
3. **Third — Passenger Doom Card (B2 remainder, ~1–2h).** Pure frontend over the live ripple endpoint; data function already exists in `api.ts`.
4. **Fourth — 6-Hour Congestion Radar (D1, the medium).** Aggregation endpoint over `spatial_index_cache` + predicted delays; ECharts heatmap.
5. **Stretch — F1 historical date input (~1h).**
6. **Before ANY of that — fix the TimeMachinePage mock hashes (see integration check, ~30min).** A tamper-evidence demo cannot contain fabricated hashes; it's the one thing a sharp judge can catch and it poisons the entire D5 story.
7. **Last hour — rehearse the 5-beat arc** (backtest → shock cone → ripple/hold → radar → live ledger) against `scripts/demo_replay.py`.

---

## 6. INTEGRATION CHECK (updated post-commit `f371ecb` + working tree)

### 🔴 NEW CRITICAL FINDING — fabricated receipt hashes in TimeMachinePage
`web/src/pages/demo/TimeMachinePage.tsx:64-94` displays hardcoded mock strings presented as sealed receipts: `'3f7a18b...92e1 (Sealed at 22:45)'`, `'Block #1963 Graded · SHA-256 Chain Intact'`. These are **not real hashes**. If a judge asks "show me a real receipt" and the same screen says "SHA-256 Chain Intact" next to fabricated data, the entire tamper-evidence story (D5) — including the REAL ledger — becomes indefensible.
**Fix (~30min):** query the real ledger (`/ledger/scoreboard` gives the tip hash; the comparator already returns a real `ledger_receipt.receipt_hash` at `api/demo_routes.py:247` — `ForesightConsolePage.tsx:304` already displays it, correctly). Either make TimeMachinePage fetch real receipts for a historical train, or relabel the mock rows as "illustrative backtest timeline" and point live-hash claims only at the real surfaces.

### Ledger health (unchanged, still solid)
- `engine/prediction_ledger.py` chain is sound — commit `6ba9280` ("fix(ledger): serialize prediction ledger writes and repair hash chain fork") repaired a fork and serialized writes (`_LEDGER_LOCK`, `engine/prediction_ledger.py:21`). `tests/test_prediction_ledger.py` exists. Safe to build the scoreboard on.
- **Fallback-defaults trap (still open):** `prediction_ledger.py:214-216` returns hardcoded 80.6 / 5.88 / 27.8 when no rows are graded. Judges must see REAL graded numbers. Run `python scripts/demo_replay.py --fast` (or a night of live grading) before the demo and assert `verified_arrivals_count > 0`.
- **Comparator writes real receipts:** `/v1/demo/comparator` calls `ledger.record_prediction_receipt` per future station (`api/demo_routes.py:247`) — good: demo traffic seeds the live ledger. But note it records shocks-affected p50s; that's honest (shocks are real inputs) — just don't reset events mid-demo after showing a receipt.

### New routes status (verified against working tree)
- `/ledger/scoreboard` + `/ledger/verify` (`api/routes.py:874-897`): exist, **zero UI consumers** — this is SMALL 1.
- `/v1/model/performance` (`api/routes.py:66`): reads `metrics.json` dynamically; consumed by `HonestModelCardPage` + `ForesightConsolePage` — healthy, numbers not hardcoded in UI (`audit_note: "zero hardcoded strings"` — good, keep `metrics.json` current).
- `/v1/demo/comparator` + `/v1/demo/inject-event` + `/v1/demo/reset-events` (`api/demo_routes.py`): mounted (`api/main.py:52,241`), consumed by `ComparatorPage`/`ForesightConsolePage`. Note `_ACTIVE_SHOCKS` is **in-memory** (`api/demo_routes.py:30`) — shocks vanish on server restart and don't persist across workers; fine for demo, don't claim persistence.
- `/v1/cascade/ripple` (`api/demo_routes.py:352+`): consumes `RakeResolver`-equivalent logic + `ConnectionCustodyEngine` (`engine/ops.py:459`) — the two engines my Phase 0 flagged as dead capability #8 and #9 are now LIVE. Remaining gap is passenger-side doom card only.
- **Cone math in comparator is illustrative, not model-served:** `api/demo_routes.py:198-230` computes p10/p50/p90 from horizon tables + corridor friction + shock sums — it does NOT call `PredictorService`. Fine for demo honesty IF the page is framed as "the calibrated envelope responding to shocks"; do NOT claim these comparator numbers are the GRU/LightGBM ensemble's live output. If asked: "the comparator demonstrates the cone's *behavior*; the served ETAs in the dashboard are the full ensemble (`api/predictor.py`)."

### Prior checks (unchanged)
- **Why-late route:** `api/live_routes.py:196` accepts `run_date` — F1 is still a UI-only addition.
- **Rake links seed:** confirm `data/seeds/demo_scenario.json` includes a late incoming rake so the ripple board shows a CRITICAL_DEFICIT live.
- **Autopsy additivity:** invariant at `engine/attribution.py:724`; `integrity_checks` returned in every why-late payload — render the checkmark.
- **Spatial index:** radar endpoint must reuse `spatial_index_cache` (`engine/spatial_context.py:276`), not rebuild per request.
- **T82 dynamism proof** (`audit/T82_dynamism_proof.json`): PASS — now doubly relevant since the demo's shock-injection moment is the same claim; cite the transcript if challenged.
- **PRD scope law:** all remaining slate items surface EXISTING pipelines; no new pipeline, no 15th feature. Frame as "surfacing."

---

## SUMMARY TABLE (post-commit `f371ecb`)

| Rank | Idea | Status | Remaining effort | Rubric lines moved |
|---|---|---|---|---|
| 1 | Honesty Scoreboard (backtest half) | **SHIPPED** (`/model-card`, Foresight banner) | — | Novelty + Impact + UX |
| 1b | Honesty Scoreboard (live ledger half) | **OPEN** | S (~2–3h) — wire existing endpoints | Novelty + Impact (the world-first claim) |
| 2 | Causal Autopsy Waterfall | **PARTIAL** (strip exists, no waterfall/proof line) | S (~2h) | Impact + UX |
| 3 | Historical Why-Late Search | **OPEN** (backend ready) | S (~1h) | Impact + UX |
| 4 | Rake Doom (controller DSS) | **SHIPPED** (`RippleBoardPage`) | — | Impact + UX |
| 4b | Rake Doom (passenger card) | **OPEN** | S (~1–2h) | Novelty + Impact |
| 5 | 6-Hour Congestion Radar | **OPEN** | M (4h–1d) | Novelty + Impact + UX |
| — | Comparator + shock injection (B1-lite) | **SHIPPED** | — | Novelty + Wow |
| — | TimeMachine mock-hash fix | **URGENT FIX** | ~30min | Trust (blocks D5 story) |

---

*Updated: 2026-09-05 after commit `f371ecb` + working tree. Remaining build: ~1–1.5 days (1 urgent fix, 3 smalls, 1 medium, 1 stretch). All reuse existing engines.*
