# RailTwin-X — PLAN.md
**Station OS Master Build Plan** · v1.0 · Status: APPROVED-FOR-BUILD (pending Phase 0)
Companion files: `fixes.md` (how we execute) · `ASSETS.md` (where every byte of data comes from)
Execution loop: BOOT → EXECUTE → WRAP → (phase end) GO/NO-GO GATE — see fixes.md Part D

---

## 0. HOW TO USE THIS FILE

- This file = **WHAT** we build and **WHEN**. `ASSETS.md` = where the data comes from. `fixes.md` = how we work.
- Build one module per Claude Code session using the Master Build Prompt (§12).
- Every module must meet the **Global Definition of Done** (§9) — it applies to all 47 modules, so it is written once here, not repeated per module.
- After each phase: run the GO/NO-GO GATE prompt (fixes.md D.2.5) before starting the next phase.

---

## 1. VISION & SCOPE

**One sentence:** RailTwin-X becomes the complete operating system for a railway station — every register, board, roster, safety workflow and prediction a real station runs on, living on one shared data spine, gated by one deterministic Safety Interlock.

**IN scope:**
- One station as the operational unit + corridor visibility (GIS, live trains, upstream/downstream prediction)
- Web application (FastAPI + Next.js 14), SQLite WAL spine
- Advice + workflow + prediction. Human confirms every safety-relevant action.

**OUT of scope (deliberate):**
- Physical interlocking / train detection hardware (signals, axel counters, track circuits) — our app *displays and advises*; it never drives hardware
- Hardware drivers (PA amplifiers, LED PIDS controllers, CCTV) — we provide feeds/hooks (§7.3)
- IRCTC/PRS ticketing integration — manual/CSV first, hook later
- Multi-station deployment — single-station scope; RBAC has a `station_code` column from day one so this costs nothing to add later

---

## 2. CURRENT FOUNDATION (what exists today)

| Component | Status | Notes |
|---|---|---|
| GRU probabilistic ETA (2-layer, temporal attention, non-crossing quantile heads [p10,p50,p90]) | ✅ | ml/ |
| 6× LightGBM quantile models + CQR calibration | ✅ | ml/ |
| PSI drift monitoring | ✅ | ml/ |
| 1-Click self-healing platform Gantt re-optimizer (<2s greedy local search) | ✅ | engine/ |
| Freight-aware headway + single-line opposing conflict scanner | ✅ | engine/ |
| SimPy cascade simulator + sim_ledger (exact causal-minute accounting) | ✅ | engine/ |
| Safety Interlock Layer (5 deterministic kinematic rules, zero ML) | ✅ | safety/ — DO NOT MODIFY without explicit approval |
| Next.js 14 cockpit (GIS corridor map, platform Gantt, crew breach lookahead) | ✅ | dashboard/ |
| OpenWA WhatsApp dispatcher (HMAC reply-to-ACK, SMS fallback) | ✅ | notifications/ |
| Delay autopsy + Maintenance Kart simulator | ✅ | engine/ |
| SQLite WAL (14 tables, 33,600+ events, thread-safe manager data/db.py) | ✅ | data/ |
| 93 pytest tests (unit/integration/adversarial), Docker, CI YAML | ✅ | tests/ |
| Auth/RBAC, audit trail, handover, rostering, registers | ❌ | → this plan |

---

## 3. ASSUMPTIONS (adjust if wrong — cheap to change now, painful later)

1. **Indian Railways domain**: SM/Dy.SM, rake, caution orders, PTW, TTE, UTS/PRS, CRIS, FOIS, Rail Madad terminology.
2. **Single station + corridor** visibility.
3. Solo developer + Claude Code; SQLite stays (revisit Postgres only if WAL write contention is measured — 07_METRICS.md).
4. All new data is **synthetic-seeded with CRUD for real entry** until real deployment (see ASSETS.md §3).

---

## 4. MODULE CATALOG (47 modules: 8 done · 3 partial · 36 new)

Legend: ✅ exists · 🟡 partial · 🆕 new · Size: S (<1 session) M (1 session) L (2+ sessions) · Priority P0–P3
Each module lists: Purpose → Features → API → DB → UI → Integrations → Acceptance (feature-specific only; global DoD in §9).

### GROUP A — TRAIN OPERATIONS (live ops core)

