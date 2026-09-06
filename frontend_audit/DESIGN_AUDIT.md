# RailTwin-X Phase 3: Design System Audit
**Auditors:** Brutal Senior Product Designer · Senior Frontend Architect · First-Time User Advocate

---

## 3.1 COLOR PALETTE AUDIT: THE TRUE VS. ACCIDENT PALETTE

A full scan of all TypeScript and TSX source files across `web/src/` revealed **132 DISTINCT HEX COLOR VALUES**.
Although `web/src/design-tokens.css` correctly specified a disciplined 8-color signal aspect system ("ASPECT"), individual developers bypassed CSS variables and hardcoded arbitrary hex values into inline Tailwind utility classes.

### The True Palette (from Landing Page Reference DNA)
Designed around Indian Railways 4-Aspect Signal Panels:

| Semantic Role | Token Name | Hex Value | Primary Application |
| :--- | :--- | :--- | :--- |
| **App Ground** | `--bg-0` | `#0A0B0D` | Deep obsidian backdrop; zero OLED pure black. |
| **Card Surface**| `--bg-1` | `#101216` | Standard container surface. |
| **Active / Raised**| `--bg-2` | `#15181D` | Hover states, active tabs, table headers. |
| **Hairline Border**| `--line` | `#23272F` | Crisp 1px division line. |
| **Signal Caution**| `--aspect-caution` | `#F5A524` | Primary brand accent; amber alert; moderate delay (6–20m). |
| **Signal Clear** | `--aspect-clear` | `#3DDC97` | On-time status (<5m); mathematical verification win; nominal. |
| **Signal Restrict**| `--aspect-restrict`| `#F4506A` | Critical delay (>20m); track circuit fail; collision conflict. |
| **Forecast Signal**| `--aspect-signal` | `#6C9FFF` | ML uncertainty bands; p10–p90 spread; predictive telemetry. |
| **Text Primary** | `--text-1` | `#E9EBEE` | High-contrast editorial and metric headlines. |
| **Text Secondary**| `--text-2` | `#A3ABB6` | Subtitles, station routes, timestamps. |
| **Text Tertiary** | `--text-3` | `#6B7480` | Micro-labels, unit abbreviations, inactive icons. |

### The Accident Palette (Rogue Clones & Copy-Paste Drift)
Due to uncoordinated development across pages, the following chaotic clusters formed:

* **The 8 Competing Dark Backgrounds:**
  `#0A0B0D` (Landing), `#07090D` (Comparator, TimeMachine, ModelCard), `#0C0F17` (Headers), `#0E121A` (Step buttons), `#10141F` (Cards), `#141A26` (Narrative), `#15171A` (Sidebar footer), `#26282C` (Yard/Overview borders).
  *Result:* Borders and cards have jarring step-offs between pages.
* **The 3 Competing Ambers:**
  `#F5A524` (Official Aspect Amber, 211 usages) vs `#FFB224` (Rogue Amber, 189 usages) vs `#F59E0B` (Tailwind amber-500, 38 usages).
* **The 4 Competing Greens:**
  `#3DDC97` (Aspect Green, 103 usages) vs `#3ECF8E` (51 usages) vs `#22C55E` (Tailwind green-500, 33 usages) vs `#10B981` (emerald-500, 24 usages).
* **The Competing Grays:**
  `#E9EBEE` vs `#E8E8E6` vs `#E5E7EB` (Primary text); `#A3ABB6` vs `#9A9DA3` vs `#9CA3AF` (Secondary text).

### Contrast Failures (Accessibility Violations)
* `text-[#6B7480]` on `#0A0B0D` background: **3.71:1 contrast ratio**. Fails WCAG AA minimum requirement of 4.5:1 for normal body text.
* `text-[#6B6E74]` on `#15171A` (Sidebar role switcher footer, `Sidebar.tsx:294`): **3.52:1 contrast ratio**. Fails WCAG AA.
* Small red badges (`text-[#F4506A]` on `bg-[rgba(244,80,106,0.13)]`): While legible at 14px bold, fails on 10px micro-tags.

