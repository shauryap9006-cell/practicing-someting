# CLEANUP & BUILD PLAN — Post-Audit Decisions
**RailTwin-X · SIH 2026 PS 26028 · Full-project audit: 29 backend route files (159 endpoints), ~30 frontend pages, 2,544-line mock system, 60+ scripts, 68 test files, ML lineage, repo hygiene.**

> Companion to `FINAL_RECOMMENDATIONS.md` and **`DEEP_RESEARCH_IMPLEMENTATION.md`** (the per-feature wiring specs — read that before building anything on the ADD side; it corrected several items here).
> Frame: judging day is near, PRD is scope-frozen, and only D1–D5 differentiators win rubric points. Anything that doesn't move the rubric or actively risks the demo gets cut.

> **⚠️ SECOND UPDATE (deep-research pass, same day):** Working tree changed again — TimeMachinePage now uses REAL data (old R3 fixed ✅), ledger scoreboard is half-wired into HonestModelCardPage (but with new fake-fallback landmines), and a congestion-radar backend appeared carrying 4 real defects (fictional 785km corridor that doesn't match the DB, a dead code branch, fabricated counts). Details + fix specs: `DEEP_RESEARCH_IMPLEMENTATION.md`. Corrections to this table are marked **[REVISED]**.

---

## CURRENT STATE (verified 2026-09-05)

### Backend (159 endpoints across 29 files)

| Area | Files | Endpoints | State |
|---|---|---|---|
| Core ETA/live/ledger | `routes.py` (1355 lines), `live_routes.py`, `predictor.py` | ~35 | Healthy, all consumed |
| Demo surfaces (NEW in `f371ecb`) | `demo_routes.py` (633) | 6 | Healthy, consumed by new pages |
| Passenger/PNR | `passenger_routes.py` (826) | 15 | Consumed by tracker pages |
| Ops (setin/setout/shunting) | `ops_routes.py` | 3 | Consumed |
| **Commercial** (certs, stalls, lost-found) | `commercial_routes.py` (495) | 9 | **ZERO frontend consumers — verified** |
| Workforce (breathalyzer, crew, shifts) | `workforce_routes.py` (526) | 10 | Partially consumed (roster only) |
| Safety, infra, handover, section, block, planner | 6 files (~2500 lines) | ~35 | Partially consumed |
| **Crew alerts `/v1/crew/alerts`** | doesn't exist | — | **Frontend calls a nonexistent endpoint — silently falls to mock** |

### Frontend (30 pages + mock system)

| Area | State |
|---|---|
| New demo pages (Foresight, Comparator, TimeMachine, Ripple, ModelCard) | Healthy, live data |
| Dashboard core (Overview, LiveMap, Trains, TrainDetail, Gantt) | Healthy |
| **Mock fallback system** (`web/src/mock/` — 2,544 lines, 20 `mockStore` refs in `api.ts`) | Advisories, Crew, Maintenance, Audit, Timetable **silently fall back to hardcoded fake data** |
| **AuditPage** | Displays **mock audit log + fake root hash** (`api.ts:762` hardcodes `'0x8f2a11b9...'`) while the REAL `/ledger/verify` endpoint sits unwired |
| **Duplicate pages** | `ModelPage` (dashboard/model) vs `HonestModelCardPage` (/model-card) — two model-proof pages |

### Security & repo hygiene

| Issue | Severity |
|---|---|
| **`.env` and `web/.env` TRACKED IN GIT** (confirmed via `git ls-files`; committed in `028fa9c` despite gitignore entries) | 🔴 Critical |
| `firebase-admin.json` — service account key at repo root (untracked, one `git add` from disaster) | 🔴 High |
| `graphify-out/` — **41MB** generated artifacts (gitignored) | 🟡 Space |
| `temp_resultshield/` — 810KB abandoned stress-test scaffold | 🟡 Junk |
| Root junk: `qr_code.png`, `master_audit_v2_results.json`, `scratch_audit_results.json`, `.coverage`, 3 `.uv-cache-*` dirs | 🟡 Junk |

### Dead ML lineage (2,624 lines)

`ml/model_v2.py`, `model_v3.py`, `train_v2.py`, `train_v3.py`, `features_v3.py`, `materialize_v3.py` — v2/v3 model generations, unserved. ORPHAN_MAP already classified them DEAD LINEAGE.

---

## REMOVE / ADD TABLE

| # | Action | Item | Where | Effort | Reason |
|---|---|---|---|---|---|
| **R1** | 🔴 REMOVE NOW | **`.env` + `web/.env` from git tracking** | repo root | 10min | Secrets in version history. `git rm --cached` both files, commit, then rotate every key that was inside. Nothing else on this table matters more. |
| **R2** | 🔴 REMOVE NOW | **Fake hash on AuditPage** | `web/src/lib/api.ts:762` (hardcoded `'0x8f2a11b9...'`) | 15min | Same fatal flaw as the old TimeMachinePage. Replace with a real `/api/audit/verify-integrity` call — that endpoint EXISTS (`api/audit_routes.py:106`) and is never used by AuditPage. **[REVISED]** also strip the twin landmine in `api.ts:936-951` — `getLedgerScoreboard`'s fabricated fallback (fake 2331/430 numbers + fake tip hash) which HonestModelCardPage can silently display. |
| **R3** | ✅ **FIXED** (verify once) | ~~TimeMachinePage mock receipts~~ | `web/src/pages/demo/TimeMachinePage.tsx` | 5min check | Deep pass confirmed: page now fetches REAL `/v1/demo/time-machine` data; hardcoded hashes gone. Only run `grep "3f7a18b\|Block #1963" web/src` before the demo to confirm zero regressions. |
| **R4** | 🟠 REMOVE | **Commercial routes** (delay-certificate, stalls, lost-found) | `api/commercial_routes.py` (495 lines) + `tests/test_passenger_commercial.py` | 1h | 9 endpoints, zero UI, zero rubric lines. The delay-certificate QR idea overlaps the G1 kill (IR refund-rule risk). **Exception:** if a teammate already demo-plans the QR certificate, keep only `/delay-certificate` and drop stalls/lost-found. |
| **R5** | 🟠 REMOVE | **Breathalyzer feature** | `api/workforce_routes.py:39-140` | 30min | Crew alcohol testing is real railway domain but irrelevant to PS 26028 (ETA forecasting). A judge asking "why is this in an ETA product?" has no good answer. KEEP crew roster + `/crew/breaches` (F13 crew duty alert is IN the PRD). |
| **R6** | 🟠 REMOVE | **Dead ML lineage v2/v3** | `ml/model_v2.py`, `model_v3.py`, `train_v2.py`, `train_v3.py`, `features_v3.py`, `materialize_v3.py` + their tests | 30min | 2,624 unserved lines; ORPHAN_MAP already classified them DEAD. Note in CHANGELOG "v3 preserved in git history" if a judge asks about experimentation. |
| **R7** | 🟠 REMOVE | **Root junk** | `qr_code.png`, `master_audit_v2_results.json`, `scratch_audit_results.json`, `.coverage`, `.uv-cache-*`, `temp_resultshield/`, local `graphify-out/` | 20min | Repo hygiene. Nothing here serves the demo. |
| **R8** | 🟡 CONSOLIDATE | **Duplicate model pages** | keep `HonestModelCardPage` (/model-card); make dashboard `/model` redirect to it | `web/src/pages/dashboard/ModelPage.tsx` | 30min | Two model-proof pages confuse the demo flow. The new card is dynamic (reads `metrics.json`); the dashboard one isn't the story anymore. |
| **R9** | 🟡 REMOVE | **Mock fallbacks for ADVISORIES / CREW / MAINTENANCE / TIMETABLE** | `web/src/mock/` (2,544 lines), `api.ts` fallback branches | 3–4h | 31 `mock` references in `api.ts`. Silent fake data is the biggest credibility trap: if a judge clicks Crew during the demo and sees plausible-but-fake crew, every real number on screen becomes suspect. Honest "no data" beats beautiful lies. **Partial purge acceptable** if short on time: strip mocks only from judge-reachable pages. Keep `mock/auth.ts` (login demo). |
| **R10** | 🟡 REMOVE | **`/v1/crew/alerts` frontend call** | `web/src/lib/api.ts:630` | 10min | Calls a nonexistent route → silent mock fallback. Either wire to the real `/api/workforce/crew/breaches` (`workforce_routes.py:320`) or delete the call. |
| **A1** | 🟢 ADD (top priority) | **Live Ledger Scoreboard UI — strip fake fallbacks + live counter** | **[REVISED]** endpoint, client fn (`api.ts:935,952`) and HonestModelCardPage consumption all EXIST. Remaining: delete the fabricated fallback in `getLedgerScoreboard`/`verifyLedgerChain`, remove `|| 2331`/`|| 430` JSX defaults, add a "blocks growing live" poll counter | **~1–2h (down)** | The #1 open item. The world-first claim — live hash-chained self-graded serving accuracy. The fake fallbacks are the last fabrication standing between you and that claim. Full spec: `DEEP_RESEARCH_IMPLEMENTATION.md` §1. |
| **A2** | 🟢 ADD | **Autopsy waterfall + Σ caption** | **[REVISED]** `AutopsyStrip` already renders proportional segments + integrity badge; missing only the cumulative waterfall form and "Σ causes = total ✓" caption. One file, pure CSS | ~2h | Renders the exact-sum proof from `engine/attribution.py:724`. Spec: §2. |
| **A3** | 🟢 ADD | **Passenger doom card** | `PassengerTrackerPage` + `api.getCascadeRipple()` (fn exists at `api.ts:920`, consumed only by RippleBoardPage) | ~1–2h | "⚠️ DOOMED — NTES says ON TIME" moment. Spec: §3. |
| **A4** | 🟢 ADD | **Historical why-late date input** | native `<input type="date">` on TrainDetailPage; `run_date` param plumbed through API + client, never sent by UI. 29 real run-days of data behind it | ~1h | "Why was my train late last Tuesday?" — archive is 33,601 events / 29 days (say that number, not "300k"). Spec: §4. |
| **A5** | 🟠 REPAIR THEN ADD | **Congestion radar — FIX 4 defects in shipped backend, then build UI** | **[REVISED]** endpoint EXISTS (`api/demo_routes.py:646`) but: (1) fictional NDLS–DDU 785km corridor vs real 440km 8-stop NDLS–LKO route in DB; (2) dead code branch (`tracker.positions` attribute doesn't exist — AST-verified); (3) fabricated counts when sections are empty (`demo_routes.py:716`); (4) `max(len,14)` fake train count | **~4–5h (up)** — repair ~2h, UI ~2–3h | The network-level D2 canvas — but a radar that can't show zero and names sections that don't exist is worse than no radar. Repair spec: §5. **Reuse `MIN_HEADWAY_KM=2.0` capacity from `engine/spatial_context.py:22` so radar and model share one capacity definition (Q&A consistency).** |
| **A6** | 🟡 NEW | **Weather-hourly backfill OR drop weather claims** | `weather_hourly` table has **1 row** behind every fog/rain story | ~30min | Run `scripts/weather_backfill.py` for the 29 run-days, or cut weather lines from the demo script. Found in deep pass (§6). |

---

## RECOMMENDED ORDER (revised after deep-research pass)

| Phase | Work | Time |
|---|---|---|
| **Day 1, hour 1** | R1 (secrets) → R2 (fake fallback strip: AuditPage + ledger client) → R3 verify-only | ~1h |
| **Day 1, rest** | A1 (now smaller: strip fakes + live counter) → A4 date input → A2 waterfall (same page as A4, do together) | ~4–5h |
| **Day 2, AM** | A5 radar REPAIR first (4 defects), then radar UI | ~4–5h |
| **Day 2, PM** | A3 doom card → R4/R5/R6/R7 removals + R8/R10 → A6 weather decision | ~3h |
| **Last hour** | Rehearse the 6-beat demo arc + smoke checklist below | 1h |

**Demo-day smoke checklist (last hour before judging):**
- [ ] `PredictionLedger(db).get_calibration_scoreboard()` shows `verified_arrivals_count > 0` (currently 432 ✓ — run `python scripts/demo_replay.py --fast` if 0)
- [ ] `grep "3f7a18b\|Block #1963\|0x8f2a11b" web/src` → 0 hits (no fabricated hashes)
- [ ] `/model-card` numbers match `ml/artifacts/metrics.json` (regenerate if models retrained)
- [ ] Radar corridor label matches real route: NDLS–LKO 440km via CNB, 8 stops, FTP absent
- [ ] Radar shows at least one genuinely EMPTY section (proves the fabrication fix)
- [ ] Ripple board shows at least one CRITICAL_DEFICIT rake (14 rake_links in DB — verify one is stressed in the demo scenario)
- [ ] Time-machine default `run_date=2026-09-02` has events (it is the max run_date ✓)
- [ ] `.env` not in `git ls-files`
- [ ] Demo script says **"33,600 events across 29 run-days, 2,343 sealed predictions, 432 graded"** — the real numbers, which grow live during the demo

---

## THE ONE-SENTENCE VERSION

**The deep pass changed the picture: your biggest remaining risk is not missing features but *fabricated data standing next to your honesty claims* — the scoreboard's fake fallback numbers, the AuditPage fake hash, and a radar that invents trains on a corridor that isn't in your database — strip those (A1-fix, R2, A5-repair ≈ 3h total) and every remaining feature is small, spec'd in `DEEP_RESEARCH_IMPLEMENTATION.md`, and wired to machinery that already works.**

---

*Generated 2026-09-05; revised same day after deep-research pass (AST verification of tracker internals, direct SQL against `data/railtwin.db` — sections/route_stations/ledger/weather volumes, line-level reads of all new demo routes, pages, and the api client). Cross-references: `DEEP_RESEARCH_IMPLEMENTATION.md` (per-feature specs), `FINAL_RECOMMENDATIONS.md` (strategy), `LATENT_ASSETS.md`, `CAPABILITY_FLIPS.md`, `RAW_IDEAS.md`, `NOVELTY_MATRIX.md`, `SCORING.md`.*
