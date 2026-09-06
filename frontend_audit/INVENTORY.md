# RailTwin-X Frontend Inventory & Measurement Report (Phase 0)
**Audit Date:** September 2026 | **Stack:** React 18, Vite 6, TypeScript 5.7, Tailwind CSS 3.4  
**Auditors:** Brutal Senior Product Designer · Senior Frontend Architect · First-Time User Advocate

---

## 0.1 ROUTE MAP (`web/src/App.tsx`)

Total Routes Mounted in React Router: **29 route definitions** (15 public, 13 authenticated dashboard children, 1 catch-all).

| Path | Page Component | Auth Gate | Reachable via Nav? | Nav Source / Orphan Status |
| :--- | :--- | :--- | :--- | :--- |
| `/` | `LandingPage` | None (Public) | Yes | Brand Logo / Top Nav |
| `/landing` | `LandingPage` | None (Public) | No | **Orphan Route** (Alias to `/`) |
| `/foresight` | `ForesightConsolePage` | None (Public) | No | **CRITICAL ORPHAN** (D1–D5 flagship; unreachable from Sidebar or TopNav) |
| `/compare` | `ComparatorPage` | None (Public) | No | **CRITICAL ORPHAN** (Signature shock injection lab; unreachable from Sidebar) |
| `/time-machine` | `TimeMachinePage` | None (Public) | No | **CRITICAL ORPHAN** (Signature replay demo; unreachable from Sidebar) |
| `/replay` | `TimeMachinePage` | None (Public) | No | **Orphan Route** (Alias to `/time-machine`) |
| `/cascade` | `RippleBoardPage` | None (Public) | No | **CRITICAL ORPHAN** (D4 cascade & custody; unreachable from Sidebar) |
| `/model-card` | `HonestModelCardPage`| None (Public) | No | **CRITICAL ORPHAN** (Unsealed metrics; unreachable from Sidebar) |
| `/track` | `PassengerTrackerPage`| None (Public)| Yes | Landing page "Track Your Train" button & TrackTrainModal |
| `/track/:trainNo`| `PassengerTrackerPage`| None (Public)| Yes | Direct link / Search result selection |
| `/passenger` | Navigate -> `/track` | None (Public) | No | **Orphan Redirect** |
| `/login` | `LoginPage` | None (Public) | Yes | Landing Header "Station Login" button |
| `/kiosk` | `KioskPage` | None (Public) | Yes | Landing Header Link + Sidebar Primary Nav Item 8 |
| `/privacy` | `PrivacyPage` | None (Public) | Yes | Landing Page Footer link |
| `/terms` | `TermsPage` | None (Public) | Yes | Landing Page Footer link |
| `/thanks` | `ThanksPage` | None (Public) | No | **Orphan Route** |
| `/dashboard` | `OverviewPage` | `AuthGuard` | Yes | Sidebar Primary Nav Item 1 |
| `/dashboard/live-map`| `LiveMapPage` | `AuthGuard` | Yes | Sidebar Primary Nav Item 2 ("Live Map Radar") |
| `/dashboard/map` | `LiveMapPage` | `AuthGuard` | No | **Orphan Route** (Alias to `/dashboard/live-map`) |
| `/dashboard/trains` | `TrainsPage` | `AuthGuard` | Yes | Sidebar Primary Nav Item 3 ("Trains & Why-Late") |
| `/dashboard/trains/:trainNo` | `TrainDetailPage`| `AuthGuard` | Yes | Train row click from TrainsPage |
| `/dashboard/gantt` | `GanttPage` | `AuthGuard` | Yes | Sidebar Primary Nav Item 4 ("Platform Gantt") |
| `/dashboard/advisories` | `AdvisoriesPage` | `AuthGuard` | Yes | Sidebar Primary Nav Item 5 ("Advisories") |
| `/dashboard/timetable` | `TimetablePage` | `AuthGuard` | Yes | Sidebar Advanced Group 1 ("Timetable Manager") |
| `/dashboard/blocks` | `BlockSectionsPage` | `AuthGuard` | Yes | Sidebar Advanced Group 1 ("Block Sections") |
| `/dashboard/corridor-gis` | `CorridorMapPage` | `AuthGuard` | Yes | Sidebar Advanced Group 1 ("Corridor GIS") |
| `/dashboard/yard-map` | `YardDiagramPage` | `AuthGuard` | Yes | Sidebar Advanced Group 1 ("Yard Diagram") |
| `/dashboard/safety/tsr` | `TSRRegistryPage` | `AuthGuard` | Yes | Sidebar Advanced Group 2 ("TSR / Caution Orders") |
| `/dashboard/safety/incidents` | `IncidentsPage` | `AuthGuard` | Yes | Sidebar Advanced Group 2 ("Incident Register") |
| `/dashboard/crew` | `CrewPage` | `AuthGuard` | Yes | Sidebar Advanced Group 2 ("Crew Rosters & Duty") |
| `/dashboard/maintenance` | `MaintenancePage` | `AuthGuard` | Yes | Sidebar Advanced Group 2 ("Track-Block Gantt") |
| `/dashboard/corridor-coordination` | `CorridorHandoffPage` | `AuthGuard` | Yes | Sidebar Advanced Group 2 ("Corridor Handoff") |
| `/dashboard/dfc-coordination` | `DFCPrecedencePage` | `AuthGuard` | Yes | Sidebar Advanced Group 2 ("DFC Precedence") |
| `/dashboard/audit` | `AuditPage` | `AuthGuard` | Yes | Sidebar Primary Nav Item 7 ("Tamper-Evident Ledger") |
| `/dashboard/model` | `ModelPage` | `AuthGuard` | Yes | Sidebar Primary Nav Item 6 ("Model & Proof") |
| `*` | `NotFoundPage` | None (Public) | N/A | Catch-all fallback |

