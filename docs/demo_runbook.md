# RailTwin-X Live Demo Runbook (5-Minute Hackathon Pitch Script)
**SIH Problem Statement ID 26028**: Dynamic ETA Forecast for Coaching Trains  
**Presenter Flow**: Keystroke-by-keystroke presentation guide with exact spoken scripts and screen actions.

---

## Pre-Flight Checklist (10 Minutes Before Judging)
1. Launch app with 1-click script:
   ```powershell
   .\scripts\demo.ps1
   ```
2. Verify endpoints return HTTP 200:
   - `http://localhost:8000/v1/health` → `{"status": "OK"}`
   - `http://localhost:8000/v1/model/performance` → `canonical_mae: 10.72`
3. Have two browser tabs open:
   - Tab 1: `http://localhost:5173/` (Foresight Console)
   - Tab 2: `http://localhost:5173/compare` (Signature Live Comparator)

---

## 5-Minute Keystroke-by-Keystroke Pitch Script

### Minute 0:00 – 0:45: The Hook ("Every train app in India is broken in the same way")
- **Screen**: Start on `http://localhost:5173/compare`.
- **Spoken Script**:
  > "Respected judges, every passenger in India has experienced this frustration: you check NTES or Where Is My Train 4 hours before your journey. It says 'Right Time'. You reach the platform, and suddenly the board flips to 'Delayed by 2 Hours'.
  > Why? Because existing trackers don't know a train is late until it has *already passed a physical sensor late*. They use static frozen delays or unbuffered linear run-rates.
  > Today, we present **RailTwin-X**: India's first dynamic, physics-informed corridor digital twin with calibrated uncertainty cones and tamper-evident audit receipts."

---

### Minute 0:45 – 1:45: The Live Comparator (`/compare`)
- **Screen**: Point to the side-by-side comparison table and error scoreboard.
- **Spoken Script**:
  > "Look at our Live Comparator on screen right now. We are tracking Train #12301 Howrah Rajdhani approaching Kanpur Central.
  > In grey is **Baseline 1 (Frozen Delay)**: it simply holds the last recorded delay flat across the entire journey.
  > In red is **Baseline 2 (Official NTES run-rate)**: it assumes linear timetable recovery, under-forecasting delays by 21 minutes!
  > In green is **RailTwin-X**: our calibrated ML quantile cone (p10–p50–p90). Notice how the cone realistically widens from ±4 minutes within 1 hour to ±18 minutes at 3 hours.
  > Now watch what happens when an unexpected operational shock hits the corridor..."
- **Action**: Click the red button **[⚡ +25m Signal Hold]**.
- **Spoken Script**:
  > "I just injected a 25-minute outer signal hold at Kanpur Central. Look at the screen:
  > RailTwin-X immediately re-calibrates. The p50 forecast shifts from +38m to +63m, and the p90 risk envelope expands to protect downstream connections.
  > Meanwhile, look at B1 and B2: completely flat, completely paralyzed, completely unaware of the blockage. This is why RailTwin-X beats official NTES by **36.3% at 3 hours** and **51.7% at 6 hours**."

---

### Minute 1:45 – 2:45: Causal Delay Autopsy (`/` D3 Surface)
- **Screen**: Switch to Tab 1 (`http://localhost:5173/`) and scroll down to the **Causal Delay Autopsy & Attribution Waterfall**.
- **Spoken Script**:
  > "When a train is delayed, controllers and passengers need to know *why*. But existing systems give zero explanation.
  > RailTwin-X breaks down the exact delay into 7 physics-based categories:
  > 1. Inbound rake turnaround deficit from previous service leg (+12m)
  > 2. Engineering speed restrictions (TSR 40 km/h) (+14m)
  > 3. Signal hold at outer home (+25m)
  > 4. Loco pilot recovery on high-speed clear blocks (−4m)
  > Crucially: notice the badge: **100% Mathematically Additive**. Every single minute is accounted for, summing exactly to the total delay, backed by verifiable sensor log pointers. Zero unexplained drift."

---

