# DEEP IMPLEMENTATION RESEARCH — Feature Specs, Wiring Maps & Data Verification
**Companion to `CLEANUP_AND_BUILD_PLAN.md`. Everything here was verified against the live codebase and `data/railtwin.db` on 2026-09-05.**

---

## 0. GROUND TRUTH — The Real Corridor (from `route_stations` + `sections` tables)

This is the single most important finding. **The real DB corridor is:**

```
NDLS(0km) → GZB(65) → ALJN(130) → TDL(195) → ETW(260) → CNB(325) → ON(390) → LKO(440)
```

- **8 stops, 440 km, terminus = LKO (Lucknow Charbagh)** — verified via `route_stations WHERE train_no='12301'`.
- `sections` table has 14 rows (7 bidirectional pairs); only `CNB–ON` and `ON–CNB` are `single_line=1`.
- **Stations that do NOT exist in DB:** `FTP` (Fatehpur — 0 rows), and the radar's km values for PRYJ(632)/MZP(721)/DDU(785) don't match any route.
- **DB volumes (live):** 151 timetabled trains · 33,601 station_events across 29 run-days (2026-01-15 → 2026-09-02) · 14 rake_links · 611 live_positions rows · 196 live_delay_ledger rows · **2,343 ledger blocks, 432 graded** · weather_hourly: only 1 row (⚠️ see §6).

**Consequence:** the new `/v1/corridor/congestion-radar` hardcodes a **fictional 785km NDLS–DDU corridor** (`api/demo_routes.py:660-680`) that does not match this database. Judges cross-checking radar section names against the live map or train journeys will see two different networks. **The radar must be rebuilt against the real 8-stop corridor (or the DB re-seeded — but rebuilding the endpoint is 1h, re-seeding data is risky).**

---

## 1. FEATURE A1 — LIVE LEDGER SCOREBOARD (finish the wiring)

### Current state (verified)
| Layer | Status | Evidence |
|---|---|---|
| Engine | ✅ done | `engine/prediction_ledger.py:187` — `get_calibration_scoreboard()`; `verify_chain_integrity()` at `:159` |
| API | ✅ done | `api/routes.py:874` `/ledger/scoreboard`; `:886` `/ledger/verify` |
| Client fn | ✅ done | `web/src/lib/api.ts:935` `getLedgerScoreboard()`, `:952` `verifyLedgerChain()` |
| Page | 🟡 **HALF-WIRED** | `HonestModelCardPage.tsx:21-49` loads both and has a verify button — BUT see landmines |

### 🟡 Landmines found in the current wiring

1. **Fabricated fallback scoreboard** (`api.ts:936-951`): if the backend call fails, the client silently returns a **fake scoreboard with hardcoded numbers** (`total_served_predictions: 2331`, `verified_arrivals_count: 430`, `chain_tip_hash: '6ffbe6ab...'`). A judge clicking during a backend hiccup sees **plausible fake numbers next to "chain verified"** — the same R2/R3 disease. **Fix: remove the fallback fn entirely** (or return `status: 'OFFLINE'` and show an error state). The real DB today has 2,343 blocks / 432 graded — the fake one says 2331/430. Close enough to be indistinguishable. That's the danger.
2. **Verify button latency**: `verify_chain_integrity()` walks ALL 2,343 rows and re-hashes each — fine at this scale (<1s), but it runs **on every scoreboard read too** (`get_calibration_scoreboard` calls it internally, `prediction_ledger.py:189`). At 50k+ blocks this doubles page latency. Fine for judging; note for Q&A.
3. **Ledger seeding flow**: `live_tracker.tick()` auto-grades on arrival (`live_tracker.py:322`), and BOTH the comparator (`demo_routes.py:247`) and time-machine (`demo_routes.py:566`) record receipts per call. **Every demo click grows the ledger live — this is the demo moment itself.** Before the demo: run `python scripts/demo_replay.py --fast` so `verified_arrivals_count` > 0.

### Remaining work (S, ~1–2h)
1. `web/src/lib/api.ts:936` — delete the mock fallback from `getLedgerScoreboard`; same for `verifyLedgerChain` (`:952`).
2. `HonestModelCardPage.tsx` — replace `|| 2331` / `|| 430` hardcode-defaults in JSX (`:278,287`) with honest loading/empty states (they currently mask a failed fetch with the same fake numbers).
3. Add a **"blocks growing live" counter**: poll `total_served_predictions` every 10s during demo; the number ticks up as you click around. Cheap (one `refetchInterval`) and is the strongest single visual for D5.
4. Optional: surface the tip-hash on `ForesightConsolePage` next to the existing D5 badge (`:304` already shows comparator receipt hash — pattern exists).

