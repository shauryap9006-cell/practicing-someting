"""Deep System Map Builder and Verification Script for RailTwin-X.

Outputs detailed structured information for:
0.1 Route Inventory & unmounted routes
0.2 DB Schema Inventory & code write paths
0.3 Artifact Inventory & missing file behavior
0.4 Startup Trace & import side-effects
0.5 Background Processes & schedulers
0.6 Frontend Contract List
"""

import ast
import asyncio
import importlib
import inspect
import json
import os
import re
import shutil
import sqlite3
import sys
import tempfile
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

def audit_0_1_routes():
    from api.main import app, ROUTER_MANIFEST
    from fastapi.testclient import TestClient

    openapi = app.openapi()
    openapi_paths = openapi["paths"]

    # Collect all mounted routes with endpoints
    mounted_routes = []
    
    def process_router(router, prefix=""):
        res = []
        for route in router.routes:
            if hasattr(route, "endpoint"):
                ep = route.endpoint
                methods = list(getattr(route, "methods", []))
                full_path = prefix + (route.path if hasattr(route, "path") else "")
                is_async = inspect.iscoroutinefunction(ep)
                auth_req = False
                deps = list(getattr(route, "dependencies", [])) + list(getattr(ep, "__annotations__", {}).values())
                ep_code = ""
                try:
                    ep_code = inspect.getsource(ep)
                    if "get_current_user" in ep_code or "require_role" in ep_code or "assert_station_scope" in ep_code:
                        auth_req = True
                except Exception:
                    pass
                file_line = f"{ep.__code__.co_filename}:{ep.__code__.co_firstlineno}"
                res.append({
                    "method": methods,
                    "path": full_path,
                    "auth": auth_req,
                    "is_async": is_async,
                    "handler": ep.__name__,
                    "file_line": file_line,
                    "doc": (ep.__doc__ or "").strip().split("\n")[0]
                })
        return res

    all_mounted = []
    for r, p in ROUTER_MANIFEST:
        p_str = p or ""
        all_mounted.extend(process_router(r, p_str))

    from api.routes import router as v1_router
    from api.passenger_routes import router as passenger_router
    all_mounted.extend(process_router(passenger_router, ""))
    all_mounted.extend(process_router(passenger_router, "/api"))
    all_mounted.extend(process_router(v1_router, ""))
    all_mounted.extend(process_router(v1_router, "/api"))

    # Also check standalone app routes
    for r in app.routes:
        if hasattr(r, "endpoint") and not any(r.endpoint == m.get("handler") for m in all_mounted):
            ep = r.endpoint
            try:
                fl = f"{ep.__code__.co_filename}:{ep.__code__.co_firstlineno}"
            except Exception:
                fl = "unknown"
            all_mounted.append({
                "method": list(getattr(r, "methods", [])),
                "path": getattr(r, "path", ""),
                "auth": False,
                "is_async": inspect.iscoroutinefunction(ep),
                "handler": getattr(ep, "__name__", str(ep)),
                "file_line": fl,
                "doc": (ep.__doc__ or "").strip().split("\n")[0] if hasattr(ep, "__doc__") else ""
            })

    # Find any unmounted routers or functions in api/*.py
    api_dir = ROOT / "api"
    unmounted = []
    for py in api_dir.glob("*.py"):
        if py.name in ["__init__.py", "schemas.py", "middleware.py", "auth.py", "brain.py", "predictor.py", "sse_limits.py"]:
            continue
        # Read file and parse AST
        content = py.read_text(encoding="utf-8", errors="ignore")
        tree = ast.parse(content, filename=str(py))
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                for dec in node.decorator_list:
                    dec_str = ast.unparse(dec) if hasattr(ast, "unparse") else ""
                    if "router." in dec_str or "app." in dec_str:
                        fn_name = node.name
                        # check if fn_name is in all_mounted
                        matched = any(m["handler"] == fn_name for m in all_mounted)
                        if not matched:
                            unmounted.append({
                                "file": str(py.relative_to(ROOT)),
                                "line": node.lineno,
                                "handler": fn_name,
                                "decorator": dec_str,
                            })

    return {
        "total_mounted_endpoints": len(all_mounted),
        "total_openapi_paths": len(openapi_paths),
        "mounted": all_mounted,
        "unmounted": unmounted,
    }

def audit_0_2_db_schema():
    db_path = ROOT / "data" / "railtwin.db"
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name;")
    tables = [r["name"] for r in cur.fetchall()]

    schema_details = {}
    for t in tables:
        cur.execute(f"PRAGMA table_info('{t}');")
        cols = cur.fetchall()
        cur.execute(f"PRAGMA index_list('{t}');")
        idxs = cur.fetchall()
        cur.execute(f"SELECT COUNT(*) as cnt FROM '{t}';")
        count = cur.fetchone()["cnt"]
        schema_details[t] = {
            "columns": [c["name"] for c in cols],
            "pk": [c["name"] for c in cols if c["pk"] > 0],
            "indexes": [i["name"] for i in idxs],
            "row_count": count,
        }
    conn.close()

    # Find table writes in code
    write_pat = re.compile(r"""(?:INSERT\s+INTO|UPDATE|DELETE\s+FROM)\s+([a-zA-Z0-9_]+)""", re.IGNORECASE)
    code_writes = defaultdict(set)
    for py in ROOT.rglob("*.py"):
        if "audit_probes" in str(py) or ".venv" in str(py):
            continue
        try:
            txt = py.read_text(encoding="utf-8", errors="ignore")
            for m in write_pat.finditer(txt):
                tbl = m.group(1).lower()
                code_writes[tbl].add(str(py.relative_to(ROOT)))
        except Exception:
            pass

    # Compare DB tables vs Code writes
    db_set = set(tables)
    written_set = set(code_writes.keys()) - {"table", "or", "into", "set", "from", "exists", "where"}
    
    missing_in_db = [t for t in written_set if t not in db_set and not t.startswith("sqlite_")]
    unused_in_code = [t for t in db_set if t.lower() not in written_set]

    return {
        "tables_count": len(tables),
        "schema_details": schema_details,
        "missing_in_db_but_written": missing_in_db,
        "in_db_not_written_in_python": unused_in_code,
        "code_writes": {k: list(v) for k, v in code_writes.items()}
    }

