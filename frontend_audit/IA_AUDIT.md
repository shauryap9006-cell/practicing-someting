# RailTwin-X Phase 2: Information Architecture (IA) Audit
**Auditors:** Brutal Senior Product Designer · Senior Frontend Architect · First-Time User Advocate

---

## 2.1 NAV REALITY & ERP DISTRACTION

### The Actual Navigation Structure
Currently, RailTwin-X splits its world into two disjointed universes:

```
[PUBLIC UNIVERSE] (No unified nav; links scattered across buttons & modals)
  ├── / (Landing Page)
  │     ├── Header: "Live Corridor" (#corridor-live), "The Line" (#the-line), "v3 Model Proof" (/dashboard/model)
  │     ├── "Track Your Train →" (Button) -> Opens TrackTrainModal (752 LOC overlay)
  │     ├── "Station Login" (Button) -> /login
  │     └── Footer: /privacy, /terms, /kiosk
  ├── /track & /track/:trainNo (PassengerTrackerPage — 1,014 LOC)
  ├── /kiosk (KioskPage)
  └── [ORPHAN DEMO PAGES] (Reachable ONLY via DemoStepperNav or secret URL):
        ├── /foresight (ForesightConsolePage)
        ├── /compare (ComparatorPage)
        ├── /time-machine & /replay (TimeMachinePage)
        ├── /cascade (RippleBoardPage)
        └── /model-card (HonestModelCardPage)

[OPERATOR DASHBOARD UNIVERSE] (`DashboardLayout.tsx` + `Sidebar.tsx`)
  ├── Primary Navigation (8 items):
  │     ├── [1] Overview (`/dashboard`)
  │     ├── [2] Live Map Radar (`/dashboard/live-map`)
  │     ├── [3] Trains & Why-Late (`/dashboard/trains`)
  │     ├── [4] Platform Gantt (`/dashboard/gantt`)
  │     ├── [5] Advisories (`/dashboard/advisories`)
  │     ├── [6] Model & Proof (`/dashboard/model`)
  │     ├── [7] Tamper-Evident Ledger (`/dashboard/audit`)
  │     └── [8] Public Kiosk (`/kiosk`)
  └── Advanced Operations (10 items across 2 accordion groups):
        ├── Group 1: Network & Track
        │     ├── [9]  Timetable Manager (`/dashboard/timetable`)
        │     ├── [10] Block Sections (`/dashboard/blocks`)
        │     ├── [11] Yard Diagram (`/dashboard/yard-map`)
        │     └── [12] Corridor GIS (`/dashboard/corridor-gis`)
        └── Group 2: Safety & Risk Controls
              ├── [13] TSR / Caution Orders (`/dashboard/safety/tsr`)
              ├── [14] Incident Register (`/dashboard/safety/incidents`)
              ├── [15] Crew Rosters & Duty (`/dashboard/crew`)
              ├── [16] Track-Block Gantt (`/dashboard/maintenance`)
              ├── [17] Corridor Handoff (`/dashboard/corridor-coordination`)
              └── [18] DFC Precedence (`/dashboard/dfc-coordination`)
```

### Quantifying the Off-Mission Sprawl
* **Total Sidebar Nav Items:** **18 items**
* **Directly addressing SIH PS 26028 (Dynamic ETA, Quantile Cones, Delay Autopsy, Foresight):**
  * `Overview` (partial)
  * `Live Map Radar`
  * `Trains & Why-Late`
  * `Model & Proof`
  * `Tamper-Evident Ledger`
  * Total on-mission: **5 of 18 items (27.8%)**