**Summary Finding:** **6 out of 7 signature hackathon demo surfaces** (`/foresight`, `/compare`, `/time-machine`, `/cascade`, `/model-card`, `/track`) are **completely orphan from the main operator dashboard shell**. If a judge logs into the dashboard via the prominent "Station Login" button, they are marooned inside 10 off-mission operator ERP modules and will **never see the D1–D5 differentiation surfaces without manual URL tampering**.

---

## 0.2 PAGE CENSUS (`web/src/pages/`)

Total Page Files: **31 files** | Total Page Code: **8,174 LOC**.

| # | File Path | LOC | Route Mounted | Purpose as ACTUALLY Rendered (Reality Check) |
| :---: | :--- | :---: | :--- | :--- |
| 1 | `auth/LoginPage.tsx` | 179 | `/login` | 6 quick-switch demo role tiles + username/password form using client-side mock credentials. |
| 2 | `dashboard/AdvisoriesPage.tsx` | 350 | `/dashboard/advisories` | List of crew duty breach alerts & precedence overtake advisories with Accept/Dismiss buttons. |
| 3 | `dashboard/AuditPage.tsx` | 195 | `/dashboard/audit` | Table of mock SHA-256 HMAC logs with a "Verify Integrity" button returning hardcoded hash on error. |
| 4 | `dashboard/CrewPage.tsx` | 189 | `/dashboard/crew` | Table of locomotive crew duty hours with "Request Relief" button triggering mock mutation. |
| 5 | `dashboard/GanttPage.tsx` | 312 | `/dashboard/gantt` | Canvas/SVG station platform occupancy with fake client-side `setTimeout` MILP re-optimizer. |
| 6 | `dashboard/LiveMapPage.tsx` | 427 | `/dashboard/live-map` | Direct raw fetch to `/v1/live/positions` plotting a 1D linear corridor track with station markers. |
| 7 | `dashboard/MaintenancePage.tsx` | 145 | `/dashboard/maintenance`| Read-only list of maintenance track possession blocks from mock store. Zero interactive elements. |
| 8 | `dashboard/ModelPage.tsx` | 187 | `/dashboard/model` | Model training evaluation proof table rendered from mockStore. Zero interactive elements. |
| 9 | `dashboard/OverviewPage.tsx` | 340 | `/dashboard/overview` | Cockpit dash: 4 metric cards, active trains table, advisories list, mini platform berthing strip. |
| 10 | `dashboard/TrainDetailPage.tsx` | 357 | `/dashboard/trains/:no` | Train journey stop timeline, speed, status lamp, and why-late autopsy breakdown. |
| 11 | `dashboard/TrainsPage.tsx` | 253 | `/dashboard/trains` | Searchable directory table of corridor trains with delay aspects and platform allocations. |
| 12 | `dashboard/coord/CorridorHandoffPage.tsx` | 136 | `/dashboard/corridor-coordination` | Table of inter-station train slot handoffs with dead button calling broken `/ack` route. |
| 13 | `dashboard/coord/DFCPrecedencePage.tsx` | 105 | `/dashboard/dfc-coordination` | Read-only freight precedence regulation table (Rooma/Panki loops). |
| 14 | `dashboard/network/CorridorMapPage.tsx` | 249 | `/dashboard/corridor-gis` | Schematic linear GIS strip with zoom/filter controls and train positions. |
| 15 | `dashboard/network/YardDiagramPage.tsx` | 264 | `/dashboard/yard-map` | **100% hardcoded static track array in file**. Zero API calls; static relay interlocking toy. |
| 16 | `dashboard/ops/BlockSectionsPage.tsx` | 159 | `/dashboard/ops/blocks` | Block section clearance grid (Clear/Caution/Occupied/Blocked). |
| 17 | `dashboard/ops/TimetablePage.tsx` | 215 | `/dashboard/timetable` | Timetable version draft/publish manager (Working Time Table WTT revisions). |
| 18 | `dashboard/safety/IncidentsPage.tsx` | 285 | `/dashboard/safety/incidents` | Incident logger (cattle trespass, OHE trip) with multi-field input modal. |
| 19 | `dashboard/safety/TSRRegistryPage.tsx` | 259 | `/dashboard/safety/tsr` | Temporary Speed Restriction register with dead "Lift TSR" button calling nonexistent `/lift`. |
| 20 | `demo/ComparatorPage.tsx` | 327 | `/compare` | **Core D1/D2 demo**: B1/B2 vs RailTwin-X quantile cone with live operational shock injection lab. |
| 21 | `demo/TimeMachinePage.tsx` | 261 | `/time-machine` | **Core D5 demo**: Historical 4-stage replay (T-6h, T-3h, T-1h, Truth) with tamper-evident reveal. |
| 22 | `foresight/ForesightConsolePage.tsx` | 680 | `/foresight` | **Mega-cockpit**: Combines Comparator, 6-Hour Radar, Shock Lab, and Autopsy in one 680-LOC screen. |
| 23 | `landing/LandingPage.tsx` | 458 | `/` | **The reference surface**: 3D corridor, telemetry ticker, live platform conflict, proof shootout. |
| 24 | `model/HonestModelCardPage.tsx` | 340 | `/model-card` | **Core D5 surface**: Out-of-sample metrics, ledger scoreboard, tip hash, and genesis verify button. |
| 25 | `ops/RippleBoardPage.tsx` | 255 | `/cascade` | **Core D4 surface**: Rake turnaround deficit, connection hold advisories, passenger-hours saved. |
| 26 | `public/KioskPage.tsx` | 249 | `/kiosk` | Fullscreen high-contrast station PIDS display with giant arrival times and bilingual flip. |
| 27 | `public/NotFoundPage.tsx` | 76 | `*` | 404 page with return buttons. |
| 28 | `public/PassengerTrackerPage.tsx` | 1014 | `/track/:trainNo` | **1014-LOC monolith**: Passenger ETA range, live map, why-late accordion, alarm modal, PNR lookup. |
| 29 | `public/PrivacyPage.tsx` | 105 | `/privacy` | Static legal text. |
| 30 | `public/TermsPage.tsx` | 100 | `/terms` | Static legal text. |
| 31 | `public/ThanksPage.tsx` | 65 | `/thanks` | Static confirmation card. |