### Minute 2:45 – 3:45: Ripple Board & Connection Custody DSS (`/cascade`)
- **Screen**: Click **[Ripple & Custody DSS]** in the header (`http://localhost:5173/cascade`).
- **Spoken Script**:
  > "A train delay in Indian Railways is never isolated. It cascades.
  > Look at our **Ripple Board**. Train #12034 arriving 45m late at New Delhi eats into the 180m turnaround buffer for outgoing #12033 Shatabdi, projecting a 25m departure delay before the rake even enters the platform.
  > Now look at our **Connection Custody Engine**:
  > At Kanpur Central, feeder train #12381 is arriving 20m late. 35 passengers have an onward transfer to #12314 Rajdhani. The next train is 5 hours away.
  > RailTwin-X calculates the exact trade-off: hold #12314 by just 6 minutes. Yes, onboard passengers lose 6 minutes, but 35 passengers are saved from 5 hours stranded on the platform. Net result: **+115.0 passenger-hours saved**.
  > And notice our clear jurisdictional badge: **Section Controller Decision Support — Advisory Only**. We empower the Section Controller; dispatch authority remains strictly in human hands."

---

### Minute 3:45 – 4:30: The Cryptographic Hash-Chained Ledger (`/model-card`)
- **Screen**: Click **[Honest Model Card]** (`http://localhost:5173/model-card`).
- **Spoken Script**:
  > "How do you know these numbers aren't cherry-picked after the fact?
  > Every single ETA forecast RailTwin-X serves is hashed and chained into an append-only **SHA-256 tamper-evident ledger** before the train arrives.
  > When the train actually triggers the track circuit, the arrival time is cryptographically graded against the sealed forecast.
  > On 25,203 test samples across 6 cross-validation folds:
  > - Our empirical 80% coverage is **80.64%** — mathematically calibrated.
  > - And we publish our ties honestly: within 1 hour, train momentum dominates, giving a physics tie of **5.88m vs 5.84m**. We don't hide ties; we publish them openly. We win where it matters: **10.48m at 3 hours** and **14.80m at 6 hours**."

---

### Minute 4:30 – 5:00: Closing & Q&A Transition
- **Spoken Script**:
  > "RailTwin-X solves SIH Problem Statement 26028 end-to-end: calibrated uncertainty for passengers, causal autopsies for controllers, cascade protection for junctions, and tamper-evident integrity for Indian Railways governance.
  > Thank you, and we are eager to answer your technical questions."

---

## 4 Deadliest Judge Trap Questions & Instant Answers

| Question | Winning Answer |
|---|---|
| **"Why not just use GPS tracking like Where Is My Train?"** | "GPS tells you where the train was 30 seconds ago; it cannot tell you what will happen 3 hours ahead. GPS has zero knowledge of upcoming TSR speed restrictions, freight train precedence on DFC sidings, or incoming rake deficits. RailTwin-X combines live GPS dead-reckoning with corridor state, junction occupancy, and physics models." |
| **"Can Section Controllers trust an AI model to hold trains?"** | "Our system is explicitly built as an **Advisory Decision Support System (DSS)**. We never auto-dispatch. We provide the Section Controller with a quantified passenger-hour tradeoff index (e.g. +115 pax-hrs saved by a 6m hold) so controllers make informed decisions backed by data rather than guesswork." |
| **"Why is your 1-hour MAE tied with frozen delay (5.88 vs 5.84 min)?"** | "Because within 90 km, train physics and signaling spacing dominate. A train moving at 110 km/h with 40 km remaining cannot magically recover 20 minutes. Competitors who claim huge 1-hour gains are either data-snooping or cherry-picking. We disclose the physics tie honestly and demonstrate our 36.3% and 51.7% gains where network complexity actually compounds: at 3h and 6h." |
| **"What happens during extreme winter fog or monsoon deluges?"** | "Our model features an integrated Weather Context Engine (temperature, humidity, visibility, precipitation). Under dense fog (vis < 200m), fog-dawn features cap permissible track speed to 60 km/h in accordance with Indian Railways safety rules, expanding the p90 confidence interval to reflect headway buffering." |