**A1 · Timetable Manager** 🆕 P0 L
- Purpose: single source of truth for scheduled operations.
- Features: versioned working timetable (draft→published→archived, effective date ranges); full CRUD per train (no., type express/passenger/freight/EMU, up/down, per-stop sch arr/dep, default platform, days-of-run); cancellations/diversions/temporary additions with reason codes; import adapter (seed JSON + RapidAPI timetable endpoint); validation (no negative dwell, min turnaround, headway preview via C2); version diff view.
- API: `GET/POST /api/timetable/versions`, `GET/PUT/DELETE /api/timetable/entries/{id}`, `POST /api/timetable/versions/{id}/publish`, `GET /api/timetable/diff?v1=&v2=`
- DB: `timetable_versions`, `timetable_entries`
- UI: `/timetable` editor (table view, version selector, diff modal, validation panel)
- Integrations: feeds A2, A3, C1, C2, B1, B3, G1; publish event → notification center
- Acceptance: create version → seed 50 trains → validation catches 1 injected bad entry → publish → A2 reflects it.

**A2 · Live Arrival/Departure Board** 🆕 P0 M
- Purpose: the station's live face — auto-updating train board.
- Features: train no/name, Sch vs Exp time (Exp = B1 p50), delay badge, platform, status (ON TIME / LATE x / CANCELLED / ARRIVED / DEPARTED); auto-refresh (TanStack Query polling ≤30s); filter by platform/hours; big-screen mode.
- API: `GET /api/board/live?date=&hours=` (computed join: timetable × ETA × ad_events)
- DB: none new (reads A1, B1, A4)
- UI: `/board` full-screen board component
- Integrations: B1 (ETA), A4 (actuals), A1 (platform), G1 (same data powers PIDS)
- Acceptance: board shows correct delay for a simulated late train within 30s of ETA update.

**A3 · Platform Allocation Console** 🟡 P0 L (upgrade of existing Gantt)
- Purpose: full control console for platform occupancy.
- Features: existing Gantt + platform state machine (FREE / OCCUPIED / BLOCKED-MAINT / OUT-OF-SERVICE); manual assign + drag-drop reallocation; instant conflict highlight (C2 rules); assignment locking (SM role only); occupancy timeline 24h; link to set-in/out truth (A4).
- API: `POST /api/platform/assign`, `PUT /api/platform/assign/{id}`, `GET /api/platform/states`
- DB: `platform_states`, `platform_assignments`
- UI: upgrade existing Gantt page
- Integrations: C1 (auto-fill), C2 (conflict check on every mutation), D1 (interlock gate before commit), A4 (occupancy truth), F1 (platform as asset)
- Acceptance: drag a train onto an occupied platform → conflict highlighted → forced alternative → passes interlock → committed + audited.

**A4 · Set-In / Set-Out Workflow** 🆕 P0 M
- Purpose: record ACTUAL arrival/departure + platform occupancy — the ground truth that keeps predictions honest.
- Features: one-tap set-in/set-out per train (SM console + mobile-friendly); actual platform, actual times; auto-suggestion from B1 p50 pre-filled, human confirms; discrepancy flag if |actual−p50| > threshold; late manual entry supported.
- API: `POST /api/ops/setin/{run_id}`, `POST /api/ops/setout/{run_id}`
- DB: `ad_events` (arrival/departure events, source=human vs inferred)
- UI: `/ops` quick-action panel + confirmation log
- Integrations: **this is the Bucket-C training data capture point** (ASSETS.md §4); B4 punctuality; B1 future retraining labels
- Acceptance: set-in for a train → board shows ARRIVED → ad_events row written with source=human → autopsy can use it.

**A5 · Block Section & Line Status Board** 🆕 P1 M
- Purpose: visual line/block state around the station.
- Features: corridor diagram (from NetworkX topology) with per-block state (CLEAR / OCCUPIED / BLOCKED / CAUTION); grant/line-clear entry workflow (advisory only — hardware out of scope); caution-order overlay from D2.
- API: `GET /api/blocks/status`, `POST /api/blocks/{id}/state`
- DB: `block_status`
- UI: `/blocks` corridor schematic panel (reuse GIS map layers)
- Integrations: D2 overlay, C2 (blocked blocks → scanner constraints), F1 (block = asset)
- Acceptance: mark block blocked → scanner excludes paths through it → D2 caution order visible on schematic.