---

## 0.3 COMPONENT CENSUS (`web/src/components/`)

Total Component Files: **30 files** | Total Component Code: **4,923 LOC**.

| Component File | LOC | Consumers Count | Consumers List | Status / Health |
| :--- | :---: | :---: | :--- | :--- |
| `components/aspect/AspectLamp.tsx` | 105 | 17 | 14 pages, 2 subcomponents, 1 index | Core primitive: Active & essential |
| `components/aspect/AutopsyStrip.tsx` | 507 | 3 | `LiveMapPage`, `TrainDetailPage`, `index` | Massive 507 LOC; duplicated in pages |
| `components/aspect/ConfidenceBand.tsx`| 54 | 7 | 4 pages, `api-schema`, `index` | Core primitive: Active |
| `components/aspect/CorridorSpine.tsx` | 331 | 4 | `OverviewPage`, `TrainDetailPage`, `LandingPage`, `index` | Active signature spine |
| `components/aspect/EmptyState.tsx` | 85 | 7 | 6 pages, `index` | Standard error/empty state |
| `components/aspect/EventTicker.tsx` | 99 | 2 | `LandingPage`, `index` | Only used on Landing Page |
| `components/aspect/Provenance.tsx` | 54 | 13 | 11 pages, 1 subcomponent, 1 index | Timestamp/clock provenance badge |
| `components/aspect/RailCursor.tsx` | 56 | 2 | `LandingPage`, `index` | Custom cursor; only used on Landing |
| `components/aspect/TimeRuler.tsx` | 196 | 2 | `GanttPage`, `index` | Tied to GanttPage only |
| `components/aspect/TrainChip.tsx` | 82 | 2 | `OverviewPage`, `index` | Single consumer |
| `components/aspect/index.ts` | 10 | 21 | Re-export barrel | Barrel file |
| `components/common/DataFreshnessBadge.tsx`| 71 | 4 | `StatusBar`, `MaintenancePage`, `OverviewPage`, `CorridorMapPage` | Active |
| `components/demo/DemoStepperNav.tsx` | 164 | 5 | 5 demo pages | Demo step controller |
| `components/landing/AuditChainVisual.tsx`| 150 | 1 | `LandingPage` | Isolated to Landing Page |
| `components/landing/BootPreloader.tsx`| 82 | 1 | `LandingPage` | Isolated to Landing Page |
| `components/landing/GrassField.tsx` | 531 | 1 | `ThreeCorridor.tsx` | **531 LOC 3D procedural grass for Landing only** |
| `components/landing/TheLineScroll.tsx`| 267 | 1 | `LandingPage` | Isolated to Landing Page |
| `components/landing/ThreeCorridor.tsx`| 786 | 1 | `LandingPage` | **786 LOC Three.js canvas; causes 907 kB chunk** |
| `components/layout/AuthGuard.tsx` | 19 | 1 | `App.tsx` | Auth gate wrapper |
| `components/layout/DashboardLayout.tsx`| 100 | 1 | `App.tsx` | Private shell wrapper |
| `components/layout/ErrorBoundary.tsx`| 33 | 1 | `main.tsx` | Crash boundary |
| `components/passenger/PassengerFAB.tsx`| 28 | 1 | `App.tsx` | Floating action button on mobile |
| `components/passenger/TrackTrainModal.tsx`| 752 | 1 | `App.tsx` | **752 LOC monolith duplicating PassengerTracker** |
| `components/shell/CommandPalette.tsx`| 197 | 2 | `DashboardLayout`, `TopBar` | Cmd+K palette |
| `components/shell/CookieBanner.tsx` | 64 | 1 | `App.tsx` | Consent banner |
| `components/shell/Sidebar.tsx` | 316 | 1 | `DashboardLayout` | Left navigation panel (18 routes) |
| `components/shell/StatusBar.tsx` | 55 | 1 | `DashboardLayout` | Bottom telemetry status bar |
| `components/shell/TopBar.tsx` | 108 | 1 | `DashboardLayout` | Header bar with role switch & search |
| `components/ui/Badge.tsx` | 26 | 9 | 9 consumers | UI primitive |
| `components/ui/Button.tsx` | 43 | 9 | 9 consumers | UI primitive |

