# PHASE 1 — CAPABILITY FLIPS
**15 top latent assets × 3 lenses (passenger / controller / trust). Weak flips discarded. Strong flips starred ★.**

> **STATUS UPDATE 2026-09-05 (commit `f371ecb`):** Flip #2 (what-if → shock-injection demo), #8 (doom → ripple board), #9 (custody HOLD → hold advisories w/ passenger-hours) are now **BUILT**. Flip #1/#7 (public accountability ticker → the LIVE hash-chained ledger) remains the strongest unbuilt flip — the backtest model card shipped, but the live ledger still has zero UI. #14 (congestion radar) remains the strongest controller flip to build.

---

## Asset 1: PredictionLedger Scoreboard (`engine/prediction_ledger.py:187`)

- **PASSENGER:** ★ "How accurate was your train's prediction?" — passenger-facing card: "We predicted +35 min; actual was +37 min. Coverage last 1000 predictions: 80.6%."
- **CONTROLLER:** "Which train class do we predict worst?" — "Superfast long-range: MAE 9.2 min vs Shatabdi: MAE 3.1 min." Lets controllers trust selectively.
- **TRUST:** ★ **Live public accountability ticker** — "Our last 1000 ETA predictions: 80.6% arrived within 10 min. Tamper-evident chain: 12,847 blocks verified."

**VERDICT:** ★★★ Two strong flips. The trust angle is the most novel.

---

## Asset 2: CascadeSimulator (`engine/simulator.py:57`)

- **PASSENGER:** "Will my train cascade?" — passenger sees a forecast of cascade risk before boarding. (Marginal value vs current ETA.)
- **CONTROLLER:** ★ **"What-If intervention lab"** — "Hold 12556 at CNB for 10 min" → ripple map showing 5 downstream inheritances totaling +47 min. "Don't intervene — net cost: +47 min vs saves 0."
- **TRUST:** "Decision traces" — controller actions are recorded alongside ledger hashes, creating an audit trail of "what we did and why."

**VERDICT:** ★★★ The intervention lab is the standout.

---

## Asset 3: ConformalPIDController (`ml/conformal.py:311`)

- **PASSENGER:** ★ "Why is my ETA band so wide?" — badge: "REGIME: FOG SEASON — intervals widened 22% to reflect low visibility."
- **CONTROLLER:** "Current PID state: α=0.27" — operational transparency.
- **TRUST:** "We are honest about when we don't know" — α-tracking shown as "uncertainty barometer."

**VERDICT:** ★★ The fog regime badge has clear product shape.

---

## Asset 4: PSIDriftMonitor (`ml/drift.py:179`)

- **PASSENGER:** Weak.
- **CONTROLLER:** "Model health: 3 features RED" — not actionable in 60s.
- **TRUST:** ★ "Model regime: fog" badge on scoreboard.

**VERDICT:** ★ Drift badge is best used as a *complement* to Asset 3, not standalone.

---

## Asset 5: CUSUMDetector / ADWINDetector (`ml/drift.py:73,98`)

- **PASSENGER:** "Anomaly detected" — could be a passenger-facing card if framed right.
- **CONTROLLER:** ★ **"Behavior change-point alert"** — "Train 12556 velocity profile shifted at 14:32 — possible signal failure. Investigate."
- **TRUST:** Weak.

**VERDICT:** ★★ Behavior anomaly is genuinely useful for controllers.

---

## Asset 6: AdaptiveConformalInference (`ml/conformal.py:216`)

- **PASSENGER:** (same as PID — fog badge)
- **CONTROLLER:** Marginal.
- **TRUST:** ★ "Adaptive coverage: bands tightened 5% this week as we gained confidence."

**VERDICT:** ★ Subsumed under #3.

---

## Asset 7: verify_chain_integrity() (`engine/prediction_ledger.py:159`)

- **PASSENGER:** ★ **"✓ Tamper-proof audit: 12,847 predictions verified"** — public trust badge.
- **CONTROLLER:** Operational.
- **TRUST:** ★★★ This is the cryptographic accountability surface.

