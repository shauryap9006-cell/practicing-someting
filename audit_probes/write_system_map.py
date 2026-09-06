import json
from pathlib import Path

routes_mounted = json.load(open("audit_probes/routes_mounted.json", encoding="utf-8"))
db_inv = json.load(open("audit_probes/db_schema_inventory.json", encoding="utf-8"))
art_usage = json.load(open("audit_probes/artifact_usage.json", encoding="utf-8"))
bg_tasks = json.load(open("audit_probes/background_tasks.json", encoding="utf-8"))
fe_contracts = json.load(open("audit_probes/frontend_contracts.json", encoding="utf-8"))
fe_cross = json.load(open("audit_probes/frontend_backend_cross_check.json", encoding="utf-8"))

lines = []
lines.append("# RailTwin-X System Map (Phase 0 Audit Deliverable)")
lines.append("")
lines.append("> Generated via dynamic introspection and static AST cross-referencing.")
lines.append("> Environment: Windows / PowerShell / Python 3.14 / SQLite / FastAPI.")
lines.append("")
lines.append("---")
lines.append("")

# 0.1 ROUTE INVENTORY
lines.append("## 0.1 ROUTE INVENTORY")
lines.append("")
lines.append(f"Total Mounted Routes: **{len(routes_mounted)}**")
lines.append("All 22 router modules in `api/` are included in `api/main.py`. Unmounted router files: **0**.")
lines.append("")
lines.append("| HTTP Method(s) | Full Path | Auth Required | Handler Function | Async? | Source Location |")
lines.append("|---|---|---|---|---|---|")
for r in sorted(routes_mounted, key=lambda x: (x['path'], x['methods'])):
    m = ", ".join(r['methods'])
    auth_str = "YES" if r['auth'] else "NO"
    async_str = "async" if r['async'] else "sync (def)"
    lines.append(f"| `{m}` | `{r['path']}` | {auth_str} | `{r['handler']}` | {async_str} | `{r['location']}` |")

lines.append("")
lines.append("---")
lines.append("")

# 0.2 DB SCHEMA INVENTORY
lines.append("## 0.2 DATABASE SCHEMA INVENTORY (data/railtwin.db)")
lines.append("")
lines.append(f"Total tables in active database: **{len(db_inv['db_tables'])}**")
lines.append(f"Total tables written across codebase: **{len(db_inv['code_written_tables'])}**")
lines.append("")
lines.append("### Critical Schema Anomalies")
lines.append("1. **Table Absent from DB but Referenced in Feature Pipeline:** `route_cum_km`")
lines.append("   - Referenced in `ml/features_v3.py:234` (`SELECT train_no, station_code, seq, cum_km FROM route_cum_km`).")
lines.append("   - Because the table does not exist in `data/railtwin.db`, the query raises `OperationalError` which is swallowed by `except Exception: pass`, silently aborting the fallback query and leaving `cum_km_map`, `train_routes`, and `route_seq_map` empty.")
lines.append("2. **Tables Present in DB with Zero Writes in Code:**")
for t in db_inv['tables_in_db_not_written_in_code']:
    cnt = db_inv['details'][t]['row_count']
    lines.append(f"   - `{t}` ({cnt} rows in DB, 0 write call sites across `api/`, `engine/`, `collector/`, `safety/`, `scripts/`)")
lines.append("")

lines.append("### Table Inventory Table")
lines.append("| Table Name | Row Count | Column Count | Indexes | Writing Modules / Code Paths |")
lines.append("|---|---|---|---|---|")
for t_name in sorted(db_inv['db_tables']):
    t_info = db_inv['details'][t_name]
    writes = db_inv['table_writes'].get(t_name.lower(), [])
    write_summary = f"{len(writes)} write site(s): " + ", ".join(writes[:2]) if writes else "NONE (read-only/orphan)"
    if len(writes) > 2:
        write_summary += f" (+{len(writes)-2} more)"
    idx_names = [i['name'] for i in t_info['indexes'] if not i['name'].startswith('sqlite_autoindex')]
    idx_summary = ", ".join(idx_names) if idx_names else "None (PK only)"
    lines.append(f"| `{t_name}` | {t_info['row_count']} | {len(t_info['columns'])} | {idx_summary} | {write_summary} |")

lines.append("")
lines.append("---")
lines.append("")