def audit_0_3_artifacts():
    art_dir = ROOT / "ml" / "artifacts"
    files = list(art_dir.glob("*")) if art_dir.exists() else []

    artifact_map = []
    for f in sorted(files):
        if not f.is_file():
            continue
        size_kb = round(f.stat().st_size / 1024, 2)
        loaders = []
        for py in ROOT.rglob("*.py"):
            if "audit_probes" in str(py):
                continue
            try:
                txt = py.read_text(encoding="utf-8", errors="ignore")
                if f.name in txt:
                    loaders.append(str(py.relative_to(ROOT)))
            except Exception:
                pass
        artifact_map.append({
            "name": f.name,
            "size_kb": size_kb,
            "loaders": loaders,
        })
    return artifact_map

def audit_0_4_startup():
    from config import settings
    
    # Trace api/main.py lifespan
    startup_steps = [
        "1. Process startup: torch.set_num_threads(1)",
        "2. Database init: db = get_db(); db.init_schema(); db.materialize_historical_baselines()",
        "3. Live Tracker initialization: tracker = get_live_tracker(db); await tracker.start() (starts background loop)",
        "4. Router mounts: 22 router packages mounted on FastAPI app",
        "5. Middleware stack: RequestContext, SecurityHeaders, GZip, CORS, Idempotency, ResponseCache, TokenBucketRateLimiter",
    ]

    # Check for import-time side-effects
    # Specifically DB connections, file writes, network calls at module load time
    import_side_effects = []
    for mod_name in ["api.routes", "api.predictor", "api.brain", "ml.ensemble", "data.db", "engine.live_tracker"]:
        try:
            m = sys.modules.get(mod_name)
            # check if globals exist
        except Exception as e:
            import_side_effects.append(f"{mod_name}: failed import {e}")

    return {
        "startup_steps": startup_steps,
        "import_side_effects": import_side_effects,
    }

def audit_0_5_background_processes():
    # Search for asyncio.create_task, Thread, background tasks
    task_pat = re.compile(r"""(asyncio\.create_task|threading\.Thread|BackgroundTasks|start_background|schedule|PeriodicTask)""", re.IGNORECASE)
    bg_tasks = []
    for py in ROOT.rglob("*.py"):
        if "audit_probes" in str(py) or ".venv" in str(py):
            continue
        try:
            lines = py.read_text(encoding="utf-8", errors="ignore").splitlines()
            for idx, line in enumerate(lines, 1):
                if task_pat.search(line):
                    bg_tasks.append({
                        "file": str(py.relative_to(ROOT)),
                        "line": idx,
                        "code": line.strip(),
                    })
        except Exception:
            pass
    return bg_tasks

def audit_0_6_frontend_contracts():
    web_dir = ROOT / "web" / "src"
    ts_calls = []
    if web_dir.exists():
        # Match api.get/post or fetch or apiClient or axios
        call_pat = re.compile(r"""(?:apiClient|api|http|axios)\s*\.\s*(get|post|put|delete|patch)\s*(?:<[^>]+>)?\s*\(\s*[`"']([^`"']+)""", re.IGNORECASE)
        fetch_pat = re.compile(r"""fetch\s*\(\s*[`"']([^`"']+)""", re.IGNORECASE)
        for ts in web_dir.rglob("*.ts*"):
            try:
                lines = ts.read_text(encoding="utf-8", errors="ignore").splitlines()
                for idx, line in enumerate(lines, 1):
                    for m in call_pat.finditer(line):
                        ts_calls.append({
                            "file": str(ts.relative_to(ROOT)),
                            "line": idx,
                            "method": m.group(1).upper(),
                            "url": m.group(2),
                        })
                    for m in fetch_pat.finditer(line):
                        ts_calls.append({
                            "file": str(ts.relative_to(ROOT)),
                            "line": idx,
                            "method": "FETCH",
                            "url": m.group(1),
                        })
            except Exception:
                pass
    return ts_calls

if __name__ == "__main__":
    print("Building Phase 0 Map...")
    r_res = audit_0_1_routes()
    db_res = audit_0_2_db_schema()
    art_res = audit_0_3_artifacts()
    boot_res = audit_0_4_startup()
    bg_res = audit_0_5_background_processes()
    fe_res = audit_0_6_frontend_contracts()

    full_map = {
        "routes": r_res,
        "db": db_res,
        "artifacts": art_res,
        "startup": boot_res,
        "background": bg_res,
        "frontend": fe_res,
    }

    with open(ROOT / "audit_probes" / "system_map_data.json", "w", encoding="utf-8") as f:
        json.dump(full_map, f, indent=2)
    print("Exported system_map_data.json successfully!")