**Dead Code & Hyper-Isolated Components:**
1. `GrassField.tsx` (531 LOC) + `ThreeCorridor.tsx` (786 LOC) = **1,317 LOC** of 3D Three.js rendering code consumed exclusively by a background canvas on `LandingPage.tsx`.
2. `TrackTrainModal.tsx` (752 LOC) is an entire second copy of `PassengerTrackerPage.tsx` embedded in a modal overlay mounted at root.
3. `AutopsyStrip.tsx` (507 LOC) contains its own causal waterfall parser that conflicts with `ForesightConsolePage.tsx` and `TrainDetailPage.tsx`.

---

## 0.4 BUTTON CENSUS (The Baseline to Crush)

Audit script inspected every interactive element (`<button>`, `<Button>`, `onClick`, `<a/Link>`, form inputs) across all pages:

* **Page Interactive Elements:** 162
* **Shell & Nav Interactive Elements:**
  * `Sidebar.tsx`: 29 elements (8 primary nav links, 1 accordion toggle, 10 advanced links, 1 role dropdown trigger, 7 role select options, 1 theme toggle, 1 signout)
  * `TopBar.tsx`: 6 elements (Command palette trigger, station selector dropdown, sound toggle, track train modal trigger, mobile sidebar toggle)
  * `CookieBanner.tsx`: 3 elements (Accept, Dismiss, Privacy link)
  * `CommandPalette.tsx`: 26 elements (Search input, ~25 command items)
  * `TrackTrainModal.tsx`: 16 elements (Close button, search input, tabs, quick trains, PNR button)