**VERDICT:** ★★★ Cryptographic trust is a category-defining angle.

---

## Asset 8: RakeResolver is_doomed (`engine/rakes.py:57`)

- **PASSENGER:** ★ "Outgoing train doomed — incoming rake 45 min late. Book refund."
- **CONTROLLER:** ★★ "DOOM ALERT: Train 12556. Definite +45 min departure delay. Cascade to 3 connecting trains."
- **TRUST:** Marginal.

**VERDICT:** ★★ The passenger-side doom disclosure is novel and high-impact.

---

## Asset 9: ConnectionCustodyEngine (`engine/ops.py:459`)

- **PASSENGER:** ★★ **"Your connection is 62% likely to hold"** — quantified connection risk with HOLD action card.
- **CONTROLLER:** "Hold advisory for 12556 at CNB — saves 47 missed connections."
- **TRUST:** Marginal.

**VERDICT:** ★★★ Two strong flips. The HOLD action is uniquely Railways-specific.

---

## Asset 10: CrewDutyEngine (`engine/ops.py:341`)

- **PASSENGER:** Weak.
- **CONTROLLER:** ★ "Crew C-412 fatigue breach in 2h 10m — relief at CNB."
- **TRUST:** Marginal.

**VERDICT:** ★ Good but not differentiated. Skip.

---

## Asset 11: ConflictScanner (`engine/conflicts.py:76`)

- **PASSENGER:** Weak.
- **CONTROLLER:** ★ "5 conflicts predicted in next hour on NDLS-CNB section."
- **TRUST:** Marginal.

**VERDICT:** ★ Already exists as brain advisory. Skip standalone.

---

## Asset 12: Signal-hold inference (`engine/live_tracker.py:516`)

- **PASSENGER:** ★ "Train inferred at signal: RED — currently held."
- **CONTROLLER:** ★ "Block occupancy: train inferred at RED at km 342."
- **TRUST:** Marginal.

**VERDICT:** ★★ Novel and pretty, but a styling layer not a rubric mover.

---

## Asset 13: PositionResolver (`engine/position_resolver.py`)

- **PASSENGER:** ★ "Location certainty: 78% — most likely at km 342, but could be at 290."
- **CONTROLLER:** Marginal.
- **TRUST:** Marginal.

**VERDICT:** ★ Marginal novelty; uncertainty shown elsewhere.

---

## Asset 14: DaySpatialIndex (`engine/spatial_context.py:152`)

- **PASSENGER:** Marginal.
- **CONTROLLER:** ★★ "Network congestion at 14:00: CNB section 78% occupied. Rain radar for delays."
- **TRUST:** Marginal.

**VERDICT:** ★★ 6-hour-ahead junction congestion radar = high novelty.

---

## Asset 15: NNLS stacking weights by horizon (`ml/ensemble.py:30`)

- **PASSENGER:** Weak.
- **CONTROLLER:** Marginal.
- **TRUST:** ★ **"At long horizon, we rely more on linear extrapolation"** — explainability card.

**VERDICT:** ★ Marginal. Use only as transparency layer.

---

## ★★★ STRONGEST FLIPS — TOP 6

1. **Asset 1+7 — Public live accountability ticker** (D5) — scoreboard + chain integrity → world-first.
2. **Asset 2 — What-if intervention lab** (D4) — slider → ripple map. World-first.
3. **Asset 3 — Fog regime badge** (D1 + drift) — adaptive bands shown as a "regime" card.
4. **Asset 8 — Rake doom disclosure** (D4) — passenger-facing doom card. (NTES cannot do this.)
5. **Asset 9 — Connection custody with HOLD action** (D1) — quantified hold + passenger-hours.
6. **Asset 14 — 6-hour corridor congestion radar** (D2) — network view, not single train.

---

*Generated: Phase 1 — Capability Flips. Strongest 6 flips drive Phase 2 ideas.*