### API contract (already live — for reference)
```
GET /v1/ledger/scoreboard → { scoreboard: {
  total_served_predictions, verified_arrivals_count, empirical_80pct_coverage,
  target_coverage_pct: 80.0, mean_absolute_error_min, mean_winkler_score,
  chain_integrity_verified, total_blocks_verified, chain_tip_hash, as_of } }
GET /v1/ledger/verify → { chain_integrity_verified, total_blocks_verified, broken_at_block_id }
```

---

## 2. FEATURE A2 — AUTOPSY WATERFALL (upgrade `AutopsyStrip`)

### Current state (verified)
- `AutopsyStrip` (`web/src/components/aspect/AutopsyStrip.tsx`) already: renders **proportional horizontal segments** (widths = `sumAbsMinutes`, `:117`), color-codes 7 cause categories (`:48-94`), shows the **integrity badge with additivity PASS/FAIL tooltip** (`:155-175`), and accepts `integrityChecks` — already passed by `TrainDetailPage.tsx:219`. The "EVIDENCE VERIFIED" badge exists.

### So what's actually missing?
Only the **waterfall form** (cumulative stepped bars from 0 → total, with negative RECOVERY segments stepping down) and the visible **"Σ causes = total delay. Exact."** caption. Current strip is proportional slices — good, but a judge can't see the running-sum property that makes D3 special.