**A6 · Shunting & Loco Movement Log** 🆕 P1 S
- Purpose: non-timetable movements (loco attach/detach, rake release) logged so they never silently conflict with the Gantt.
- Features: quick-log form (movement type, rake/loco id, from→to, window); optional Gantt overlay as hatched blocks; conflict check on entry.
- API: `POST /api/ops/shunting`, `GET /api/ops/shunting?date=`
- DB: `shunting_moves`
- UI: `/ops` sub-tab
- Integrations: A3 (overlay), C2 (conflict check)
- Acceptance: log shunt overlapping an express platform window → conflict flagged.

### GROUP B — PREDICTION & INTELLIGENCE

**B1 · Probabilistic ETA (GRU + LightGBM + CQR)** ✅ DONE
- Enhancement (Phase 5, after A4 accumulates real data): retrain on live snapshots (ASSETS.md §4), source-labeling aware.

**B2 · Dwell-Time Model** 🆕 P2 M
- Purpose: per-platform/per-train-type dwell prediction → replaces constant-dwell assumption in C1.
- Features: LightGBM quantile dwell model (features: train type, platform, scheduled halt, crowd forecast B3, time-of-day, monsoon flag); plugged into re-optimizer as variable dwell; backtest vs constant-dwell baseline.
- API: internal (engine); `GET /api/ml/dwell?train=&platform=`
- DB: `dwell_stats` (observed dwell from A4 set-in/out gaps)
- Integrations: C1 (constraint), B3 (feature), A4 (labels)
- Acceptance: backtest shows pinball loss ≤ constant-dwell baseline on synthetic + real data.

**B3 · Footfall/Crowd Forecast** 🆕 P2 M
- Purpose: platform crowd forecast next 2h → crowd alerts + staff positioning + dwell feature.
- Features: per-platform hourly forecast (features: timetable arrivals/departures, day-of-week, festival calendar, fog-season factor); crowd threshold alerts via notification center; validation vs H1 actuals.
- API: `GET /api/ml/crowd?platform=&horizon=2h`
- DB: `crowd_forecasts`
- Integrations: H1 (actuals), B2 (feature), notification center, `/ops` display
- Acceptance: forecast for a seeded festival day shows the spike; MAPE reported in 07_METRICS.md.

**B4 · Punctuality KPI Engine** 🆕 P2 M
- Purpose: the station's scorecard, computed continuously.
- Features: punctuality % (within 5/10/15 min), avg delay, delay minutes by cause (from autopsy), per train/hour/day/week trends; dwell excess KPI; export CSV; powers H4 daily report.
- API: `GET /api/kpi/punctuality?from=&to=&group_by=`
- DB: materialized `kpi_daily` (recompute job)
- UI: `/kpi` dashboard page (Recharts)
- Integrations: A4 actuals, B5 causes, H4 report
- Acceptance: seeded 30-day data → correct punctuality % cross-checked by hand for one day.

**B5 · Root-Cause Delay Autopsy** ✅ DONE — Phase 2 upgrade: consume D2 caution orders + D4 incidents as cause inputs.

**B6 · PSI Drift Monitoring** ✅ DONE — Phase 5 upgrade: wire breach → actionable task + alert (close risk ML-03).

### GROUP C — SCHEDULING & CONFLICT

**C1 · Re-optimizer** ✅ DONE — Phase 5 upgrade: variable dwell from B2; caution-order speed constraints from D2.

**C2 · Headway/Opposing Scanner** ✅ DONE.

**C3 · SimPy Simulator + sim_ledger** ✅ DONE — becomes the **what-if engine** for C5 and the regression gate in GO/NO-GO.

**C4 · Gantt Planner (manual drag-drop day editor)** 🆕 P1 L
- Purpose: edit the whole day by hand; every edit conflict-checked live; commit passes D1.
- Features: 24h Gantt across all platforms + loop lines; drag/move/insert/cancel trains; live conflict highlighting (C2); "simulate this day" button (C3, side-by-side before/after delay propagation); apply → interlock → versioned change record.
- API: `POST /api/planner/apply` (batch change set), `POST /api/planner/simulate`
- DB: `planner_changesets` (before/after JSON, who, when, sim result)
- UI: `/planner` full-screen editor
- Integrations: A1, A3, C2, C3, D1; changeset → audit log
- Acceptance: move 3 trains in a conflicting pattern → simulate shows +18 min cascade → apply passes interlock → changeset versioned.

