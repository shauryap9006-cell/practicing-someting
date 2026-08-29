# RailTwin-X — ASSETS.md
**Data, Sources & Integration Assets** · v1.0
Answers for every module in PLAN.md: where the data comes from, how we get it, how we use it.

---

## 0. THE 3-BUCKET RULE

| Bucket | Definition | Examples |
|---|---|---|
| **A — Real & Free now** | Public data that exists today | Timetable, station list, corridor geometry, elevation, weather |
| **B — Synthetic now, CRUD forever** | Not public anywhere → generate realistic seeds; every module ships admin CRUD so a real station enters its own data on day one | Crew, footfall, incidents, failures, complaints, earnings |
| **C — Collect yourself, starting NOW** | Only becomes training data if we snapshot the live feed continuously | Train run/delay history (GRU + dwell + drift monitoring fuel) |

**Iron rule: Bucket C cron starts THIS WEEK, before any module is built. Every week of delay is training data we never get back.**

---

## 1. BUCKET A — REAL, FREE, AVAILABLE NOW

### 1.1 Live train position + timetable
| | |
|---|---|
| Source | RapidAPI Indian Railways provider (key already in repo) |
| Get | Existing `collector/` — audit which endpoints the provider exposes (timetable/route/live-status) |
| Use | A1 import adapter · A2 board · B1 inference features · **Bucket C snapshots (§4)** |
| Legal | Licensed key — fine for demo/pilot/portfolio. Not for redistribution. |
| Fallback | Second provider via same adapter interface; adapter pattern = swap without rewrite |

### 1.2 Corridor geometry, stations, platforms, level crossings, signals
| | |
|---|---|
| Source | **OpenStreetMap via Overpass API** (`overpass-api.de`) |
| Get | Query below with our corridor bbox; export JSON → `scripts/fetch_osm.py` → seed |
| Use | GIS map layers · NetworkX topology (engine/) · F1 asset positions · D6 LC register · A5 block schematic base · C3 simulator topology |

```overpass
[out:json][timeout:90];
(
  way["railway"="rail"]({{bbox}});
  way["railway"="platform"]({{bbox}});
  node["railway"="station"]({{bbox}});
  node["railway"="halt"]({{bbox}});
  node["railway"="level_crossing"]({{bbox}});
  node["railway"="signal"]({{bbox}});
  way["railway"="sidings"="yes"]({{bbox}});
  way["railway"="yard"]({{bbox}});
);
out body geom;
```
Note: `railway=platform` ways give platform geometry (→ platform count/positions for A3/F1). Signal coverage in India is patchy — treat OSM signals as the *position layer*, not a complete census (F1 CRUD completes it).
License: ODbL — attribute "© OpenStreetMap contributors" in the public page (G3).

### 1.3 Weather & fog (current + historical)
| | |
|---|---|
| Source | **Open-Meteo** (`open-meteo.com`) — already integrated |
| Get | Current: existing collector. **Historical backfill: Open-Meteo Archive API (free, decades back)** — pull 3–5 years for our corridor now |
| Variables to add | `visibility` (fog!), precipitation, temperature, wind |
| Use | B1 features (fog→delay) · B3 · C3 scenario shocks · D2 context |
| Legal | Free, attribution required. |

### 1.4 Station master list / reference data
| | |
|---|---|
| Source | data.gov.in (Government Open Data License) + Kaggle/GitHub "indian railways station code" datasets |
| Use | station codes/names/zones/coords → autocomplete, board, corridor endpoints |
| When | Phase 1, one-time static seed |

### 1.5 Timetable (bulk historical)
| | |
|---|---|
| Source | Kaggle "Indian Railways timetable" datasets; GitHub search `indian railways timetable json` |
| Use | A1 bulk import bootstrap (then RapidAPI endpoint keeps it fresh) |
| Caution | Verify freshness against RapidAPI; conflicting rows → RapidAPI wins |

### 1.6 Elevation / gradient
| | |
|---|---|
| Source | Copernicus DEM GLO-30 or SRTM 30 m (free) |
| Get | Sample raster along track polyline → gradient per block segment |
| Use | Safety Interlock kinematic inputs (gradient-dependent rules) · C3 realism |
| When | Phase 2 (D2/A5) |

### 1.7 NTES — **AVOID**
Scraping NTES violates its ToS. RapidAPI providers are the legal equivalent. Documented here so nobody "helpfully" adds an NTES scraper later.

---

## 2. BUCKET C — SELF-COLLECTED (the most valuable asset we own)

### 2.1 Snapshot collector cron
```
Every 5–10 min (config):
  collector/ → fetch live status for every train serving our corridor today
             → append timestamped snapshot to run_snapshots
             → mark run active in train_runs (once per train per day)
```
- **Label everything**: `source = synthetic | rapidapi | manual` on every row. Benchmarks never mix sources silently.
- Gap detection: if cron misses >3 consecutive cycles → degraded-mode banner (I6) + risk note.
- Retention: SQLite holds 90 days hot → nightly export to Parquet (`ml/data/history/`) for training.

