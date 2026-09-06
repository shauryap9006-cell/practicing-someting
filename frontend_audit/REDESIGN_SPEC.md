# RailTwin-X Phase 6: The Minimal Frontend Redesign Spec (Part B)
**Architecture Design Document** | **Target Release:** RailTwin-X v3.1 (Minimalist ASPECT)  
**Authors:** Brutal Senior Product Designer · Senior Frontend Architect · First-Time User Advocate

---

## 6.1 TARGET INFORMATION ARCHITECTURE

The redesigned architecture collapses 31 fragmented, overlapping pages down to **5 Canonical Core Surfaces**:

```
                              RAILTWIN-X MINIMAL IA
                                        │
    ┌────────────────┬──────────────────┼──────────────────┬────────────────┐
    │                │                  │                  │                │
    ▼                ▼                  ▼                  ▼                ▼
   `/`          `/t/:trainNo`       `/network`         `/proof`         `/compare`
 LANDING        THE TRAIN PAGE    CORRIDOR TELEMETRY   HONESTY & LEDGER  SHOCK LAB
(Unchanged DNA) (Unified Single-   (Live Radar & 1D    (Model Metrics & (B1/B2 Baselines
                Train Truth)       Track Schematic)     Genesis Chain)   vs ML Cone)
                     │
         [Role Lens Toggle]
         ├── Passenger (Default Daylight)
         └── Staff / Dispatch Telemetry
                     │
                     ▼
                 `/console` (Hidden Behind Auth Gate — Collapsed Secondary Ops)
```

---

### TEXT WIREFRAME 1: `/t/:trainNo` — THE UNIFIED TRAIN PAGE

*Serves The Grandma, The Controller, and The Hackathon Judge from a single URL without authentication.*