* **Off-mission Operator ERP Modules:**
  * `Timetable Manager` (WTT draft editor)
  * `Block Sections` (manual section occupation monitor)
  * `Yard Diagram` (static JSON relay toy)
  * `Corridor GIS` (duplicate SVG map)
  * `TSR / Caution Orders` (safety orders with broken `/lift` route)
  * `Incident Register` (cattle trespass logger)
  * `Crew Rosters & Duty` (loco pilot HR hours)
  * `Track-Block Gantt` (civil engineering work possessions)
  * `Corridor Handoff` (inter-station locks with broken `/ack` route)
  * `DFC Precedence` (freight loop hold table)
  * `Platform Gantt` (station berthing with fake `setTimeout` MILP solver)
  * Total off-mission: **11 of 18 items (61.1% OFF-MISSION)**

> **Brutal Verdict:** **11 out of 18 nav items (61.1%) are irrelevant operator ERP distractions.** Meanwhile, the 5 core surfaces that win hackathons (`/compare`, `/foresight`, `/time-machine`, `/cascade`, `/model-card`) are completely absent from the sidebar!

---

## 2.2 THE MONEY-SHOT PATH (Clicks & Seconds from App Open)

Target for an evaluation judge: **≤1 click to witness each core differentiator.**

| Differentiator Surface | Path from App Open (`/`) | Click Count | Latency / Friction | Gap vs Target (≤1 Click) |
| :--- | :--- | :---: | :---: | :---: |
| **D1: Calibrated p10–p50–p90 Uncertainty Cone** | Open `/` -> Click "Station Login" (`/login`) -> Click "Station Master" demo tile -> Click "Sign In" (`/dashboard`) -> Click "Trains & Why-Late" (`/dashboard/trains`) -> Click "12301" row -> Scroll to ConfidenceBand. | **5 clicks** | ~12 seconds | **+4 clicks (FAILURE)**. BURIED. |
| **D2: 3–6h Lookahead Horizon Foresight** | Not reachable from any menu. Judge must manually edit browser address bar to `/foresight` or `/compare`! | **∞ (Unlinked)** | Requires typing URL | **CRITICAL FAILURE**. |
| **D3: Causal Why-Late Autopsy** | Open `/` -> Click "Track Your Train" button -> `TrackTrainModal` opens -> Click "12301" tile -> Navigates to `/track/12301` -> Scroll down -> Click "Why is this train delayed?" accordion. | **3 clicks** | ~6 seconds | **+2 clicks**. Needs to be visible immediately without accordion gating. |
| **D4: Cascade & Connection Custody** | Not reachable from sidebar or landing nav. Must type `/cascade` or reach via `DemoStepperNav` from another demo page. | **∞ (Unlinked)** | Requires typing URL | **CRITICAL FAILURE**. |
| **D5: Hash-Chained Ledger Receipt & Auto-Grading** | Open `/` -> Click "Station Login" -> Select role -> Click "Sign In" -> Click "Tamper-Evident Ledger" (`/dashboard/audit`) -> Click "Verify Integrity" (which returns a fake mock hash on failure!). | **5 clicks** | ~14 seconds | **+4 clicks (FAILURE)**. Live ledger proof is locked in orphan `/model-card`. |

---

## 2.3 DUPLICATION MAP (Redundant & Overlapping Surfaces)

The codebase suffers from 4 massive duplication clusters that divide development focus and bloat the bundle:

### Cluster 1: Train Journey & Autopsy Triplication
* `web/src/pages/public/PassengerTrackerPage.tsx` (1,014 LOC)
* `web/src/pages/dashboard/TrainDetailPage.tsx` (357 LOC)
* `web/src/components/passenger/TrackTrainModal.tsx` (752 LOC)
* **Reality:** All three components fetch the exact same train telemetry, render the same stations, and parse the same why-late autopsy.
* **Proposed Merge:** **Delete all three; build ONE unified target page `/t/:trainNo`** with a role lens toggle (Passenger View / Staff Telemetry Lens).

### Cluster 2: Live Network & Corridor Map Duplication
* `web/src/pages/dashboard/LiveMapPage.tsx` (427 LOC)
* `web/src/pages/dashboard/network/CorridorMapPage.tsx` (249 LOC)
* `web/src/pages/dashboard/network/YardDiagramPage.tsx` (264 LOC)
* **Reality:** `LiveMapPage` renders real `/v1/live/positions`. `CorridorMapPage` renders a duplicate SVG track with one-shot stale polling. `YardDiagramPage` is a completely hardcoded static array in code.
* **Proposed Merge:** **Delete `CorridorMapPage` and `YardDiagramPage`; promote `LiveMapPage` into the single canonical target `/network` corridor view.**