# 0.3 ARTIFACT INVENTORY
lines.append("## 0.3 ARTIFACT INVENTORY (ml/artifacts/)")
lines.append("")
lines.append("| Artifact Filename | Size | Code References | Primary Consumer | Boot Impact If Missing |")
lines.append("|---|---|---|---|---|")
for fname in sorted(art_usage.keys()):
    locs = art_usage[fname]
    ref_count = len(locs)
    primary = locs[0].split(":")[0] if locs else "Unreferenced / Static output"
    
    # Assess boot impact
    if fname in ["manifest.json", "model_direct_q10.txt", "model_direct_q50.txt", "model_direct_q90.txt", "artifact_integrity.json", "metrics.json"]:
        boot_impact = "CRITICAL: /v1/health reports models unavailable, ready=False; production raises RuntimeError"
    elif fname == "registry.json":
        boot_impact = "HIGH: Falls back to hardcoded champion 'LightGBM_Quantile_Direct'"
    elif fname == "model_gru_challenger.pt":
        boot_impact = "HIGH: GRU Challenger fails to load, logs warning, challenger fallback fails"
    elif fname == "drift_report.json":
        boot_impact = "LOW: /v1/health defaults drift status to GREEN and model trust to HIGH"
    elif fname == "model_lr_benchmark.pkl":
        boot_impact = "MEDIUM: Linear regression baseline model fails in evaluate.py / ensemble.py"
    else:
        boot_impact = "INFORMATIONAL: Evaluator or diagnostic output artifact"
        
    p = Path("ml/artifacts") / fname
    sz = f"{p.stat().st_size:,} bytes" if p.exists() else "Missing"
    lines.append(f"| `{fname}` | {sz} | {ref_count} call site(s) | `{primary}` | {boot_impact} |")

lines.append("")
lines.append("---")
lines.append("")

# 0.4 STARTUP TRACE
lines.append("## 0.4 STARTUP TRACE & LIFECYCLE ORDER")
lines.append("")
lines.append("### Execution Sequence in `api/main.py:lifespan`:")
lines.append("1. **Threadpool Configuration**: `torch.set_num_threads(1)` caps torch execution to 1 thread to avoid thread contention.")
lines.append("2. **Database Initialization**: `db = get_db(); db.init_schema()` validates DB file, runs DDL, and applies outstanding migrations from `scripts/migrations/*.sql`.")
lines.append("3. **Historical Baseline Materialization**: `db.materialize_historical_baselines()` runs aggregate queries to populate `hist_baselines` table.")
lines.append("4. **Row Count Telemetry**: `counts = db.table_counts()` logs loaded station events count.")
lines.append("5. **Background Tracker Start**: `tracker = get_live_tracker(db); await tracker.start()` launches asyncio background task `_run_loop()`.")
lines.append("6. **Model Loading Pattern**: **LAZY ON-DEMAND**. Models are NOT eagerly loaded in `lifespan`. They are initialized on the first inbound request to `/v1/health` or `/v1/trains/{train_no}/eta` via `get_predictor_service()`.")
lines.append("7. **Import-Time Side Effects**: **0**. Probe script detected zero database queries or network socket connections at module import time.")
lines.append("")
lines.append("---")
lines.append("")

# 0.5 BACKGROUND PROCESSES
lines.append("## 0.5 BACKGROUND PROCESSES")
lines.append("")
lines.append("| Process / Task Name | Type | Started By | Supervised / Survives Errors? | Graceful Shutdown? | Multi-Worker / Reload Hazard |")
lines.append("|---|---|---|---|---|---|")
lines.append("| `LiveTracker._run_loop()` | `asyncio.Task` (`engine/live_tracker.py:191`) | `lifespan` startup (`api/main.py:68`) | YES (`except Exception: pass` inside loop) | YES (`await tracker.stop()` cancels task on shutdown) | **HIGH**: If running multiple uvicorn workers (e.g. `-w 4`), each worker executes `lifespan` and launches an independent tracker loop writing concurrently to SQLite |")
lines.append("")
lines.append("---")
lines.append("")

# 0.6 FRONTEND CONTRACT AUDIT
lines.append("## 0.6 FRONTEND CONTRACT LIST & CROSS-LAYER PARITY")
lines.append("")
lines.append(f"Total Unique Frontend Endpoints: **{len(fe_contracts)}**")
lines.append(f"Matching Backend Routes: **{len(fe_cross['matches'])}**")
lines.append(f"Contract Mismatches: **{len(fe_cross['mismatches'])}**")
lines.append("")
lines.append("### Definite Contract Mismatches Found")
lines.append("| Frontend Endpoint Call | Frontend Source | Backend Route Status | Severity | Failure Impact |")
lines.append("|---|---|---|---|---|")
lines.append("| `POST /api/platform/rollback` | `web/src/lib/api.ts:624` | **NONEXISTENT ROUTE** | **HIGH** | UI button for platform rollback throws 404/405 |")
lines.append("| `POST /api/safety/tsr/${id}/lift` | `web/src/lib/api.ts:841` | Backend route is `DELETE /api/safety/tsr/{tsr_id}` | **HIGH** | UI 'Lift TSR' action sends POST .../lift, returns 405 Method Not Allowed |")
lines.append("| `POST /api/section/handoffs/${id}/ack` | `web/src/lib/api.ts:876` | Backend route is `PUT /handoff/{lock_id}/grant` | **HIGH** | Section controller handoff acknowledgement fails with 404 Not Found |")
lines.append("| `POST /api/workforce/crew/signon` | `web/src/lib/api.ts:747` | Backend route is `POST /api/workforce/crew/sign-on` (hyphenated) | **HIGH** | Crew sign-on submission fails with 404 Not Found |")
lines.append("")

Path("audit_probes/SYSTEM_MAP.md").write_text("\n".join(lines), encoding="utf-8")
print(f"Successfully wrote audit_probes/SYSTEM_MAP.md ({len(lines)} lines)")