---

## 3.2 TYPOGRAPHY AUDIT: 15-STEP SCALE CHAOS

Instead of a disciplined 5–6 step typographic scale, the application exhibits **15 distinct font size steps** in production:

1. `text-[8px]` (`Sidebar.tsx:234` — micro badges)
2. `text-[9px]` (`Sidebar.tsx:134`, `ForesightConsolePage.tsx:442` — aspect labels)
3. `text-[10px]` (`LandingPage.tsx:88`, `OverviewPage.tsx:112` — station tags)
4. `text-[11px]` (`LandingPage.tsx:220`, `HonestModelCardPage.tsx:283` — table headers)
5. `text-[13px]` (`TopBar.tsx:45`)
6. `text-xs` (12px — pervasive across tables)
7. `text-sm` (14px — standard body)
8. `text-base` (16px — subheadings)
9. `text-lg` (18px — card titles)
10. `text-xl` (20px — modal titles)
11. `text-2xl` (24px — scoreboard metrics)
12. `text-3xl` (30px — KPI numbers)
13. `text-4xl` (36px — hero counters)
14. `text-5xl` (48px — hero title)
15. `text-6xl` (60px — landing headline)

### Font Families & Tabular Alignment
* Font stack in `tailwind.config.js`: `Space Grotesk` (display), `Inter` / `IBM Plex Sans` (sans), `JetBrains Mono` / `IBM Plex Mono` (mono).
* **Defect:** Key telemetry numbers on `PassengerTrackerPage.tsx:139` and `TrainDetailPage.tsx:473` omit the `tabular-nums` class, causing arrival countdowns and delay minutes to wobble horizontally on every 5s polling refresh!

---

## 3.3 SPACING & LAYOUT AUDIT

* **Padding Scale Chaos:** **72 distinct padding utility classes** (`p-0.5`, `p-1`, `p-1.5`, `p-2`, `p-2.5`, `p-3`, `p-3.5`, `p-4`, `p-5`, `p-6`, `p-8`, `p-12`, plus horizontal/vertical split variations).
* **Border Radius Fragmentation:**
  * `rounded-xs` (1px) — used on Aspect lamps.
  * `rounded-sm` (2px) — used on Landing Page buttons and cards.
  * `rounded-md` (6px) — used on dashboard overview cards.
  * `rounded-lg` (8px) — used on PassengerTracker cards.
  * `rounded-xl` (12px) — used on ComparatorPage and TimeMachinePage.
  * `rounded-2xl` (16px) — used on modals.
  * *Result:* Every page presents a different curvature philosophy!

---

## 3.4 COMPONENT DUPLICATION CENSUS

The application reinvents the same 5 UI elements in bespoke ad-hoc code across multiple files:

### 1. The "Stat / Metric Card" (4 separate implementations):
* `web/src/pages/dashboard/OverviewPage.tsx:102-140` (Bespoke 4-box grid with hardcoded icons).
* `web/src/pages/model/HonestModelCardPage.tsx:279-312` (Ledger metric cards with custom borders).
* `web/src/pages/foresight/ForesightConsolePage.tsx:120-155` (Horizon stat cards).
* `web/src/pages/ops/RippleBoardPage.tsx:90-125` (Turnaround custody stat cards).

### 2. The "Status Badge / Aspect Tag" (5 separate implementations):
* `web/src/components/ui/Badge.tsx:8` (Standard badge primitive).
* `web/src/components/aspect/AspectLamp.tsx:32` (Pulsing circular LED lamp).
* `web/src/components/common/DataFreshnessBadge.tsx:15` (Telemetry latency badge).
* `web/src/pages/dashboard/TrainsPage.tsx:180` (Inline span with conditional background).
* `web/src/pages/public/PassengerTrackerPage.tsx:140` (Giant single-delay pill).