### Implementation (S, ~2h) — one file, no backend work
In `AutopsyStrip.tsx`:
1. Compute cumulative offsets: `let cum = 0; const steps = segments.map(s => { const start = cum; cum += s.minutes; return {...s, start, end: cum}; })`.
2. Render as stacked absolute-positioned divs on a single baseline track (each step's `left = start/total * 100%`, `width = minutes/total * 100%`, negative minutes render below the baseline). Pure CSS — no echarts needed at this size.
3. Below the track, one line: `Σ {cum} min = total {totalDelayMin} min · {additivity_pass ? '✓ EXACT' : '✗ MISMATCH'}` (value already arrives via `integrityChecks.additivity_pass` from `/why-late`).
4. Keep the existing slice view as a fallback prop (`variant="strip" | "waterfall"`) so `TrainDetailPage` chooses waterfall.

### Data source (already live)
```
GET /v1/trains/{no}/why-late?run_date=YYYY-MM-DD
→ { causes: [{cause_code/event_type, minutes/attributed_min, cause, station_code, percentage...}],
    total_delay_minutes, is_exact_accounting, integrity_checks: {additivity_pass, ...}, narrative }
```
`api.ts:506 getTrainAutopsy(id, runDate?)` — **runDate param already plumbed but never sent by any page** (that's A4).

---

## 3. FEATURE A3 — PASSENGER DOOM CARD (on PassengerTrackerPage)

### Current state (verified)
- Controller half shipped: `/v1/cascade/ripple` (`api/demo_routes.py:352+`) returns `rake_turnarounds[]` with `buffer_deficit_min`, `projected_outgoing_delay_min`, `status ∈ {HEALTHY, AT_RISK, CRITICAL_DEFICIT}`.
- Client fn exists: `api.ts:920 getCascadeRipple(stationCode)` — consumed ONLY by `RippleBoardPage`.
- `PassengerTrackerPage.tsx` (938 lines) already queries `getPassengerSnapshot(train, stop, pnr)` (`api.ts:597`) and subscribes to SSE `getPassengerStreamUrl` (`api.ts:605`).

### Implementation (S, ~1–2h) — frontend only
1. In `PassengerTrackerPage`, add a `useQuery` on `api.getCascadeRipple(lastRakeStation || 'CNB')` (refetch 60s — it's an advisory, not telemetry).
2. Filter `rake_turnarounds` to rows where `outgoing_train === activeTrainNo && buffer_deficit_min > 15`.
3. Render a doom card above the journey strip:
   - `⚠️ DOOMED — incoming rake #{incoming_train} arrived +{incoming_delay_min}m late`
   - `Turnaround: {scheduled_turnaround_min}m scheduled · only {remaining_buffer_min}m left · projected departure +{projected_outgoing_delay_min}m`
   - `NTES says: "ON TIME" · we said this {hours} before departure`
4. **Data honesty note for Q&A:** `cascade/ripple` computes deficit vs a 90-min minimum buffer (`demo_routes.py:399`) — a policy constant, defensible as "minimum cleaning + inspection + rake prep standard." Say that, don't say "ML."

### Backend gap check
None — the route takes `station_code` and returns all links; filter client-side. If you want per-train lookup: `?station_code=` of the **turnaround station**, not the train's current station. The 14 rake_links live across stations; for the demo pick the link whose station has the most links (CNB).

---

## 4. FEATURE A4 — HISTORICAL WHY-LATE DATE INPUT

### Current state (verified)
- Backend: **fully ready** — `api/live_routes.py:196` `GET /v1/trains/{no}/why-late?run_date=` → `attribution.get_why_late_summary(train, run_date)` (`engine/attribution.py:477`).
- Client: `api.ts:506 getTrainAutopsy(id, runDate?)` — **accepts the param, never called with it**.
- Data: **29 distinct run-dates** (2026-01-15 → 2026-09-02) in `station_events`. A date picker with real content exists for every date in that range.

### Implementation (S, ~1h)
1. `TrainDetailPage.tsx`: add a `<input type="date" min="2026-01-15" max="2026-09-02">` next to the autopsy section title (HTML native date picker — matches the "native platform first" rule; no library).
2. Wire to the existing query: `queryKeys.trainAutopsy` becomes `['train', trainNo, 'autopsy', runDate]` and `api.getTrainAutopsy(trainNo, runDate)`.
3. When `runDate ≠ today`, show a "HISTORICAL AUTOPSY" chip on the waterfall so it's visually distinct from live.
4. Empty-date handling: `get_why_late_summary` falls back to `decompose_train_delay` which returns `integrity_status: 'UNVERIFIED'` when no events exist (`attribution.py:203-210`) — render that honestly ("no recorded events for this date"), never a zero-delay default. The engine already refuses to fake it; the UI must too.

### The demo line
"The archive holds 33,601 point-in-time events across 29 run-days. Pick any date — last Tuesday, January 15th — same autopsy engine, same exact-sum proof."

---

## 5. FEATURE A5 — CONGESTION RADAR (fix what shipped, then build UI)

### ⚠️ The shipped backend has 4 real defects (verified)

| # | Defect | Evidence | Fix |
|---|---|---|---|
| 1 | **Fictional corridor** — hardcodes 9 sections NDLS→DDU 785km with km values that match nothing in DB; `FTP` doesn't exist; PRYJ/MZP/DDU aren't on any route | `api/demo_routes.py:660-680` vs `route_stations` (8 stops to LKO 440km) and `sections` table | Read sections from the `sections` table (14 rows, direction-filtered = 7) and derive km from `route_stations.distance_km` |
| 2 | **Dead code branch** — `if tracker and hasattr(tracker, 'positions')` (`demo_routes.py:692`): `LivePositionTracker` has **no `positions` attribute** (verified via AST over `engine/live_tracker.py`; the real caches are `_position_cache`, `_routes_cache`). This branch NEVER runs; only the `live_positions` DB fallback feeds the radar | `demo_routes.py:692-703` | Use `tracker.get_all_live_positions()` (the public API, `live_tracker.py:593`) or keep the DB path and delete the dead branch |
| 3 | **Fabricated counts** — when a section has 0 projected trains, it *invents* `base_count = max(2, capacity*0.45 + ...)` and synthetic delay (`demo_routes.py:716-718`) — the radar can never show an empty section | `demo_routes.py:716` | Show real 0. An empty corridor is honest; a phantom 45% baseline is fabrication |
| 4 | **`active_monitored_trains: max(len(live_trains), 14)`** — forces at least 14 even if 6 are running | `demo_routes.py:781` | Report the real count |

**Why these matter:** this endpoint is exactly the kind of surface a railway judge probes — "how many trains are actually on CNB–ON right now?" If the radar can't ever say zero, it's not a decision tool, it's a screensaver. Fix 1–4 (≈2h, one file) **before** building the UI.

### Rebuild spec (backend, ~2h)
```python
# /v1/corridor/congestion-radar — honest version
sections = SELECT from sections WHERE from_km < to_km ORDER BY distance  # 7 directional
#   km anchors from route_stations (train 12301): NDLS 0, GZB 65, ALJN 130, TDL 195,
#   ETW 260, CNB 325, ON 390, LKO 440
positions = tracker.get_all_live_positions()        # real public API
# project each train: km_now + speed*(Δt/60), clamp to 440, mark TERMINATED beyond LKO
# count per section per horizon; occupancy = count / (length_km / MIN_HEADWAY_KM=2.0)  # same constant as spatial_context.py:22
# level thresholds: CRITICAL ≥85, HIGH ≥70, MODERATE ≥45, LOW else
# NO synthetic baseline; empty section = 0 trains, LOW
```
`MIN_HEADWAY_KM = 2.0` and the capacity formula already exist at `engine/spatial_context.py:22-23` — reuse the constant so radar and ML features share one definition of "capacity" (a Q&A consistency win: "the radar's occupancy denominator is the same 2-minute-headway capacity the model trains on").

### UI spec (~2–3h, one new page or a tab on ForesightConsole)
- Grid: **7 sections × 5 horizons (T+0/1/2/4/6h)** heatmap. Sections on the y-axis as the real names (Delhi–Ghaziabad … Unnao–Lucknow), horizons on x.
- Cell color by congestion_level; cell text = occupancy %; hover = `active_trains / capacity, total_delay_min`.
- A horizon time-slider that highlights one column (the "rain radar scrub").
- Below: `highest_chokepoints` cards with the recommended action (already in the response shape — keep).
- Client fn `api.ts:962 getCorridorCongestionRadar()` exists with a mock fallback — **delete the fallback** (same rule as A1; the mock returns `radar: []` which is safe but the pattern invites fabrication later).
- ECharts is already installed (`echarts-for-react` in node_modules) — but for 7×5 a CSS grid of colored cells is simpler and matches the terminal aesthetic. Ponytail rule: CSS first.

### The single-line correction that must ship with it
Route alias says "NCR Mainline (NDLS – DDU 785km)" (`demo_routes.py:778`) — replace with the real corridor label "NDLS – LKO via CNB (440 km)" or read it from config. Two corridors on screen = instant credibility loss.

---

## 6. NEW FINDINGS FROM THIS DEEP PASS (not in the earlier plan)

| Finding | Severity | Action |
|---|---|---|
| **R3 is now FIXED** — TimeMachinePage fetches real `/v1/demo/time-machine` data; the old hardcoded hashes (`'3f7a18b...'`) are gone; remaining strings are loading placeholders labeled "Sealing block..." | ✅ resolved | None. Verify once more before demo (grep `'3f7a18b\|9a4c82e\|Block #1963` in web/src → expect 0 hits) |
| **A1 is half-shipped** — HonestModelCardPage consumes the ledger + has a verify button, BUT both client fns carry **fabricated fallback scoreboards** and JSX `|| 2331` defaults mask fetch failures with fake numbers | 🔴 new landmine (same class as old R2) | Remove fallbacks + hardcode-defaults (§1) |
| **Time-machine backend is genuinely good** — real ML predictions per checkpoint (`predictor.predict_train_eta` at `demo_routes.py:520`), real receipts into the ledger, real truth-stage grading against `station_events` | 🟢 | Nothing. This is demo-grade honest. One caution: it defaults `run_date="2026-09-02"` — ensure that date has events in the demo DB (it's the max run_date, good) |
| **`weather_hourly` has only 1 row** — fog/rain features and any weather-linked story have essentially no hourly data behind them | 🟡 | Either backfill via `scripts/weather_backfill.py` for the 29 run-days, or drop weather claims from the demo script. Check `weather` (daily) table separately — daily may be populated even if hourly isn't |
| **Radar corridor fiction** (§5 defect 1) | 🔴 | Rebuild against real sections (§5) |
| **29 run-days, not "300k events"** — the archive is 33,601 events over 29 days | 🟡 | Update demo script phrasing: "33,600 point-in-time events across 29 run-days" (still strong; honest beats inflated). The 300k figure in older docs/reports should be corrected everywhere it's spoken aloud |

---

## 7. CONSOLIDATED WIRING MAP (who calls what — post-research)

```
BACKEND (exists)                          CLIENT FN (api.ts)              UI CONSUMER              ACTION
/v1/ledger/scoreboard (:874)         → getLedgerScoreboard (:935)   → HonestModelCardPage 🟡   strip fake fallback
/v1/ledger/verify (:886)             → verifyLedgerChain (:952)     → HonestModelCardPage 🟡   strip fake fallback
/v1/model/performance (:66)          → getModelPerformance (:901)   → ModelCard+Foresight ✅   none
/v1/demo/comparator                  → getDemoComparator (:904)     → Comparator+Foresight ✅   none
/v1/demo/inject-event /reset         → injectShockEvent/reset (:910)→ Comparator ✅            none (in-memory OK)
/v1/demo/time-machine (:457)         → getTimeMachineData (:929)    → TimeMachinePage ✅       none (real now)
/v1/cascade/ripple (:352)            → getCascadeRipple (:920)      → RippleBoard ✅ / doom 🟡  add PassengerTracker card
/v1/corridor/congestion-radar (:646) → getCorridorCongestionRadar  → ❌ NO PAGE              fix backend, build UI
/v1/trains/{no}/why-late?run_date    → getTrainAutopsy (:506)       → TrainDetail 🟡 (no date) date input + waterfall
/api/workforce/crew/breaches (:320)  → ❌ client calls /v1/crew/alerts (nonexistent)          → fix path or drop (R10)
/api/audit/verify-integrity (:106)   → verifyAuditIntegrity (:758)  → AuditPage 🟡 (fake root hash fallback) → use real
```

---

## 8. REVISED EFFORT TABLE (supersedes the ADD side of CLEANUP_AND_BUILD_PLAN)

| Item | What changed after deep research | New effort |
|---|---|---|
| A1 Ledger scoreboard | Was "build UI from scratch" → now "strip 2 fake fallbacks + add live counter" | **~1–2h (down from 2–3h)** |
| A2 Autopsy waterfall | `AutopsyStrip` already renders segments + integrity badge → only waterfall form + Σ caption needed | **~2h (unchanged)** |
| A3 Doom card | Client fn + endpoint proven; pure page work | **~1–2h (unchanged)** |
| A4 Date input | Param plumbed end-to-end except the UI | **~1h (unchanged)** |
| A5 Radar | Was "build endpoint + UI" → now "REPAIR endpoint (4 defects) + UI" | **~4–5h (up from 4h)** — do not skip the repair |
| NEW: weather_hourly backfill | 1 row behind fog stories | `python scripts/weather_backfill.py` ~30min, or cut weather claims |
| NEW: corridor-label fix | "785km DDU" strings on 3 surfaces | ~15min |
| Total honest remaining | | **~1.5–2 days** |

### Revised order
1. **Hour 1:** A1 fake-fallback strip (🔴 credibility) + R1 secrets if not done
2. **Hour 2–3:** A4 date input → A2 waterfall (same page, do together)
3. **Hour 4–5:** A3 doom card
4. **Day 2 AM:** A5 radar repair (defects 1–4) then UI
5. **Day 2 PM:** weather backfill decision, corridor-label fix, R4–R7 removals, rehearsal
6. **Demo script line to rehearse:** "33,600 events, 29 run-days, 2,343 sealed predictions, 432 graded live — the number on screen is growing as we speak."

---

## 9. Q&A DEFENSE CARD (one line each, per feature)

- **Scoreboard:** "Every served ETA is SHA-256-sealed and auto-graded on arrival — `engine/prediction_ledger.py`; the scoreboard is that ledger aggregated, served at `/ledger/scoreboard`."
- **Waterfall:** "Cause minutes sum exactly to total by an asserted invariant — `engine/attribution.py:724`; the checkmark renders the same `integrity_checks` the API returns."
- **Doom card:** "Same physical rake, turnaround arithmetic from the `rake_links` table — computed at `/v1/cascade/ripple`; we surface it to passengers, NTES doesn't model rakes."
- **Date search:** "Point-in-time `station_events` archive; the identical autopsy engine runs on any historical `run_date` — `engine/attribution.py:477`."
- **Radar:** "Occupancy = projected trains per section over the same 2-minute-headway capacity the model trains on — `engine/spatial_context.py:22`; projections use live positions and speed from the tracker."
- **If asked about the old mock numbers:** "We removed every fabricated fallback; a failed fetch now shows an error state, never plausible numbers." *(only true once §1/§5 fixes land — don't say it before)*

---

*Research basis: AST verification of `LivePositionTracker` attributes; direct SQL against `data/railtwin.db` (sections, route_stations, stations, station_events, live_positions, live_delay_ledger, eta_prediction_ledger, weather_hourly, rake_links); line-level reads of `api/demo_routes.py`, `api/routes.py`, `api/live_routes.py`, `web/src/lib/api.ts`, all new pages, `AutopsyStrip`, `PassengerTrackerPage`, `TrainDetailPage`, `queryKeys.ts`, `fetchBackend` contract.*
