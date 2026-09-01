# RailTwin-X: 3-Minute Stage Demo Script & Judge Presentation Runbook

> **Format:** 3-Minute Live Interactive Demonstration & Hackathon Pitch  
> **Target Audience:** Technical Judges, Railway Domain Experts, Ministry Evaluators  
> **Environment:** Localhost (`npm run dev` + `python scripts/demo_replay.py --fast` or Live FastAPI)

---

## Stage Script Timeline

```
┌──────────────┬────────────────────────────┬─────────────────────────────┬────────────────────────────────┐
│ TIME OFFSET  │ SCREEN / VIEW              │ SPOKEN NARRATION            │ ACTION & PROOF NUMBERS         │
├──────────────┼────────────────────────────┼─────────────────────────────┼────────────────────────────────┤
│ 0:00 – 0:30  │ /dashboard/live-map        │ The Live Corridor Twin      │ Show SSE 5s Pulse, 1s Gliding  │
│ 0:30 – 1:00  │ /dashboard/live-map Drawer │ Micro-Weather & Attribution │ Click #12301, Point at +16m    │
│ 1:00 – 1:45  │ /dashboard/advisories      │ Neural Brain & WhatsApp ACK │ Point at Cryptographic ACK     │
│ 1:45 – 2:20  │ /dashboard/gantt           │ Gantt Theatre & Sub-50ms Opt│ Click 1-Click Re-Opt (42ms)    │
│ 2:20 – 3:00  │ /dashboard/model           │ Honest Proof & MLOps Shield │ Point at 80.64% Cov, 0.77ms p50│
└──────────────┴────────────────────────────┴─────────────────────────────┴────────────────────────────────┘
```

---

### Act 1: The Live Corridor Twin (0:00 – 0:30)
* **Screen:** `/dashboard/live-map` (Corridor Spatial Twin)
* **What to Say:**
  > "Distinguished judges, Indian Railways runs on dynamic physical reality, but legacy dispatchers fly blind between fixed station signals. This is **RailTwin-X** — the neural operational twin for the 785 KM New Delhi to Pt. Deen Dayal Upadhyaya mainline corridor."
* **What to Do:**
  1. Open `/dashboard/live-map`.
  2. Point at the live train markers gliding along the polyline.
  3. Toggle the **Confidence Halo** button.
* **Proof Numbers to Highlight:**
  * **Active SSE Pulse:** `5.0s` heartbeat in top right badge.
  * **Exponential Decay Tau:** `τ = 1800s` with visible fading halos when telemetry ages.
  * **Kinematic Gliding:** Markers interpolate every `1000ms` client-side.

---

### Act 2: Environmental Shock & Live Delay Autopsy (0:30 – 1:00)
* **Screen:** `/dashboard/live-map` (Click Train `#12301` to open Side Drawer)
* **What to Say:**
  > "At T+30 seconds, an atmospheric cold-wave triggers dense fog at Kanpur Central (CNB). Visibility plunges to 350m. Rajdhani Express #12301 enters the section and delay jumps by +16 minutes. Instead of hiding behind an opaque average, Pipeline 07 computes an instant, mathematically exact delay autopsy."
* **What to Do:**
  1. Click on Train marker `#12301` (Howrah Rajdhani).
  2. Side drawer slides open with live telemetry, weather, and Why-Late breakdown.
* **Proof Numbers to Highlight:**
  * **Micro-Weather:** `14.0°C`, `92% RH`, `Visibility: 0.35 km` (`fog_flag = 1`).
  * **Exact Delay Accounting:** `sum(attributed_minutes) == 16.0 min` (`is_exact_accounting: true`).
  * **Cause Chips:** `WEATHER_FOG` (+8.5m), `TSR_ACTIVE` (+5.0m), `CONGESTION` (+2.5m).

---

### Act 3: Neural Brain Perception & WhatsApp Closed-Loop (1:00 – 1:45)
* **Screen:** `/dashboard/advisories` (Advisory Triage Queue)
* **What to Say:**
  > "Rather than waiting for downstream chaos, RailTwin-X's Neural Brain scans 30km spatial headway windows. It perceives headway compression between #12301 and Vande Bharat #12004, evaluates priority preemption through deterministic kinematic interlocks, and dispatches a cryptographically signed WhatsApp alert directly to the Section Controller."