```
+---------------------------------------------------------------------------------------+
|  RAILTWIN-X  [  Search Train # or Station...  ]      [Lens: Passenger | Staff Telemetry] |
+---------------------------------------------------------------------------------------+
|                                                                                       |
|  [ENDPOINT: GET /v1/passenger/snapshot?train={trainNo}]                              |
|  TRAIN #12301 · HOWRAH RAJDHANI EXPRESS                                               |
|  New Delhi (NDLS) -> Kanpur Central (CNB) -> Howrah (HWH)                            |
|                                                                                       |
|  +---------------------------------------------------------------------------------+  |
|  | 1. HEADLINE ARRIVAL RANGE (Biggest Type on Page)                                |  |
|  |                                                                                 |  |
|  |   EXPECTED AT KANPUR CENTRAL (CNB)                                              |  |
|  |   18:12 — 18:26                                            [+18m LATE]          |  |
|  |   80% Confidence Interval (p10–p90)                         Aspect: AMBER       |  |
|  |   Scheduled: 18:00 IST · Platform 4 (Re-Optimized)          Speed: 112 km/h     |  |
|  +---------------------------------------------------------------------------------+  |
|                                                                                       |
|  +---------------------------------------------------------------------------------+  |
|  | 2. WHY-LATE: CAUSAL DELAY AUTOPSY                                               |  |
|  | [ENDPOINT: GET /v1/trains/{trainNo}/why-late]                                   |  |
|  |                                                                                 |  |
|  |   "Signal regulation before Kanpur (+11m) + 40 km/h TSR renewal near Tundla (+7m)|  |
|  |                                                                                 |  |
|  |   [v] Expand Mathematical Breakdown                                             |  |
|  |   ----------------------------------------------------------------------------- |  |
|  |   * INHERITED RAKE DEFICIT  [NDLS]  +5m  (27.8%)  | LogRef: #RAKE-12034-TURN    |  |
|  |   * TSR SPEED RESTRICTION   [TDL]   +7m  (38.9%)  | Order: CO-NCR-ETW-0942      |  |
|  |   * JUNCTION HEADWAY HOLD   [CNB]   +9m  (50.0%)  | Section: BLK-CNB-ON-UP      |  |
|  |   * LOCO SPEED RECOVERY     [ALJN]  -3m (-16.7%)  | Section: Clear Track Fast   |  |
|  |   ----------------------------------------------------------------------------- |  |
|  |   NET SUM: +18m · Additivity Check: PASSED (Exact Accounting Proof: 18m = 18m)   |  |
|  +---------------------------------------------------------------------------------+  |
|                                                                                       |
|  +---------------------------------------------------------------------------------+  |
|  | 3. JOURNEY TIMELINE & UNCERTAINTY CONE (Widening Signature Visual)               |  |
|  | [ENDPOINT: GET /v1/trains/{trainNo}/journey]                                    |  |
|  |                                                                                 |  |
|  |   NDLS (0km)  ─── TDL (206km) ──[Train ● 112km/h]── CNB (435km) ─── PRYJ (632km)  |  |
|  |   Passed          Passed                             Expected         Upcoming  |  |
|  |   16:55 (Act)     17:34 (Act)                        18:12–18:26      20:45     |  |
|  |                                                      [±7m spread]     [±16m]    |  |
|  |                                                      (CONE WIDENS DOWNSTREAM)   |  |
|  +---------------------------------------------------------------------------------+  |
|                                                                                       |
|  +---------------------------------------------------------------------------------+  |
|  | 4. RIPPLE & CONNECTION CUSTODY                                                  |  |
|  | [ENDPOINT: GET /v1/cascade/ripple?station_code=CNB]                             |  |
|  |                                                                                 |  |
|  |   PASSENGER ALERT: 14 Connecting Passengers for #14218 (Departs 18:35)           |  |
|  |   Status: PROTECTED (Holding Order Dispatched · 12m Buffer Maintained)          |  |
|  |   Outgoing Pairing Rake #12302 Turnaround Risk: LOW (Slack Remaining: 42m)      |  |
|  +---------------------------------------------------------------------------------+  |
|                                                                                       |
|  +---------------------------------------------------------------------------------+  |
|  | 5. CRYPTOGRAPHIC RECEIPT CHIP                                                   |  |
|  | [ENDPOINT: GET /v1/ledger/scoreboard]                                           |  |
|  |                                                                                 |  |
|  |   Sealed Block #2109 · Hash: 0x6ffbe6...3031e · Auto-Graded on Wheel Touchdown  |  |
|  |   [Verify on Ledger Scoreboard →]                                               |  |
|  +---------------------------------------------------------------------------------+  |
|                                                                                       |
|  [v] STAFF TELEMETRY LENS (Collapsed by Default — One Click to Expand)                |
|  +---------------------------------------------------------------------------------+  |
|  | Block Section: BLK-ETW-TDL-UP · Priority: 1 · Locomotive: WAP-7 #30214          |  |
|  | Headway Behind: BOXN-7041 (+14km ahead) · Crew Duty: Rajesh K. (5.2h / 10h Cap) |  |
|  +---------------------------------------------------------------------------------+  |
+---------------------------------------------------------------------------------------+
```

**Mobile Layout Notes (375px):**
* Headline Arrival Range stacks: Station name on top, giant `18:12 — 18:26` centered with 28px font.
* Timeline converts to a clean vertical subway spine (`CorridorSpine`) with station cards.
* Total buttons on screen: **3 buttons** (Search modal trigger, Why-late expander, Staff lens toggle). Meets the Grandma constraint.

---

### TEXT WIREFRAME 2: `/network` — CORRIDOR TELEMETRY & CONGESTION RADAR

*Answers: "Where is every train right now and where will the network seize up in the next 6 hours?"*