### Cluster 3: Shock Injection & Comparator Duplication
* `web/src/pages/foresight/ForesightConsolePage.tsx` (680 LOC)
* `web/src/pages/demo/ComparatorPage.tsx` (327 LOC)
* **Reality:** Both implement identical shock injection state (`SIGNAL_HOLD`, `TSR_ACTIVE`, `RAKE_DELAY`, `WEATHER_FOG`, `reset-events`) and render the B1/B2 vs RailTwin-X table.
* **Proposed Merge:** **Retain `ComparatorPage` as the target `/compare` page.** Move the 6h lookahead congestion radar from `ForesightConsolePage` into `/network`.

### Cluster 4: Model Validation & Ledger Scoreboard Duplication
* `web/src/pages/model/HonestModelCardPage.tsx` (340 LOC)
* `web/src/pages/dashboard/ModelPage.tsx` (187 LOC)
* `web/src/pages/dashboard/AuditPage.tsx` (195 LOC)
* **Reality:** `HonestModelCardPage` contains live out-of-sample metrics, ledger tip hash, and real SHA-256 chain verification. `ModelPage` and `AuditPage` in the dashboard render stale mockStore duplicates.
* **Proposed Merge:** **Delete `ModelPage` and `AuditPage`; promote `HonestModelCardPage` as the single canonical target `/proof` page.**

---

## 2.4 ROLE MODEL & ACCESS CONTROL AUDIT

### Is Staff Content Actually Gated?
1. **The Client-Side Illusion:** Authentication is guarded exclusively by `AuthGuard` (`web/src/components/layout/AuthGuard.tsx:13`):
   ```typescript
   export function AuthGuard({ children }: { children: React.ReactNode }) {
     const session = getCurrentSession();
     if (!session && !isExplicitDemoMode()) {
       return <Navigate to="/login" replace />;
     }
     return <>{children}</>;
   }
   ```
2. **The Bypass:** If `?demo=1` or `localStorage.getItem('railtwin_demo_mode') === 'true'`, `AuthGuard` completely opens all private routes without a token!
3. **Role Enforcement on Pages:** Zero! Although `ROLE_CONFIGS` in `mock/auth.ts` defines `allowedGroups` for 9 roles (Station Master, Controller, Crew Controller, etc.), **not a single page in `web/src/pages/dashboard/` checks permissions before rendering!** A `viewer` or `tte` can click into `TSRRegistryPage` or `TimetablePage` and execute write actions.
4. **Passenger Exposure:** A passenger typing `/track` is one click away from `/kiosk`, and typing any `/dashboard/*` route in demo mode instantly grants full administrative views.

---

## 2.5 ENTRY POINTS & FIRST-CLICK TRAJECTORY

### How does a user start?
* **Landing Page Entry (`/`):**
  * There is **no train search input on the landing hero**!
  * Instead, there is a button: `"Track Your Train →"`.
  * Clicking it opens `TrackTrainModal`, which requires the user to type a 5-digit train number (e.g. `12301`) or click one of 4 preset pills (`12301`, `12004`, `22436`, `12424`).
  * Selecting a train navigates to `/track/12301` (`PassengerTrackerPage`).
* **The Disconnect:**
  * Typing `12301` on the landing page lands the user on the sprawling 1,014-LOC passenger tracker.
  * Searching `12301` from the dashboard command palette lands the user on `/dashboard/trains/12301` (`TrainDetailPage`).
  * **Result:** Two users looking up the exact same train get two completely different, inconsistent visual experiences depending on where they entered!

---

*End of Phase 2 Information Architecture Audit. Proceed to Phase 3 Design System Audit.*