* **What to Do:**
  1. Navigate to `/dashboard/advisories`.
  2. Show active advisory card for `#12301` (`PRIORITY_HOLD`).
  3. Highlight the incoming WhatsApp ACK from Controller `SC_CNB_01`.
* **Proof Numbers to Highlight:**
  * **Brain Advisory Latency:** `12.5 ms` (SLA ceiling: `< 2000 ms`).
  * **Safety Interlock:** `5/5 Checks Passed` with 0 ML imports.
  * **Dispatcher ACK:** Status `ACCEPTED` with SHA-256 Merkle audit entry.

---

### Act 4: Platform Gantt Theatre & Sub-50ms Self-Healing (1:45 – 2:20)
* **Screen:** `/dashboard/gantt` (Platform Occupancy Timeline)
* **What to Say:**
  > "The delayed arrival of Rajdhani creates an immediate collision on Platform 1 with scheduled departures. Watch the red pulsing conflict block on Platform 1. The station master clicks one button: '1-Click Re-Optimize'."
* **What to Do:**
  1. Navigate to `/dashboard/gantt`.
  2. Point at the **pulsing red conflict block** on Platform 1.
  3. Click **1-Click Re-Optimize Plan**.
  4. Watch the block animate smoothly to Platform 3 (`~600ms` CSS lane slide).
  5. Point at the green **ReoptDiff Stamp** (`1 swap in 42ms`).
  6. Click **Rollback** to show instantaneous restoration, then re-optimize again.
* **Proof Numbers to Highlight:**
  * **Greedy Solver Execution:** `42 ms` (sub-50ms SLA guarantee).
  * **Conformal Risk Bands:** Shaded `q10–q90` uncertainty band labeled: *"This plan survives 95% of delay scenarios."*
  * **Swaps Performed:** `1 platform swap` (`#12301 -> PF3`), `0 remaining conflicts`.

---

### Act 5: Model Artifact Inspection & MLOps Shield (2:20 – 3:00)
* **Screen:** `/dashboard/model` (Neural Architecture & Proof Table)
* **What to Say:**
  > "Judges, all metrics you see are backed by verifiable code and frozen artifacts in `ml/artifacts/metrics.json`. We don't train black boxes — our Champion PyTorch GRU is bound by Mondrian Conformal Quantile Regression, guaranteeing an empirical 80.64% coverage target at a median latency of 0.77ms."
* **What to Do:**
  1. Navigate to `/dashboard/model`.
  2. Point at the 80% coverage gauge, MAE proof table across horizons, and Champion Model SHA256 pin.
* **Proof Numbers to Highlight:**
  * **Champion Latency:** `0.77 ms` p50 / `1.56 ms` p95.
  * **Empirical Coverage:** `80.64%` (target: 80.0%).
  * **Overall MAE:** `10.72 min` (evaluated across 434,382 held-out test snapshots).
  * **Deterministic Safety Invariant:** `0 <= q10 <= q50 <= q90` strictly non-crossing.

---

## Judge Q&A Defense Sheet

| Question | Winning Technical Answer | Codebase Reference |
|---|---|---|
| *"What happens if external RapidAPI or GPS goes down?"* | "The system fails over to web scraping, then to dead-reckoning along route polylines with exponential confidence decay ($\tau = 1800\text{s}$). The UI displays a STALE badge and never crashes or throws 500s." | `engine/live_tracker.py:410-440` |
| *"How do you prove the delay minutes aren't hallucinated?"* | "The Live Delay Ledger enforces the exact mathematical invariant $\sum \text{causes} \equiv \Delta\text{delay}$. Any residual above $2.0\text{m}$ is honestly recorded as `UNEXPLAINED`." | `engine/attribution.py:315-325` |
| *"Can platform swaps cause unphysical turnarounds?"* | "No. The safety interlock enforces a minimum 15-minute dwell buffer and loco kinematic speed limits ($\le 15\text{km/h}$ yard moves) before any swap is accepted." | `safety/interlock.py:120-160` |
| *"Is this deterministic across offline runs?"* | "Yes. Our determinism test runs the full 3-minute scenario twice against SQLite and asserts byte-identical DB rows and metrics." | `tests/test_demo_replay.py` |
