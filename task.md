# RailTwin-X v3 Audit Fix — Task Tracker

- [x] Step 1: `data/holidays.json` — Indian Railways holiday calendar
- [x] Step 2: `ml/snapshots.py` — day_type=2, fog-hour weighting
- [x] Step 3: `ml/train.py` — early stopping, q_hat delta/GRU, feature importance, B3, Wilcoxon gate
- [x] Step 4: `ml/model_seq.py` — gradient clipping, patience early stopping
- [x] Step 5: `ml/evaluate.py` — autoregressive rollout, error bars, B3
- [x] Step 6: `ml/ensemble.py` — horizon weights, Wilcoxon gate, GRU CQR
- [x] Step 7: `api/predictor.py` — autoregressive rollout, delta q_hat
- [x] Step 8: `safety/interlock.py` — priority recovery, cancellation flag
- [x] Step 9: `api/main.py` — WebSocket, API key middleware
- [x] Step 10: `tests/test_model_accuracy.py` — regression test
- [x] Step 11: `ml/audit.py` — updated audit with all new checks
- [x] Step 12: `docs/architecture.md` — Mermaid architecture diagram