```
+---------------------------------------------------------------------------------------+
|  RAILTWIN-X NETWORK  [NDLS — DDU TRUNK CORRIDOR · 785 KM]        [Live 5s Polling ●]  |
+---------------------------------------------------------------------------------------+
|                                                                                       |
|  [REGION 1: 1D LINEAR TRACK SCHEMATIC]                                               |
|  [ENDPOINT: GET /v1/live/positions]                                                   |
|                                                                                       |
|  KM 0           KM 206         KM 435                 KM 632            KM 785       |
|  NDLS ─────────── TDL ─────────── CNB ───────────────── PRYJ ──────────── DDU        |
|         ● #12004         ● #12301          ● #22436              ● BOXN-7041          |
|       (110 km/h)        (112 km/h)        (130 km/h)              (0 km/h)           |
|                                                                                       |
|  +---------------------------------------------------------------------------------+  |
|  | REGION 2: 6-HOUR PREDICTIVE CONGESTION RADAR MATRIX                             |  |
|  | [ENDPOINT: GET /v1/corridor/congestion-radar]                                   |  |
|  |                                                                                 |  |
|  |  SECTION              NOW(T+0)    T+1h       T+2h       T+4h       T+6h         |  |
|  |  GZB – ALJN (UP)      12% NOM     18% NOM    25% NOM    42% MOD    30% NOM      |  |
|  |  TDL – ETW (UP)       45% MOD     68% HIGH   88% CRIT*  55% MOD    22% NOM      |  |
|  |  ETW – CNB (UP)       30% NOM     42% MOD    74% HIGH   92% CRIT*  60% MOD      |  |
|  |  CNB – ON (UP)        80% CRIT*   60% MOD    40% NOM    35% NOM    20% NOM      |  |
|  |                                                                                 |  |
|  |  *CHOKEPOINT ADVISORY: ETW–CNB projects 92% occupancy at T+4h due to 3 freight  |  |
|  |   precedence crossings. Recommended intervention: Regulate BOXN-7041 at Rooma.   |  |
|  +---------------------------------------------------------------------------------+  |
|                                                                                       |
|  [REGION 3: ACTIVE TRAINS DIRECTORY (Density-First Grid)]                             |
|  [ENDPOINT: GET /v1/network/state]                                                    |
|  TRAIN #   NAME             LAST SEEN     NEXT STN   DELAY    SPEED     STATUS LAMP   |
|  12301     Howrah Rajdhani  TDL (206km)   CNB        +18m     112 km/h  AMBER         |
|  12034     Shatabdi Exp     ETW (297km)   CNB        +25m     98 km/h   AMBER         |
|  22436     Vande Bharat     CNB (435km)   PRYJ       +2m      130 km/h  GREEN         |
|  12424     Dibrugarh Raj    NDLS (0km)    GZB        +0m      85 km/h   GREEN         |
+---------------------------------------------------------------------------------------+
```

---

### TEXT WIREFRAME 3: `/compare` — THE OPERATIONAL SHOCK LAB

*Answers: "Why does official NTES fail during sudden disruptions while RailTwin-X adapts instantly?"*

```
+---------------------------------------------------------------------------------------+
|  RAILTWIN-X  /  COMPARATOR SHOCK LAB                    [Train: #12301 Howrah Raj v]  |
+---------------------------------------------------------------------------------------+
|                                                                                       |
|  +---------------------------------------------------------------------------------+  |
|  | OPERATIONAL SHOCK INJECTION CONTROL CENTER                                      |  |
|  | [ENDPOINT: POST /v1/demo/inject-event & POST /v1/demo/reset-events]             |  |
|  |                                                                                 |  |
|  |  [ +25m Outer Signal Hold (CNB) ]   [ +20m TSR Speed Restriction (ETW) ]        |  |
|  |  [ +35m Turnaround Deficit (NDLS)]   [ +15m Winter Gangetic Fog (CNB)   ]        |  |
|  |  [ Reset to Pristine Model State ]                                              |  |
|  +---------------------------------------------------------------------------------+  |
|                                                                                       |
|  +---------------------------------------+-----------------------------------------+  |
|  | BASELINE 2: OFFICIAL STATIC NTES      | RAILTWIN-X CALIBRATED QUANTILE CONE     |  |
|  | (Paralyzed by Static Run-Rates)       | (Instant Physics-Informed Recalibration)|  |
|  |                                       |                                         |  |
|  | ETA: 18:02 (+2m delay published)      | ETA RANGE: 18:18 — 18:32 (+24m p50)     |  |
|  | Behavior: Assumes train will recover  | Behavior: Ingests signal queue velocity;|  |
|  | speed on clear track.                 | widens cone downstream to absorb shock. |  |
|  | Status: MISLEADING (Under-forecasted) | Status: HONEST & SEALED IN LEDGER       |  |
|  +---------------------------------------+-----------------------------------------+  |
|                                                                                       |
|  ACCURACY SCOREBOARD OVER 33,600 EVALUATED STOPS:                                     |
|  B1 Frozen MAE: 14.2m  |  B2 Official MAE: 16.8m  |  RailTwin-X p50 MAE: 9.8m (-41.6%) |
+---------------------------------------------------------------------------------------+
```

---