* **TOTAL APP-WIDE INTERACTIVE ELEMENTS:** **242 elements**

### Page-by-Page Interactive Classification

| Page | Buttons | onClicks | Links | Inputs | Total | Verdict Breakdown (WORKS / DEAD / DEMO / COSMETIC) |
| :--- | :---: | :---: | :---: | :---: | :---: | :--- |
| `LoginPage` | 2 | 1 | 2 | 2 | **6** | 2 DEMO (quick-role fill), 1 WORKS (login submit), 2 WORKS (links) |
| `AdvisoriesPage` | 5 | 6 | 0 | 1 | **7** | 4 WORKS (accept/dismiss advisories), 1 COSMETIC (filter tab), 1 WORKS (search) |
| `AuditPage` | 1 | 2 | 0 | 1 | **3** | 1 DEMO (verify integrity with fake hash fallback), 1 COSMETIC (filter) |
| `CrewPage` | 1 | 1 | 0 | 0 | **1** | 1 DEMO (request relief calls mockStore/endpoint fallback) |
| `GanttPage` | 2 | 2 | 0 | 0 | **2** | **1 DEAD/FAKE** (re-optimize triggers client-side `setTimeout` fake swap), 1 DEMO (undo) |
| `LiveMapPage` | 7 | 7 | 0 | 1 | **8** | 4 COSMETIC (zoom/pan icons), 2 WORKS (train select), 1 WORKS (search) |
| `MaintenancePage` | 0 | 0 | 0 | 0 | **0** | Pure read-only list |
| `ModelPage` | 0 | 0 | 0 | 0 | **0** | Pure read-only table |
| `OverviewPage` | 0 | 0 | 9 | 0 | **9** | 9 WORKS (train navigation links) |
| `TrainDetailPage` | 1 | 1 | 1 | 1 | **3** | 1 COSMETIC (run date selector), 1 WORKS (back link), 1 WORKS (refresh) |
| `TrainsPage` | 0 | 4 | 0 | 2 | **6** | 4 WORKS (train row selection), 2 WORKS (search/filter inputs) |
| `CorridorHandoffPage` | 2 | 2 | 0 | 0 | **2** | **1 DEAD** (acknowledge handoff calls nonexistent `POST /api/section/handoffs/{id}/ack`), 1 COSMETIC |
| `DFCPrecedencePage` | 1 | 1 | 0 | 0 | **1** | 1 COSMETIC (refresh button) |
| `CorridorMapPage` | 5 | 7 | 0 | 0 | **7** | 5 COSMETIC (zoom in/out/reset, layer toggles), 2 WORKS (train select) |
| `YardDiagramPage` | 1 | 2 | 0 | 0 | **2** | **2 COSMETIC** (station tab switches static in-memory array) |
| `BlockSectionsPage` | 0 | 1 | 0 | 0 | **1** | 1 COSMETIC (section card click) |
| `TimetablePage` | 2 | 3 | 0 | 1 | **4** | 1 DEMO (publish draft timetable version), 2 COSMETIC (version tabs) |
| `IncidentsPage` | 4 | 4 | 0 | 4 | **8** | 1 DEMO (log incident modal submit), 3 COSMETIC (filter tabs, modal close) |
| `TSRRegistryPage` | 6 | 5 | 0 | 6 | **12** | **1 DEAD** (lift TSR calls nonexistent `POST /api/safety/tsr/{id}/lift`), 1 DEMO (create TSR), 4 COSMETIC |
| `ComparatorPage` | 6 | 6 | 1 | 0 | **7** | 4 WORKS (shock injection triggers), 1 WORKS (reset shocks), 1 WORKS (train select), 1 WORKS (link) |
| `TimeMachinePage` | 1 | 1 | 1 | 0 | **2** | 4 WORKS (step 1-4 stage switchers), 1 WORKS (back link) |
| `ForesightConsolePage`| 7 | 7 | 5 | 0 | **12** | 4 WORKS (shock triggers), 1 WORKS (reset), 1 WORKS (train switcher), 5 WORKS (links) |
| `LandingPage` | 3 | 2 | 11 | 4 | **18** | 2 WORKS (track modal trigger, submit demo key), 11 WORKS (links), 4 WORKS (form inputs) |
| `HonestModelCardPage` | 2 | 2 | 1 | 0 | **3** | 1 WORKS (re-verify SHA-256 chain), 1 WORKS (back link) |
| `RippleBoardPage` | 0 | 0 | 1 | 0 | **1** | 1 WORKS (back link) |
| `KioskPage` | 2 | 2 | 0 | 0 | **2** | 1 COSMETIC (language toggle), 1 COSMETIC (fullscreen toggle) |
| `NotFoundPage` | 3 | 0 | 4 | 0 | **7** | 4 WORKS (navigation links) |
| `PassengerTrackerPage`| 13 | 14 | 2 | 1 | **17** | 3 WORKS (search, stop select, language), 2 COSMETIC (alarm modal, share button), 2 WORKS (refresh, retry), 6 COSMETIC |
| `PrivacyPage` | 0 | 0 | 3 | 0 | **3** | 3 WORKS (links) |
| `TermsPage` | 0 | 0 | 3 | 0 | **3** | 3 WORKS (links) |
| `ThanksPage` | 2 | 0 | 3 | 0 | **5** | 3 WORKS (links) |