### 3. The "Causal Why-Late Card" (3 separate implementations):
* `web/src/components/aspect/AutopsyStrip.tsx:25` (Horizontal segmented multi-cause bar).
* `web/src/pages/public/PassengerTrackerPage.tsx:640-710` (Bilingual accordion card with evidence links).
* `web/src/pages/foresight/ForesightConsolePage.tsx:519-563` (Stacked waterfall list with percentage metrics).

### 4. The "Journey Station Timeline" (3 separate implementations):
* `web/src/components/aspect/CorridorSpine.tsx:40` (Vertical interactive subway-style spine).
* `web/src/pages/public/PassengerTrackerPage.tsx:420-580` (Horizontal scrolling station dots with live train marker).
* `web/src/pages/demo/ComparatorPage.tsx:210-310` (Horizontal table row station comparison).

---

## 3.5 MOTION & ANIMATION AUDIT

* **Good Motion:**
  * `BootPreloader.tsx`: Clean 900ms one-shot session boot.
  * `AspectLamp.tsx`: Subtle 1.4s infinite cubic-bezier pulse on restriction (`aspect-pulse-restrict`) accurately conveys dangerous railway line closures.
  * `EventTicker.tsx`: Smooth marquee crawl.
* **Bad Motion / Masking Data:**
  * `GanttPage.tsx:129-166`: Uses a fake `setTimeout(..., 600)` with a progress spinner to give the illusion that a mathematical Mixed-Integer Linear Program (MILP) is running on the backend, when it is literally executing hardcoded client-side array swaps (`slot.id === '12301' ? platform: 4`)!
  * `TimeMachinePage.tsx:272`: Spin animation on the "Re-Verify" button while displaying static in-memory hashes.

---

## 3.6 AESTHETIC FIT & CONTEXTUAL SPLIT

The current frontend applies a single dark, glassmorphic, sci-fi ops console look across all surfaces indiscriminately. This is a profound UX failure when measured against the 4 personas:

1. **The Station Controller (`/console`, `/network`, `/compare`):**
   * *Fit:* **PERFECT.** Needs dark obsidian background (`#0A0B0D`), high-contrast signal lamps (`#3DDC97`, `#F5A524`, `#F4506A`), dense tabular layouts, and zero decorative animations.
2. **The Grandma on a Phone (`/t/:trainNo`):**
   * *Fit:* **DISASTROUS.** Looking at dark glassmorphism on a mobile screen under harsh Indian sunlight while standing on Platform 4 at Kanpur Central is illegible. The passenger view needs an ultra-clean, high-contrast, daylight-readable theme with giant numbers, clear hindi labels, and zero cockpit chrome.
3. **The Station concourse Display (`/kiosk`):**
   * *Fit:* **NEEDS MASSIVE GLANCEABILITY.** Must be readable from 10 meters away with zero interactive buttons.
4. **The Hackathon Judge (`/`, `/compare`, `/proof`):**
   * *Fit:* **EXCELLENT.** The dark ops look signals deep engineering sophistication, provided every single number connects to real ledger blocks and real quantile models.

### Proposed Aesthetic Split
* **Passenger Surface (`/t/:trainNo`):** Daylight-readable default (crisp high-contrast light theme: `#FFFFFF` ground, `#0F172A` text, bold amber/green signal accents; optional dark toggle).
* **Operations & Demo Surfaces (`/network`, `/compare`, `/proof`, `/console`):** Pure ASPECT dark signal console (`#0A0B0D`, `#101216`, `#23272F`, `#F5A524`).
* **Station Display (`/kiosk`):** Ultra-high contrast 10-meter PIDS theme (`#000000` base, `#FFD700` golden amber, `#FFFFFF` text).

---

*End of Phase 3 Design System Audit. Proceed to Phase 4 Data Layer & Contract Audit.*