### TEXT WIREFRAME 4: `/proof` — THE UNSEALED HONESTY CARD & LEDGER

*Answers: "Can RailTwin-X prove its accuracy on out-of-sample data and verify its tamper-evident audit chain?"*

```
+---------------------------------------------------------------------------------------+
|  RAILTWIN-X  /  EVALUATION PROOF & SELF-GRADING LEDGER         [Status: CHAIN VERIFIED]|
+---------------------------------------------------------------------------------------+
|                                                                                       |
|  +---------------------------------------------------------------------------------+  |
|  | SECTION 1: LIVE TAMPER-EVIDENT LEDGER SCOREBOARD                                |  |
|  | [ENDPOINT: GET /v1/ledger/scoreboard & GET /v1/ledger/verify]                  |  |
|  |                                                                                 |  |
|  |  TOTAL SERVED        VERIFIED ARRIVALS    LIVE EMPIRICAL MAE    80% COVERAGE    |  |
|  |  2,331 Blocks        430 Wheel Touchdowns 10.72 Minutes         80.6% (Target:80)| |
|  |                                                                                 |  |
|  |  Tip Hash: 6ffbe6ab4550951b0b79bea38aa3b181927805e68d27d2f9298ff0bd6fb3031e      |  |
|  |  [  Re-Verify SHA-256 Hash Chain (Genesis to Tip)  ]                            |  |
|  +---------------------------------------------------------------------------------+  |
|                                                                                       |
|  +---------------------------------------------------------------------------------+  |
|  | SECTION 2: OUT-OF-SAMPLE TEST BENCHMARKS (ml/artifacts/metrics.json)             |  |
|  | [ENDPOINT: GET /v1/model/performance]                                           |  |
|  |                                                                                 |  |
|  |  HORIZON       DISTANCE     RAILTWIN MAE   B2 NTES MAE   GAIN (%)   COVERAGE    |  |
|  |  T-0h (Now)    0 – 30 km    2.1 min        3.4 min       -38.2%     84.1%       |  |
|  |  T-1h          30 – 80 km   4.8 min        7.9 min       -39.2%     82.4%       |  |
|  |  T-2h          80 – 160 km  7.6 min        12.4 min      -38.7%     81.9%       |  |
|  |  T-4h          160 – 300 km 11.2 min       18.6 min      -39.8%     80.8%       |  |
|  |  T-6h          300 – 500 km 15.4 min       24.1 min      -36.1%     80.2%       |  |
|  +---------------------------------------------------------------------------------+  |
+---------------------------------------------------------------------------------------+
```

---

## 6.2 DESIGN TOKENS SPECIFICATION (`web/src/tokens.ts`)

Here is the exact production token draft to unify the entire application and eliminate the 132 distinct hex colors:

```typescript
/**
 * RAILTWIN-X ASPECT DESIGN TOKENS (v3.1)
 * Single Source of Truth for Theme, Typography, Spacing, and Semantics.
 */

export const TOKENS = {
  colors: {
    // 1. Dark Ops Ground (Console, Compare, Proof, Network)
    dark: {
      bg0: '#0A0B0D',       // App ground (deep obsidian)
      bg1: '#101216',       // Card surface
      bg2: '#15181D',       // Raised / hover state
      bg3: '#1B1F26',       // Elevated panel / modal
      line: '#23272F',      // 1px hairline border
      lineStrong: '#2E333D',// Active / emphasized border
      text1: '#E9EBEE',     // Primary headline text
      text2: '#A3ABB6',     // Secondary label text
      text3: '#6B7480',     // Muted micro-text
    },

    // 2. Light Daylight Ground (Passenger /t/:trainNo Default)
    light: {
      bg0: '#F8FAFC',       // Clean slate backdrop
      bg1: '#FFFFFF',       // Card surface
      bg2: '#F1F5F9',       // Hover / tab surface
      bg3: '#E2E8F0',       // Modal surface
      line: '#E2E8F0',      // Hairline border
      lineStrong: '#CBD5E1',// Emphasized border
      text1: '#0F172A',     // Deep slate-900 primary text
      text2: '#475569',     // Slate-600 secondary text
      text3: '#94A3B8',     // Slate-400 muted text
    },

    // 3. Indian Railways Signal Aspects (Universal Semantics)
    aspect: {
      clear: '#3DDC97',     // Green (On-time, <5m delay, test passed)
      clearTint: 'rgba(61, 220, 151, 0.13)',
      caution: '#F5A524',   // Amber (Brand accent, watch, 5–20m delay)
      cautionTint: 'rgba(245, 165, 36, 0.13)',
      restrict: '#F4506A',  // Red (Critical delay >20m, safety stop)
      restrictTint: 'rgba(244, 80, 106, 0.13)',
      signal: '#6C9FFF',    // Blue (Forecast uncertainty cone p10–p90)
      signalTint: 'rgba(108, 159, 255, 0.13)',
    },

    // 4. Semantic Purpose Tokens
    semantic: {
      arrivalRange: '#F5A524',
      whyLateInherited: '#6C9FFF',
      whyLateTSR: '#F5A524',
      whyLateCongestion: '#F4506A',
      whyLateRecovery: '#3DDC97',
      receiptHash: '#3DDC97',
      baselineStatic: '#F4506A',
    },
  },

  typography: {
    fontFamilies: {
      display: 'Space Grotesk, sans-serif',
      sans: 'Inter, system-ui, -apple-system, sans-serif',
      mono: 'JetBrains Mono, IBM Plex Mono, monospace',
    },
    // Strict 6-Step Scale
    scale: {
      micro: '10px',        // Aspect lamps, unit tags
      caption: '12px',      // Metadata, hashes, timestamps
      body: '14px',         // Standard descriptions, table rows
      subhead: '18px',      // Card section titles
      headline: '24px',     // Surface headings, KPI scores
      hero: '36px',         // Arrival range headline, landing display
    },
  },

  geometry: {
    radius: '2px',          // Universal crisp corner (rounded-sm)
    radiusLg: '6px',        // Modal & outer container corner (rounded)
  },

  spacing: {
    unit: 4,                // 4px/8px standard grid
  },
} as const;
```

---

## 6.3 COMPONENT PLAN: THE 10 CANONICAL PRIMITIVES

Every bespoke table, stat box, and badge in `web/src/pages/` will be replaced by these **10 Single-Purpose Primitives**:

1. `<ArrivalRange>`: Renders the headline p10–p90 interval with aspect color lamp and confidence spread.  
   *Replaces:* Bespoke headers in `PassengerTrackerPage.tsx`, `TrainDetailPage.tsx`, and `OverviewPage.tsx`.
2. `<ConeTimeline>`: Renders the widening uncertainty envelope across downstream stations.  
   *Replaces:* `AutopsyStrip.tsx`, `CorridorSpine.tsx`, and `ComparatorPage` station tables.
3. `<WhyLateCard>`: Clean causal waterfall with plain-English summary, rule matches, and additivity verification checkmark.  
   *Replaces:* 3 redundant why-late accordion implementations.
4. `<CascadeCard>`: Pairing rake turnaround deficit and passenger connection custody warning.  
   *Replaces:* `RippleBoardPage.tsx` bespoke turnaround cards.
5. `<ReceiptChip>`: Live SHA-256 block hash linked to verification scoreboard.  
   *Replaces:* Fabricated strings in `TimeMachinePage.tsx` and `HonestModelCardPage.tsx`.
6. `<StatCard>`: Uniform metric box with tabular numerals, label, and trend indicator.  
   *Replaces:* 16 scattered bespoke metric cards across Overview, ModelCard, and Foresight.
7. `<DataTable>`: Virtualized high-density operational table with sorting and aspect lamps.  
   *Replaces:* 8 ad-hoc `<table>` implementations in Trains, Timetable, Crew, TSR, Incidents.
8. `<SectionShell>`: Standard surface container with hairline borders and consistent padding.  
   *Replaces:* 72 conflicting padding variants.
9. `<ErrorState>`: Honest offline error display with retry trigger. **Zero silent mock fallback.**  
   *Replaces:* Silent try/catch blocks in `api.ts`.
10. `<LoadingState>`: Clean 200ms delayed skeleton.  
    *Replaces:* Inconsistent spinners.

---

## 6.4 BUTTON CENSUS TARGET

We crush the current 242 app-wide interactive elements down to a disciplined, purpose-driven count:

| Surface | Current Buttons/Interactive | Redesigned Target | Reduction | Justification |
| :--- | :---: | :---: | :---: | :--- |
| **Landing Page (`/`)** | 18 | **6** | -66.7% | 1 Train search, 1 Demo link, 4 Nav links. Removed fake access form. |
| **Train Page (`/t/:trainNo`)** | 17 (Passenger) + 3 (Detail) = 20 | **4** | -80.0% | 1 Search, 1 Why-late expand, 1 Receipt link, 1 Staff lens toggle. |
| **Network Telemetry (`/network`)**| 8 (LiveMap) + 7 (CorridorMap) = 15 | **4** | -73.3% | 1 Train filter, 1 Horizon tab selector, 2 Zoom controls. |
| **Shock Lab (`/compare`)** | 7 (Comparator) + 12 (Foresight) = 19 | **6** | -68.4% | 4 Operational shock injectors, 1 Reset button, 1 Train switch. |
| **Honesty & Ledger (`/proof`)**| 3 (ModelCard) + 3 (AuditPage) = 6 | **2** | -66.7% | 1 Re-verify Hash Chain, 1 Export JSON proof. |
| **Station Kiosk (`/kiosk`)** | 2 | **1** | -50.0% | 1 Language toggle (Fullscreen automated on F11). |
| **Dashboard Shell Nav (`Sidebar`)**| 29 | **5** | -82.7% | Collapsed 18 routes down to 4 canonical tabs + 1 role indicator. |
| **TOTAL APP-WIDE** | **242** | **35** | **-85.5%** | **Massive 85.5% reduction in cognitive chrome.** |

---

## 6.5 COMPLETE KILL & HIDE LIST

### Surfaces to HIDE FROM NAVIGATION (Preserve code, remove from sidebar):
1. `TimetablePage.tsx` (`/dashboard/timetable`) — Off-mission WTT timetable ERP.
2. `BlockSectionsPage.tsx` (`/dashboard/ops/blocks`) — Off-mission manual block section monitor.
3. `TSRRegistryPage.tsx` (`/dashboard/safety/tsr`) — Off-mission caution order CRUD.
4. `IncidentsPage.tsx` (`/dashboard/safety/incidents`) — Off-mission safety incident logger.
5. `CrewPage.tsx` (`/dashboard/crew`) — Off-mission loco pilot HR roster.
6. `MaintenancePage.tsx` (`/dashboard/maintenance`) — Off-mission civil engineering possession blocks.
7. `CorridorHandoffPage.tsx` (`/dashboard/corridor-coordination`) — Off-mission inter-division slot manager.
8. `DFCPrecedencePage.tsx` (`/dashboard/dfc-coordination`) — Off-mission freight priority table.
9. `GanttPage.tsx` (`/dashboard/gantt`) — Station platform berthing with fake client-side re-optimizer.

### Surfaces to MERGE & DELETE:
1. `PassengerTrackerPage.tsx` + `TrainDetailPage.tsx` -> **MERGE INTO `/t/:trainNo`**.
2. `TrackTrainModal.tsx` (752 LOC) -> **DELETE** (Redundant overlay; search directly opens `/t/:trainNo`).
3. `CorridorMapPage.tsx` (249 LOC) -> **DELETE** (Redundant copy of `LiveMapPage.tsx`).
4. `AuditPage.tsx` (195 LOC) + `ModelPage.tsx` (187 LOC) -> **DELETE** (Inferior duplicates of `HonestModelCardPage.tsx`).
5. `YardDiagramPage.tsx` (264 LOC) -> **DELETE CODE (ASK OWNER)** (100% hardcoded static array).

---

## 6.6 STEP-BY-STEP MIGRATION PLAN (No Big-Bang Rewrite)

Estimated Total Effort: **14 Engineering Hours** (~1.8 Days). Well within the 3-day constraint.

```
MIGRATION TIMELINE
├─ Step 1: Design Tokens & Primitives (2.5h)  --> Shippable
├─ Step 2: Build Unified /t/:trainNo (3.5h)   --> Shippable
├─ Step 3: Build /proof from ModelCard (2.0h) --> Shippable
├─ Step 4: Restyle /compare Shock Lab (1.5h)  --> Shippable
├─ Step 5: Consolidate /network (1.5h)        --> Shippable
├─ Step 6: Navigation Collapse & Hiding (1.5h)--> Shippable
└─ Step 7: Data Layer Honesty & Typings (1.5h)--> Shippable & Audited
```