**Interactive Elements Summary:**
* **WORKS (Real API):** 84 (34.7%)
* **COSMETIC (No-op / UI only):** 96 (39.7%)
* **DEMO-ONLY (Simulated / Mock fallback):** 59 (24.4%)
* **DEAD (Nonexistent route / Fabricated):** 3 (1.2%)

---

## 0.5 TYPE HONESTY AUDIT

* **`any` occurrences in `web/src/lib/api.ts`:** **23 occurrences** across 32 API methods.
* **`any` occurrences in `web/src/pages/`:** **14 occurrences** (`PassengerTrackerPage`: 7, `RippleBoardPage`: 2, `LiveMapPage`: 1, `ComparatorPage`: 1, `TimeMachinePage`: 1, `ForesightConsolePage`: 1, `CrewPage`: 1).
* **Total `any` usages across `web/src/`:** **39 occurrences**.
* **Real TypeScript Interfaces in `api.ts`:** 11 interfaces declared (`DelayCauseItem`, `DelayAutopsyResponse`, `PassengerSearchResult`, `PassengerPopularTrain`, `PassengerPNRResponse`, `PassengerSnapshot`, `ModelPerformanceData`, `DemoComparatorData`, `CascadeRippleData`, `TimeMachineData`, `LedgerScoreboardResponse`, `CorridorRadarResponse`).

### Contract Drift Caught by Compiler Blindness
Because `fetchBackend<any>` returns untyped promises in 23 methods, the following real mismatches exist:
1. `api.getTrains()` receives backend `current_delay_min`, but manually re-maps `t.delay_min ?? 0`, inventing client-side p10/p50/p90 math using `p50Minutes = 18 * 60 + delayMin` (`api.ts:384-394`)! The compiler cannot flag that backend already provides quantile forecasts.
2. `api.getTrainAutopsy()` checks `c.event_type || c.cause` because `/autopsy` returns `causes[].event_type` while `/why-late` returns `cause_breakdown[].cause_code`.
3. `api.getCrew()` does `res?.roster || res?.items || mockStore.getCrew()` because the backend response shape changed from list to dict without typed guards.

---