### 2.2 Schemas (new migration)
```
train_runs      (run_id PK, train_no, run_date, origin, dest, source)
run_snapshots   (snapshot_id PK, run_id FK, ts, station_code,
                 sch_arr, sch_dep, exp_arr, exp_dep, delay_min,
                 last_loc_station, lat, lng, raw_json, source)
```
Indices: `(run_id, ts)`, `(train_no, run_date)`, `(ts)`.

### 2.3 What this buys us (timeline)
| After | We have |
|---|---|
| 1 week | Real delay patterns for the corridor; live board works off real positions |
| 8 weeks | Enough snapshots to retrain/validate B1 on observed data (source=rapidapi) |
| Ongoing | PSI drift becomes meaningful; B2 dwell labels (via A4 set-in/out gaps); honest benchmarks |

### 2.4 Bootstrap training (until real data matures)
Train B1/B2 on synthetic runs generated by **C3 SimPy + synthetic delay model** (Bucket B), label `source=synthetic`, then continuously replace with live data. Eval scripts MUST report metrics per source label.

---

## 3. BUCKET B — SYNTHETIC GENERATORS (realism specs)

All generators: `scripts/generate_*.py`, CLI with `--days`, `--seed` (reproducible), validate output against DB schema, write to `data/seeds/*.json`, label source=synthetic.

| Dataset | Generator must include | Volume | Feeds |
|---|---|---|---|
| Timetable | Realistic corridor pattern: ~60–80 trains/day (10–15 express, ~30 passenger/EMU, 8–10 freight night, 2–4 specials); peak-hour clustering 07–10 & 17–20 | 1 version, 90-day effective | A1, everything |
| Crew roster | 6/8/12h shifts, ≥12h rest, night limits, weekly offs, **deliberate 3–5 seeded violations** (so E2 breach engine has something to catch), leave records | 40–60 crew, 30 days | E2/E3/E4 |
| Footfall | AM/PM peaks, weekday>>Sunday, **festival spikes** (Diwali, Chhath, Holi, Eid calendar file), fog-season dampening | 365 days × platforms | B3, H1 |
| Earnings | Correlated with footfall (r>0.8) + noise | 365 days | H1 |
| Incidents | Rare-event distribution (~2–5/month), type mix, severity skew to LOW | 12 months | D4, B5, H4 |
| Asset failures | MTBF by type (points worst), winter/fog surge factor, 2 repeat-offender assets | 12 months | F3 |
| Complaints | Category mix: punctuality > water > cleanliness > staff > other | 12 months | G4 |
| Parcels/vendors/lost-found | Sparse, boring, realistic | 12 months | H2/H3/G5 |
| Caution orders | 2–4 active at a time, 5–40 km chainage, monsoon cluster | rolling | D2 |
| Weather-fog events | Dec–Jan visibility drops coupled with delay inflation in synthetic runs | historical 3 yr | B1, C3 |

**Correlation requirements (what makes it look real, not noise):** fog↔delay · festival↔footfall↔earnings · points-failure↔delay clusters · weekend↔footfall.

---

## 4. MODULE → DATA REQUIREMENTS MATRIX

| Module | Data needed | Bucket | Source | Status |
|---|---|---|---|---|
| A1 | Timetable, station list | A | RapidAPI + Kaggle + data.gov.in | ready |
| A2 | Live positions, ETA | A+C | RapidAPI + B1 | ready |
| A3 | Platform geometry, occupancy | A+C | OSM platforms + A4 | ready |
| A4 | Human confirmations | C | **station staff at deployment / us in dev** | start now |
| A5 | Topology, block defs | A | OSM + NetworkX + manual block mapping | ready |
| A6 | Movements | B | generator + CRUD | ready |
| B1 | Delay history, weather | A+C | snapshots + Open-Meteo archive | **cron now** |
| B2 | Dwell observations | C | A4 set-in/out gaps | after A4 |
| B3 | Timetable, festivals, actuals | A+B | A1 + festival calendar + H1 | ready |
| B4 | Actuals, causes | C | A4 + B5 | after A4 |
| B5/B6 | exists | — | — | — |
| C1/C2/C3 | exists | — | — | — |
| C4 | A1+A3+C2 | — | — | — |
| C5 | A1 + C3 | — | — | — |
| D2 | SR orders | B | generator + CRUD | ready |
| D3 | possessions | B | CRUD | ready |
| D4 | incidents | B | generator + CRUD | ready |
| D5 | SOP templates | B | hand-write 4 templates | ready |
| D6 | LC register | A | OSM level_crossings | ready |
| E2–E4 | crew data | B | generator + CRUD | ready |
| F1 | asset positions/attrs | A+B | **OSM seed + CRUD** | ready |
| F2–F4 | due dates, failures | B | generator + CRUD | ready |
| G1/G2 | derived | — | from A2/A3/D2 events | — |
| G3 | derived | — | read-only | — |
| G4/G5 | complaints, items | B | CRUD | ready |
| H1 | footfall, earnings | B | generator + CSV import | ready |
| H2/H3 | parcels, vendors | B | generator + CRUD | ready |
| H4 | everything | — | reads other modules | — |
| I1–I6 | users, roles, config | B | 10 hand-seeded users | ready |

