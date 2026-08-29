# RailTwin-X — Architecture Decision Records (04_DECISIONS.md)

**Baseline Git SHA:** `d074cc69188948644de72cad7bd4a248547e26ac`  
**Audit Date:** 2026-08-28  

---

### ADR-001: Zero-ML Deterministic Boundary in Safety Interlock Layer
- **Date:** 2026-08-27
- **Decision:** Keep `safety/interlock.py` completely isolated from machine learning libraries (`torch`, `lightgbm`, `sklearn`, `scipy`). Enforce all 5 kinematic safety rules using pure Python standard library primitives.
- **Rationale:** Safety-critical railway operations cannot permit uninterpretable black-box ML failure modes or numerical hallucinations to reach live dispatch controllers.
- **Alternatives Rejected:** Training a secondary neural network classifier to detect anomalies (rejected due to lack of deterministic guarantees).

### ADR-002: Architectural Guarantee of Non-Crossing Quantile Neural Forecaster
- **Date:** 2026-08-27
- **Decision:** Enforce quantile monotonicity ($p_{10} \le p_{50} \le p_{90}$) in the PyTorch GRU using cumulative `softplus` parameterization rather than post-hoc sorting or heuristic clipping.
- **Rationale:** Ensures valid confidence interval semantics $[p_{10}, p_{90}]$ directly during gradient descent training, eliminating quantile inversion at the source.

---

AUDIT_BASELINE: d074cc69188948644de72cad7bd4a248547e26ac | 2026-08-28 | audit-v2.0