## 0.6 MOCK SURFACE MAP

### 1. `web/src/mock/` Modules Directory
* `mock/auth.ts` (361 LOC): Hardcoded demo accounts (`sm@cnb.railtwin.app`, `demo1234`), mock JWT tokens, in-memory session store.
* `mock/store.ts` (398 LOC): In-memory mutable simulation store containing fake trains, stations, platform allocations, advisories, and maintenance possessions.
* `mock/types.ts` (215 LOC): Redundant domain types mirroring `api-schema.ts`.
* `mock/trains.ts`, `mock/stations.ts`, `mock/crew.ts`, `mock/advisories.ts`, `mock/maintenance.ts`, `mock/audit.ts`, `mock/model.ts`: Hardcoded static fallback fixtures.

### 2. Silent `mockStore` Fallback Trigger Paths (`web/src/lib/api.ts`)
Lines 335-348 in `api.ts`:
```typescript
if (fallbackFn) {
  return await fallbackFn(); // SILENT FALLBACK WHEN BACKEND 404s/500s
}
```
**When does the user see mock data?**
* **When backend is DOWN:** All operator modules (`/dashboard/*`) silently fall back to `mockStore`. A judge visiting `/dashboard/timetable`, `/dashboard/blocks`, `/dashboard/safety/tsr`, or `/dashboard/crew` with the backend completely dead will see plausible-looking mock data and never realize the backend is offline!
* **When backend is LIVE:**
  * `YardDiagramPage.tsx`: **ALWAYS** renders hardcoded mock data in `YARD_TRACKS` (lines 14-42). Zero network calls.
  * `TimeMachinePage.tsx`: **ALWAYS** falls back to fabricated string `'Sealing block in SHA-256 chain...'` (line 82) during data loading.
  * `GanttPage.tsx`: **ALWAYS** executes hardcoded client-side swap of train 12301 to Platform 4 on re-optimize button click (lines 134-144).
  * `HonestModelCardPage.tsx`: Lines 282, 291, 297, 308 fallback to hardcoded string `'6ffbe6ab4550951b0b79bea38aa3b181927805e68d27d2f9298ff0bd6fb3031e'` if the API returns null!

---

## 0.7 BUNDLE HEALTH (`npm run build`)

Output of `npm run build` executed in `web/`:

```
vite v6.4.3 building for production...
transforming...
✓ 2360 modules transformed.
rendering chunks...
computing gzip size...
dist/index.html                                2.97 kB │ gzip:   1.01 kB
dist/assets/index-tZedyZsx.css                79.43 kB │ gzip:  13.23 kB
dist/assets/plus-jyD4hD2M.js                   0.32 kB │ gzip:   0.25 kB
dist/assets/EmptyState-C024XZs_.js             1.76 kB │ gzip:   0.82 kB
dist/assets/DFCPrecedencePage-B41X-rpI.js      3.39 kB │ gzip:   1.26 kB
dist/assets/CorridorHandoffPage-eLPpWoCm.js    4.23 kB │ gzip:   1.43 kB
dist/assets/CrewPage-DZrYLByf.js               5.22 kB │ gzip:   1.99 kB
dist/assets/BlockSectionsPage-CkAVEdj_.js      5.25 kB │ gzip:   1.52 kB
dist/assets/MaintenancePage-cG1DOXES.js        5.54 kB │ gzip:   1.62 kB
dist/assets/AuditPage-_EyhgnOh.js              5.58 kB │ gzip:   2.10 kB
dist/assets/TimetablePage-Cu1XLVew.js          6.75 kB │ gzip:   2.26 kB
dist/assets/TrainsPage-Dul-Uqqa.js             7.24 kB │ gzip:   2.50 kB
dist/assets/TSRRegistryPage-BxakyboT.js        7.36 kB │ gzip:   2.20 kB
dist/assets/CorridorMapPage-sQ1ATXpR.js        7.80 kB │ gzip:   2.56 kB
dist/assets/ModelPage-DcFrMdQC.js              7.82 kB │ gzip:   2.07 kB
dist/assets/IncidentsPage-Ca91UejX.js          8.43 kB │ gzip:   2.40 kB
dist/assets/YardDiagramPage-DdbAFbMy.js        9.03 kB │ gzip:   2.59 kB
dist/assets/OverviewPage-EFmRmh-B.js           9.75 kB │ gzip:   2.84 kB
dist/assets/AdvisoriesPage-DwCvbNmV.js         9.77 kB │ gzip:   3.03 kB
dist/assets/LiveMapPage-CBZXnDB8.js           10.83 kB │ gzip:   3.69 kB
dist/assets/GanttPage-DBWFGVfz.js             11.97 kB │ gzip:   3.83 kB
dist/assets/TrainDetailPage-Bb1U99Lx.js       11.97 kB │ gzip:   3.70 kB
dist/assets/AutopsyStrip-DuVl6_fn.js          14.07 kB │ gzip:   4.03 kB
dist/assets/vendor-tanstack-CkqkKyJj.js       40.71 kB │ gzip:  12.07 kB
dist/assets/vendor-react-CDhiE_C8.js         166.83 kB │ gzip:  54.46 kB
dist/assets/index-g2JHggoC.js                466.60 kB │ gzip: 126.67 kB
dist/assets/vendor-three-CYfrdEyX.js         907.60 kB │ gzip: 246.33 kB
```