**C5 · Capacity Analyzer** 🆕 P2 M
- Purpose: "can we add 2 more trains at 18:00?" — answered with simulation, not opinion.
- Features: platform/loop utilization %, peak saturation; add/remove train what-if (runs C3); headway headroom per hour; printable analysis.
- API: `POST /api/capacity/analyze` (scenario JSON)
- DB: none (reads A1, C3 results)
- UI: `/capacity` page
- Integrations: C3, A1, B2
- Acceptance: analyze seeded Friday evening → saturation report matches manual count.

### GROUP D — SAFETY & COMPLIANCE

**D1 · Safety Interlock Layer** ✅ DONE — sacred. 5 deterministic rules, zero ML. Every mutation from A3, C1, C4, D3 must pass through it. (`safety/` off-limits without explicit human approval per EXECUTE prompt.)

**D2 · Caution Orders / Speed Restriction Registry** 🆕 P0 M
- Purpose: active SRs by chainage, first-class citizens in prediction + optimization.
- Features: create/order lifecycle (issued → active → lifted) with chainage km, speed limit, reason, expiry; auto-expiry alerts; corridor map overlay; feeds B1 as feature + C1/C2 as constraint.
- API: `POST /api/safety/caution-orders`, `GET /api/safety/caution-orders/active`
- DB: `caution_orders`
- UI: `/safety` tab + map overlay
- Integrations: B1, C1, C2, A5, G2 (announcement when major SR active)
- Acceptance: active SR between km 12–15 → GRU features include SR flag → optimizer respects it (test proves it).

**D3 · Permit-to-Work / Possession Workflow** 🆕 P1 M
- Purpose: turn Maintenance Kart from simulator into a real workflow: request → grant → block → work → safe-to-restore, with interlock checks at grant and restore.
- Features: possession request (asset, window, type); grant requires no conflicting trains (checks A1 + C2); during possession A5 shows BLOCKED; restore requires worker confirmation + interlock pass; all state changes audited.
- API: `POST /api/possessions`, `PUT /api/possessions/{id}/grant|start|restore`
- DB: `possessions`
- UI: `/maintenance/possessions`
- Integrations: F2 (auto-creates requests), A5, D1, notifications
- Acceptance: grant attempted during conflicting train window → denied with reason; valid grant → block state propagates.

**D4 · Incident & Near-Miss Register** 🆕 P1 M
- Features: structured report (type: SPAD/equipment failure/passenger injury/near-miss; severity; location; description; linked train/asset); status workflow; feeds B5 autopsy as cause input; monthly summary.
- API: `POST /api/incidents`, `GET /api/incidents`
- DB: `incidents`
- UI: `/safety/incidents`
- Integrations: B5, F3 (equipment failure → asset failure record), H4 report
- Acceptance: equipment-failure incident creates linked asset_failure row automatically.

**D5 · SOP / Emergency Checklist Runner** 🆕 P1 M
- Features: templated checklists (fire, medical, derailment, level-crossing failure); step-by-step runner with timestamps + responsible role; auto-notification of escalation chain on start; post-run PDF.
- API: `POST /api/sop/runs`, `PUT /api/sop/runs/{id}/steps/{n}`
- DB: `sop_templates`, `sop_runs`
- UI: `/sop` runner (large buttons — stress-usable)
- Integrations: notification center, H4 report
- Acceptance: fire SOP run → step timestamps recorded → escalation WhatsApp sent on start.

**D6 · Level Crossing Status Board** 🆕 P2 S
- Features: LC register (from OSM seed), status (OK / FAULT / UNDER REPAIR), failure log, link to F3/F4.
- API: `GET /api/lc/status`, `POST /api/lc/{id}/fault`
- DB: `lc_status` (or assets-based)
- UI: map layer + `/safety/lc`
- Integrations: F1/F3/F4, D2 (SR if LC fault persists)
- Acceptance: mark LC faulty → work order auto-suggested.

### GROUP E — CREW & STAFF

**E1 · Crew Duty Breach Lookahead** ✅ → absorbed into E2 as a rule engine.