---

## 5. ASSET REGISTRY (F1) — CONCRETE RECIPE

1. **Positions/layout**: OSM Overpass (§1.2) → `scripts/fetch_osm.py` → `assets` seed (type, lat/lng, chainage where mappable).
2. **Attributes** (install date, make, condition): synthetic seed values + **admin CRUD UI is the real deliverable** — in deployment, S&T/P-way inspector fills it (this module IS the digitization of paper registers).
3. **Hierarchy**: segment → asset → work_orders → maintenance_due (all in spine, §5 PLAN.md).
4. **Elevation**: DEM gradient per segment merged in Phase 2.

---

## 6. REAL-DEPLOYMENT INTEGRATION MAP (design adapters now, integrate someday)

| Our module | Real IR system it replaces/ingests | Adapter interface |
|---|---|---|
| A2/A4 board + set-in/out | NTES / station control chart | `LiveFeedAdapter` (already = RapidAPI) |
| H1 | UTS/PRS station reports | `CSVImportAdapter` |
| E2/E3 | CRIS Crew Management System | `CrewFeedAdapter` |
| F1–F4 | TMS / S&T failure registers | `AssetRegisterAdapter` |
| G4 | Rail Madad | `ComplaintFeedAdapter` |
| C2 freight | FOIS | `FreightFeedAdapter` |

**Design rule:** every ingest = `Adapter → normalized spine schema`. Swapping synthetic→real must be one class, never a rewrite. This is also what makes the project deployment-credible.

---

## 7. INFRASTRUCTURE & STORAGE ASSETS

| Asset | Role | Notes |
|---|---|---|
| SQLite WAL (existing) | operational spine | single-writer respected; writes via db.py manager |
| `backups/` + I5 cron | disaster recovery | `.backup` API, 7 daily + 4 weekly retention |
| Parquet store `ml/data/history/` | training warehouse | 90-day-old snapshots archived; pandas-ready |
| `ml/artifacts/*.json` (existing) | model artifacts | versioned via `model_runs` table from Phase 5 |
| Docker (existing) | deployment | final stage must not carry training data (risk OP-03) |
| Festival calendar `data/seeds/festivals.json` | seasonality truth | hand-curated, feeds B3 + generators |

---

## 8. HARDWARE HOOKS (feeds, not drivers)

| Hook | Provided by | Consumer (future) |
|---|---|---|
| PIDS screens | G1 JSON feed + HTML page | LED controller box |
| PA announcements | G2 TTS audio files + trigger API | PA amplifier interface |
| Breathalyzer | E3 checkbox + device hook placeholder | certified device vendor |
| CCTV | out of scope | — |

---

## 9. LEGAL & COMPLIANCE

| Source | License/Status | Obligation |
|---|---|---|
| RapidAPI provider | commercial key | no redistribution of raw feed |
| OpenStreetMap | ODbL | attribution on public page (G3) |
| Open-Meteo | CC-BY free | attribution |
| data.gov.in | GODL | license terms per dataset |
| NTES | **do not scrape** | ToS violation |
| Synthetic data | ours | must be labeled everywhere it appears |

---

## 10. PHASE-ALIGNED DATA ACTIONS

| Phase | Data actions |
|---|---|
| **0** | Start Bucket C cron · Open-Meteo historical backfill · users/roles seed |
| **1** | OSM corridor fetch → topology + platforms · timetable bulk import (Kaggle+RapidAPI) · festival calendar |
| **2** | DEM gradient per segment · caution-order/incident generators · 4 SOP templates |
| **3** | Crew generator (with seeded violations) |
| **4** | OSM asset seed + attribute generator |
| **5** | First live-source retrain if ≥4–8 wks snapshots · dwell labels from A4 · H1 actuals validate B3 |
| **6–7** | Remaining Bucket B generators + CRUD |

---

## 11. DATA QUALITY RULES (apply to every ingest, synthetic or real)

1. Pydantic validation at the adapter boundary — bad rows quarantined, not silently dropped.
2. `source` label mandatory on every row (synthetic | rapidapi | manual | inferred).
3. Referential integrity checks in migration + nightly job (orphan snapshots, runs without trains).
4. Snapshot gap alarm (>3 missed cycles → degraded mode + risk note).
5. PSI also runs on **incoming feed distributions**, not just model features.
6. Benchmarks always report per-source metrics — never blended silently.

---

## 12. IMMEDIATE ACTION (this week, in order)

1. `git commit` PLAN.md + ASSETS.md + fixes.md at repo root.
2. **Run fixes.md Part B audit** → fills every "verify against repo" gap, produces control-room files.
3. **Write + deploy the Bucket C snapshot cron** (schema in §2.2) — single highest-leverage action in this entire plan.
4. Run Open-Meteo historical backfill (3–5 years, corridor bbox).
5. Start Phase 0: `BUILD MODULE I1` (RBAC) via Master Build Prompt.