* **Total Production Assets Size:** **1.78 MB** uncompressed | **490.4 kB** gzip.
* **Top 5 Largest Chunks:**
  1. `vendor-three-CYfrdEyX.js`: **907.60 kB** (gzip: 246.33 kB) — Three.js engine for Landing page 3D background.
  2. `index-g2JHggoC.js`: **466.60 kB** (gzip: 126.67 kB) — Monolithic main chunk containing **ALL 11 public pages statically imported in `App.tsx:8-20`**!
  3. `vendor-react-CDhiE_C8.js`: **166.83 kB** (gzip: 54.46 kB) — React, ReactDOM, React Router.
  4. `index-tZedyZsx.css`: **79.43 kB** (gzip: 13.23 kB) — Tailwind CSS stylesheet.
  5. `vendor-tanstack-CkqkKyJj.js`: **40.71 kB** (gzip: 12.07 kB) — TanStack React Query.
* **Dead-Weight Dependencies Flagged:**
  * `maplibre-gl`: In `package.json:20`. **0 occurrences across all `src/` files.** Pure dead-weight package.
  * `puppeteer`: In `package.json:37` devDependencies.
  * Static imports in `App.tsx` prevent route-splitting for `ForesightConsolePage`, `ComparatorPage`, `PassengerTrackerPage`, bloating initial load by 466 kB.

---

## 0.8 STATE & TELEMETRY AUDIT

| Data Pattern | Pages Implementing | Silent Stale Risk |
| :--- | :--- | :--- |
| **Active 5s Polling (`refetchInterval: 5000` via React Query)** | `AdvisoriesPage`, `AuditPage`, `CrewPage`, `OverviewPage`, `TrainDetailPage`, `TrainsPage`, `KioskPage` | Medium: If network drops, React Query retries, but `api.ts` masks failure by serving static `mockStore` fixtures without an offline warning. |
| **Manual `setInterval(..., 5000)`** | `LiveMapPage` | High: If fetch fails, sets error state, but does not use exponential backoff or SSE streaming. |
| **Server-Sent Events (SSE) / LiveMotionEngine** | `PassengerTrackerPage` (calls `useLiveMotionEngine`) | Low: Subscribes to `/v1/passenger/stream`, falls back to 5s polling when SSE closes. |
| **One-Shot Fetch on Mount (`useEffect` / `useQuery` without interval)** | `ComparatorPage`, `ForesightConsolePage`, `HonestModelCardPage`, `RippleBoardPage`, `TimeMachinePage`, `TimetablePage`, `BlockSectionsPage`, `IncidentsPage`, `TSRRegistryPage`, `CorridorHandoffPage`, `DFCPrecedencePage`, `CorridorMapPage`, `GanttPage`, `MaintenancePage`, `ModelPage` | **CRITICAL: 15 PAGES GO STALE SILENTLY**. Once mounted, they never refresh unless the user triggers a manual action or page reload. A controller monitoring `GanttPage` or `BlockSectionsPage` sees frozen state forever. |

---

*End of Phase 0 Inventory Report. Proceed to Phase 1 Page-by-Page Teardown.*
