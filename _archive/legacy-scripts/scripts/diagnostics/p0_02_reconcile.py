# -*- coding: utf-8 -*-
"""Recompute every number ever reported. Every FAIL is a finding."""
import math
from pathlib import Path

OUT = Path("control-room/23_DIAGNOSTICS"); OUT.mkdir(parents=True, exist_ok=True)
lines = []

def p(s=""):
    print(s)
    lines.append(str(s))

def check(name, reported, recomputed, tol):
    ok = abs(float(reported) - float(recomputed)) <= tol
    p(f"[{'OK  ' if ok else 'FAIL'}] {name}: reported={reported} recomputed={recomputed:.6f}")

p("=== NUMBER RECONCILIATION ===")
# --- Round 3 training-log identities ---
check("EMA residual d=0.999 T=1092",        0.3353615, 0.999**1092, 1e-4)
check("old steps/epoch (N=23100, b=256)",   91, math.ceil(23100/256), 0)
check("old total steps (91 x 12)",          1092, 91*12, 0)
check("new steps/epoch (N=18900, b=256)",   74, math.ceil(18900/256), 0)
check("new total steps (74 x 40)",          2960, 74*40, 0)
# --- Round 4 report ---
check("'-5.5% vs champion' true value",     0.055, (5.9021-5.6270)/5.9021, 1e-4)
check("ensemble CRPS gain round 4",         0.005, (4.3540-4.3321)/4.3540, 1e-4)
# --- Round 5 report ---
check("'4.11% gain' vs 'sigma=4.1116' digit collision", 1,
      int(round(4.1116, 2) == round(4.11, 2)), 0)
p(f"\n[FLAG] champion MAE 150743.0 vs documented 10.72 -> ratio = {150743.0/10.72:,.0f}x")
p(f"[FLAG] champion CRPS/MAE = {133984.6139/150743.0:.4f} (constant-fallback would be ~1.0; "
  f"0.889 means champion produced LARGE VARYING outputs => input-scale/domain bug suspected)")
p("[FLAG] '100 calendar days containing 564 corridor-level fog days' -- 564 > 100: resolve in Phase 3")
p("[FLAG] corpus sizes in record: 3,066,052 documented / 333k claimed / 206,363 seqs -- resolve in Phase 1")
p("[FLAG] val '44 days' but range 2025-11-06 -> 2026-08-29 = 296 days -- resolve in Phase 3")

(OUT / "02_reconcile.txt").write_text("\n".join(lines), encoding="utf-8")