### Step 1: Build Core Design Tokens & Primitives
* **Files Touched:** `web/src/tokens.ts` (new), `web/src/components/primitives/*` (10 new primitives).
* **Est. Hours:** 2.5 hours.
* **Verification Command:** `npm run build && npx tsc --noEmit`
* **Checkpoint:** Application continues running legacy pages unchanged while primitives are verified in isolation.

### Step 2: Build Unified `/t/:trainNo`
* **Files Touched:** `web/src/pages/train/TrainPage.tsx` (new), `web/src/App.tsx`.
* **Est. Hours:** 3.5 hours.
* **Verification Command:** Load `/t/12301`; verify p10–p90 headline range, why-late waterfall, and widening timeline.
* **Checkpoint:** Both `/track/12301` and `/dashboard/trains/12301` redirect to `/t/12301`.

### Step 3: Promote `/proof` (Honest Model Card + Ledger Scoreboard)
* **Files Touched:** `web/src/pages/model/HonestModelCardPage.tsx` -> `web/src/pages/proof/ProofPage.tsx`.
* **Est. Hours:** 2.0 hours.
* **Verification Command:** Click "Re-Verify SHA-256 Chain"; ensure live traversal passes across all 2,109 blocks.
* **Checkpoint:** Purge hardcoded fallback tip hash; display honest error state if ledger backend is unreachable.

### Step 4: Restyle `/compare` (Signature Shock Lab)
* **Files Touched:** `web/src/pages/demo/ComparatorPage.tsx`.
* **Est. Hours:** 1.5 hours.
* **Verification Command:** Inject `SIGNAL_HOLD`; verify B1/B2 stays static while RailTwin-X cone widens instantly.

### Step 5: Consolidate `/network`
* **Files Touched:** `web/src/pages/dashboard/LiveMapPage.tsx` -> `web/src/pages/network/NetworkPage.tsx`.
* **Est. Hours:** 1.5 hours.
* **Verification Command:** Verify live positions render along 785km track and 6h lookahead congestion radar is accessible.

### Step 6: Sidebar Navigation Collapse & Module Hiding
* **Files Touched:** `web/src/components/shell/Sidebar.tsx`, `web/src/components/shell/TopBar.tsx`.
* **Est. Hours:** 1.5 hours.
* **Verification Command:** Verify sidebar displays ONLY the 4 canonical surfaces (`/network`, `/t/12301`, `/compare`, `/proof`). Move the 10 operator ERP modules into a collapsed secondary "Legacy Station ERP" drawer.

### Step 7: Data Layer Honesty & Strong Typing
* **Files Touched:** `web/src/lib/api.ts`.
* **Est. Hours:** 1.5 hours.
* **Verification Command:** `grep -c ": any" web/src/lib/api.ts` drops from 23 to 0. Disable silent `mockStore` fallback on data routes.

---

## 6.7 THE HONESTY UPGRADES (Non-Negotiable Fixes)

1. **Purge Fabricated Receipts in `TimeMachinePage.tsx`:**  
   Replace `'Sealing block in SHA-256 chain...'` with the real backend-returned `receipt_hash` from `/v1/demo/time-machine`. If loading, display an explicit skeleton; never display fake receipt strings.
2. **Deactivate Silent `mockStore` Fallback on Data Routes:**  
   In `fetchBackend`, when the backend returns HTTP 4xx/5xx or encounters a network error, **throw an honest error** and render `<ErrorState>` with a retry button. Do NOT silently serve stale mockStore fixtures.
3. **Strongly Type the Top 10 API Responses:**  
   Import Pydantic-generated OpenAPI types into `api-schema.ts`. Eliminate `any` in `getTrains`, `getTrain`, `getTrainAutopsy`, `injectShockEvent`, and `getAdvisories`.
4. **Fix the 3 Dead Endpoints:**  
   * Point `reoptimizePlatforms` to `POST /stations/{code}/reoptimize`.
   * Point `liftTSR` to `DELETE /api/safety/tsr/{id}`.
   * Remove `rollbackPlatforms` and `acknowledgeHandoff` dead calls.

---

*End of Part B Redesign Specification.*