**E2 · Crew Rostering** 🆕 P1 L
- Features: shift planner (6/8/12h patterns, weekly off, night-duty limits, rest rules ≥12h); drag-drop roster editor; **rule engine** = E1 breach lookahead (live, any roster edit); auto-coverage suggestion (who's legal & available); publishing + change notifications.
- API: `POST /api/crew/rosters`, `GET /api/crew/breaches?horizon=7d`
- DB: `crew_members`, `crew_rosters`, `crew_duties`
- UI: `/crew` roster grid
- Integrations: E3/E4 (actuals vs roster → breach alerts), notification center
- Acceptance: build roster violating rest rule → breach flagged with rule citation → suggested fix accepted.

**E3 · Crew Sign-On / Sign-Off** 🆕 P1 S
- Features: duty start/end with fitness declaration checkbox (+ placeholder hook for breathalyzer device integration); roster-vs-actual gap alert if >15 min.
- API: `POST /api/crew/signon`, `POST /api/crew/signoff`
- DB: extends `crew_duties`
- Integrations: E2, notification center
- Acceptance: late sign-on → alert to Crew Controller role.

**E4 · Attendance & Leave Board** 🆕 P1 S
- Features: who is available right now; leave requests/approvals; substitute finder (legal + available, from E2 rules).
- API: `GET /api/crew/available?now=`, `POST /api/crew/leaves`
- DB: `attendance`, `leaves`
- Integrations: E2, E3
- Acceptance: mark 2 crew on leave → substitute finder excludes them.

### GROUP F — ASSETS & MAINTENANCE

**F1 · Asset Registry** 🆕 P1 L
- Features: every asset (points, signals, track segments, OHE spans, bridges, LC gates, platforms) with ID, type, chainage/lat-long, install date, condition, status; **seeded from OSM (ASSETS.md §5) + admin CRUD**; map view; segment→asset hierarchy.
- API: `GET/POST/PUT /api/assets`
- DB: `assets`
- UI: `/assets` registry + map
- Integrations: F2/F3/F4, A5, D3, D6, GIS map layers
- Acceptance: OSM seed imports N assets for corridor → CRUD edits persist → map renders them.

**F2 · Maintenance Scheduler** 🆕 P2 M
- Features: POH/IOH/inspection due dates per asset; calendar view; overdue alerts; auto-creates D3 possession request for window.
- API: `GET /api/maintenance/due`, `POST /api/maintenance/schedule`
- DB: `maintenance_due`
- Integrations: F1, D3, notification center
- Acceptance: overdue inspection → alert + one-click possession draft.

**F3 · Failure Log + MTBF Analytics** 🆕 P2 S
- Features: failure records per asset, downtime, repeat-offender ranking (MTBF chart), winter/fog season correlation flag.
- API: `POST /api/assets/{id}/failures`, `GET /api/assets/mtbf`
- DB: `asset_failures`
- Integrations: D4, F4, H4
- Acceptance: seeded 12-month failures → MTBF ranking matches hand-check.

**F4 · Work Orders** 🆕 P2 M
- Features: open → assigned → in-progress → done → verified workflow; linked asset + possession; photo/note attachments (path refs); overdue alerts.
- API: `POST /api/work-orders`, `PUT /api/work-orders/{id}/status`
- DB: `work_orders`
- UI: `/maintenance/work-orders` kanban
- Integrations: F1–F3, D3, H4
- Acceptance: full lifecycle test incl. verified-closure requiring possession state RESTORED.

**F5 · Maintenance Kart** ✅ → Phase 4: linked to real possessions (D3) + assets (F1).

### GROUP G — PASSENGER-FACING

**G1 · PIDS Feed** 🆕 P2 S
- Purpose: clean JSON/HTML feed any display screen can consume.
- Features: `GET /api/pids/feed` (per platform: train, exp time, delay, platform, coach position placeholder); simple HTML auto-refresh page `/pids/{platform}`; stable schema versioned.
- Integrations: A2 (same data), G2
- Acceptance: feed contract test (schema snapshot) + HTML page renders.

**G2 · Auto Announcement Engine** 🆕 P2 M
- Features: event-triggered (train 5 min out, platform change, delay >10 min, major SR active) → templated multilingual script (Hindi/English) → TTS audio file generation → WhatsApp broadcast + **hardware hook** (output file/API for future PA integration); deduplication; quiet-hours config.
- API: `POST /api/announcements/preview`, `GET /api/announcements/log`
- DB: `announcements`
- Integrations: notification center (OpenWA), A2/A3/D2 events
- Acceptance: platform change event → 1 announcement generated (not 3), Hindi+English, logged.

**G3 · Public Status Page** 🆕 P2 S
- Features: read-only mobile page: today's trains, live delay, platform; no auth; rate-limited.
- UI: `/public` + `GET /api/public/status`
- Acceptance: renders on mobile viewport; no authenticated endpoints leaked.

**G4 · Complaint/Suggestion Register** 🆕 P2 S
- Features: log, categorize (punctuality/water/cleanliness/staff/other), status track, monthly summary.
- DB: `complaints` · UI: `/passenger/complaints`
- Acceptance: lifecycle + summary count test.

**G5 · Lost & Found Register** 🆕 P3 S
- Features: item log, claim matching, disposal after N days.
- DB: `lost_found` · UI: `/passenger/lost-found`
- Acceptance: register + claim + dispose lifecycle.

### GROUP H — COMMERCIAL & STATION ADMIN

**H1 · Footfall & Earnings Dashboard** 🆕 P3 M
- Features: manual entry + CSV import (UTS-format placeholder adapter); daily/weekly charts; feeds B3 actuals.
- DB: `footfall_daily`, `earnings_daily` · UI: `/commercial`
- Acceptance: CSV import → chart → B3 validation uses it.

**H2 · Parcel & Goods Register** 🆕 P3 S — DB `parcels` · lifecycle in/out.
**H3 · Stall/Vendor Lease Tracker** 🆕 P3 S — DB `vendors` · license expiry alerts (60/30/7 days).
**H4 · Daily Station Report Generator** 🆕 P3 M
- Features: one click → PDF: punctuality (B4), incidents (D4), possessions (D3), crew exceptions (E2/E3), footfall (H1), asset failures (F3), complaints (G4); auto email/WhatsApp to division.
- API: `POST /api/reports/daily`
- Acceptance: generated PDF contains today's real numbers from ≥5 modules.

### GROUP I — PLATFORM & GOVERNANCE (BUILD FIRST)

**I1 · RBAC** 🆕 **P0 L — nothing else ships before this**
- Features: roles: Station Master, Dy.SM, Crew Controller, Section Controller, Engineer, TTE, Commercial Inspector, Admin, Viewer; endpoint-level role guards (FastAPI dependency, default-deny); `station_code` on users (future multi-station); login (JWT) + session expiry; user admin UI.
- API: `POST /api/auth/login`, `GET/POST /api/admin/users`, role middleware on every router
- DB: `users`, `roles`, `user_roles`
- UI: `/login`, `/admin/users`
- Acceptance: each role×endpoint matrix test — every mutating endpoint denies unauthorized role with 403.

**I2 · Digital Shift Handover Logbook** 🆕 P0 M
- Features: auto-populated at shift change (open incidents D4, active SRs D2, possessions D3, roster exceptions E2, unresolved complaints) + free text; outgoing SM signs, incoming SM acknowledges; searchable history.
- DB: `handover_log` · UI: `/handover`
- Acceptance: handover at 08:00 captures all open items from ≥4 modules automatically.

**I3 · Full Audit Trail** 🆕 P0 M
- Features: append-only `audit_log` (who, what, when, table, record id, before→after JSON); written by central helper, mandatory on all mutations; viewer UI with filters; integrity check (row hash chain).
- Acceptance: mutate a platform assignment → audit row with correct before/after → hash chain validates.

**I4 · Notification Center** 🟡 P0 M (upgrade of OpenWA dispatcher)
- Features: role-targeted routing (not just phone numbers); escalation ladder (unacked 5 min → supervisor → SMS); in-app notification tray (dashboard bell); event bus helper `notify(event, roles, severity)` all modules use; dedup.
- DB: `notifications`, `notification_ack`
- Acceptance: simulated unacked alert → escalation to supervisor fires; ACK via existing HMAC reply flow stops it.

**I5 · Backup & Restore Automation** 🆕 P0 S
- Features: scheduled SQLite snapshot (`.backup` API, WAL-safe) → `backups/` with retention (7 daily, 4 weekly); restore procedure documented in runbook; backup success/failure alert. Closes risk DA-02.
- Acceptance: backup runs in CI-mocked test; restore into scratch DB passes row-count check.

**I6 · Offline/Degraded Mode** 🆕 P1 M
- Features: defined behavior when live feed / OpenWA / external APIs are down: live-truth from last snapshot with **STALE DATA** banner + age; core ops (A4 set-in/out, A3, handover) stay fully local; alert queue with retry; degraded-mode status page section. Closes risk IN-04 partially.
- Acceptance: kill network mock → board shows STALE with age → set-in/out still works → queued alert flushes on reconnect.

---

## 5. DATA SPINE (14 existing → ~45 tables)

**Rule: every module reads/writes the same SQLite WAL DB via `data/db.py` and emits events to the notification center. No private stores. No exceptions.**

| Group | New tables (key columns) |
|---|---|
| Governance | `users (id, username, role_id, station_code, hash)`, `roles`, `user_roles`, `audit_log (ts, actor, table, rec_id, before, after, row_hash)`, `handover_log (shift, items_json, text, signed_by, acked_by)`, `notifications (event, target_role, severity, state)`, `notification_ack` |
| Operations | `timetable_versions (id, status, effective_from, published_at)`, `timetable_entries (version_id, train_no, type, dir, stop_seq, sch_arr, sch_dep, platform_default)`, `platform_states (platform, state, since)`, `platform_assignments`, `ad_events (run_id, kind setin/setout, actual_ts, platform, source human/inferred)`, `block_status (block_id, state, since)`, `shunting_moves` |
| Safety | `caution_orders (km_from, km_to, speed_limit, state, expires)`, `possessions (asset, window, state)`, `incidents (type, severity, refs)`, `sop_templates`, `sop_runs (steps_json, timestamps)` |
| Crew | `crew_members`, `crew_rosters (shift patterns)`, `crew_duties (roster vs actual)`, `attendance`, `leaves` |
| Assets | `assets (type, chainage, latlng, install_date, condition)`, `asset_failures`, `work_orders (state)`, `maintenance_due (asset, kind, due_date)` |
| Passenger | `announcements (trigger, lang, audio_path, state)`, `complaints (category, state)`, `lost_found` |
| Commercial | `footfall_daily`, `earnings_daily`, `parcels`, `vendors (license_expiry)` |
| ML | `dwell_stats`, `crowd_forecasts`, `kpi_daily`, `model_runs (model, version, trained_on, metrics_json)` |
| Ops | `backups (path, ts, rows)`, `planner_changesets` |

**Migrations:** numbered scripts in `scripts/migrations/NNN_*.sql`, applied by a CLI `make migrate`, recorded in `schema_migrations` table. Never edit applied migrations.

---

## 6. BUILD PHASES & ROADMAP

| Phase | Modules | Exit criteria (before next phase) | Est. |
|---|---|---|---|
| **0 Foundation** | I1, I3, I5, I2, I4↑ | RBAC matrix tests green; audit on every mutation; backup cron live; first handover signed; escalation ladder tested. GO/NO-GO green. | 1.5–2 wk |
| **1 Live Truth** | A1, A4, A2, A3↑, A5, A6, C4, I6 | Timetable published; set-in/out drives board; Gantt editor + interlock commit; stale-mode banner. **Snapshot collector cron (ASSETS.md §4) running since day 1 of this phase.** | 2.5–3 wk |
| **2 Safety & Compliance** | D2, D3, D4, D5, D6 | SR feeds B1+C1 proven by test; full PTW lifecycle; SOP run end-to-end with escalation. | 1.5–2 wk |
| **3 People** | E2, E3, E4 | Roster rule engine catches all seeded breaches; sign-on gap alerts work. | 1.5 wk |
| **4 Assets** | F1, F2, F3, F4 (F5 link) | OSM-seeded registry; PTW↔work-order↔asset chain closes. | 1.5–2 wk |
| **5 ML Upgrades** | B2, B3, B4, C5 (B1 retrain) | Dwell backtest beats baseline; crowd MAPE on 07_METRICS.md; KPI cross-checked; ≥4 weeks live snapshots available for B1 retrain. | 2–3 wk |
| **6 Passenger** | G1, G2, G3, G4, G5 | PIDS contract test; announcement dedup proven; public page rate-limited. | 1.5 wk |
| **7 Commercial** | H1, H2, H3, H4 | Daily PDF contains real numbers from ≥5 modules. | 1–1.5 wk |

**Total: ~13–17 weeks** solo + Claude Code at 1 module/session. Re-baseline after Phase 1.

**Dependency rules:** I1 blocks everything · A1+A4 block B4/C5 · D2 blocks B1-feature/C1-constraint upgrades · F1 blocks F2–F4 · H1 blocks B3 validation.

---

## 7. CROSS-CUTTING SPECS

**7.1 Event bus:** one helper (`notify(event, roles, severity, payload)`) — every module emits; notification center routes/escalates; OpenWA stays the transport.
**7.2 Performance:** API p95 < 300 ms for reads; re-optimizer stays < 2 s (07_METRICS.md gate); board poll ≤ 30 s; SQLite WAL single-writer respected (writes batched via db.py).
**7.3 Hardware hooks (not integrations):** PIDS = G1 feed consumers; PA = G2 output file/API; future: breathalyzer (E3 hook), CCTV (out of scope).
**7.4 Config:** all thresholds (delay badge, crowd limits, escalation timers, quiet hours) in one YAML config, env-overridable.

---

## 8. ML ROADMAP (summary — details in ASSETS.md for data)

- Now: B1 GRU+LGBM+CQR+PSI (exists) · Retrain gate: only on live-snapshot data, versioned via `model_runs`, GO/NO-GO includes coverage + crossing-rate checks.
- Phase 5: B2 dwell (LightGBM quantile), B3 crowd (LightGBM/GBM), B4 (no ML — SQL KPIs), C5 (simulation).
- All new models: same standards as B1 — quantile outputs where uncertainty matters, CQR calibration, PSI monitoring, artifact versioning, eval script + metrics in 07_METRICS.md.

---

## 9. GLOBAL DEFINITION OF DONE (applies to every module)

1. FastAPI router + Pydantic v2 models; data via `data/db.py` only; numbered migration script.
2. RBAC roles declared per endpoint, default-deny; every mutation → audit log.
3. Events emitted via notification helper where operationally meaningful.
4. Next.js page/component with loading + error + empty states; TanStack Query; Zustand only for local UI state.
5. pytest module: happy path + **permission denial** + ≥1 adversarial case; new test count recorded in 07_METRICS.md.
6. If it touches movement/platform/scheduling → passes Safety Interlock; `safety/` never modified without explicit approval.
7. Seed data (if any) in `data/seeds/`, validated against schema, `source=synthetic` labeled.
8. Wire-in section: states which existing components it connects to.
9. Control-room updates: 03_BACKLOG state, 08_SESSIONS entry, 07_METRICS if a metric moved.
10. GO/NO-GO-relevant checks still green.

---

## 10. RISK LINKAGE

All build-phase risks tracked in `/control-room/05_RISKS.md` (pre-seeded register in fixes.md Part C). Module-specific risks to add during PLAN review: RBAC bypass in new routers (P0), Gantt editor conflicting writes (P1), announcement spam loops (P2), CSV import injection (P3).

---

## 11. SYSTEM ARCHITECTURE (target)

```
                    ┌────────────────────────────────────────────┐
                    │              Next.js 14 Cockpit             │
                    │  board / gantt / planner / crew / safety /  │
                    │  assets / kpi / commercial / admin / public │
                    └──────────────────┬─────────────────────────┘
                                       │ TanStack Query (REST)
   collector/ ──► ┌────────────────────▼───────────────────────┐
   (RapidAPI,     │                FastAPI core                 │
   Open-Meteo)    │  auth+RBAC ► audit ► routers (A–H)          │
                  │        ► notification helper (I4)           │
                  │        ► Safety Interlock gate (D1) ◄── safety/ (zero ML)
                  └───────┬───────────────┬───────────────┬─────┘
                          │               │               │
                  ┌───────▼──────┐ ┌──────▼───────┐ ┌─────▼─────────┐
                  │ SQLite WAL   │ │ ml/          │ │ engine/       │
                  │ ~45 tables   │ │ GRU·LGBM·CQR │ │ optimizer·SimPy│
                  │ + backups/   │ │ PSI·dwell·crowd│ │ scanner·autopsy│
                  └──────────────┘ └──────────────┘ └─────┬─────────┘
                                                          │
                                            notifications/ OpenWA→WhatsApp/SMS
                                            G1 PIDS feed · G2 TTS/PA hook
```

---

## 12. EXECUTION — per-module workflow

1. `BOOT` prompt (fixes.md D.2.1) → confirm top task = next module in phase order.
2. Paste **Master Build Prompt** (fixes.md §4) with `BUILD MODULE <ID>` from this file.
3. Review the plan Claude presents → approve → review implementation → `WRAP` → commit.
4. Phase complete → GO/NO-GO GATE → next phase.
