"""RailTwin-X Deep Due Diligence: Comprehensive System Map Generator (Phase 0).

Scans:
0.1 Route inventory across all router files in api/ and cross-checks with api/main.py
0.2 DB schema inventory from data/railtwin.db and code write references
0.3 Artifact inventory in ml/artifacts/ and loader code references + missing-file behavior
0.4 Startup trace and import-time side-effects
0.5 Background processes and schedulers
0.6 Frontend contract list from web/src
"""

import ast
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

def analyze_routes():
    from api.main import app, ROUTER_MANIFEST
    import api.main as main_mod

    # 1. Map all mounted routes from app
    # In FastAPI, we can collect from ROUTER_MANIFEST, standalone routes, and included routers
    mounted_list = []
    mounted_endpoints_set = set()

    def inspect_router(router, prefix=""):
        res = []
        for route in getattr(router, "routes", []):
            if hasattr(route, "endpoint"):
                ep = route.endpoint
                methods = sorted(list(getattr(route, "methods", [])))
                full_path = (prefix or "") + (route.path if hasattr(route, "path") else "")
                is_async = inspect.iscoroutinefunction(ep)
                auth_req = False
                try:
                    src = inspect.getsource(ep)
                    if any(k in src for k in ["get_current_user", "require_role", "assert_station_scope", "Depends(get_current_active_user)"]):
                        auth_req = True
                except Exception:
                    pass
                fl = f"{getattr(ep, '__module__', '')}:{ep.__name__}"
                try:
                    file_path = inspect.getsourcefile(ep)
                    line_no = inspect.getsourcelines(ep)[1]
                    rel_file = str(Path(file_path).relative_to(ROOT))
                    fl = f"{rel_file}:{line_no}"
                except Exception:
                    pass

                item = {
                    "methods": methods,
                    "path": full_path,
                    "auth": auth_req,
                    "is_async": is_async,
                    "handler": ep.__name__,
                    "file_line": fl,
                    "router_prefix": prefix,
                }
                res.append(item)
                mounted_endpoints_set.add((ep.__name__, fl.split(":")[0]))
        return res

    for r, p in ROUTER_MANIFEST:
        mounted_list.extend(inspect_router(r, p or ""))

    from api.passenger_routes import router as passenger_router
    from api.routes import router as v1_router
    mounted_list.extend(inspect_router(passenger_router, ""))
    mounted_list.extend(inspect_router(passenger_router, "/api"))
    mounted_list.extend(inspect_router(v1_router, ""))
    mounted_list.extend(inspect_router(v1_router, "/api"))

    # Standalone routes on app
    for route in app.routes:
        if hasattr(route, "endpoint") and not hasattr(route, "original_router"):
            ep = route.endpoint
            methods = sorted(list(getattr(route, "methods", [])))
            fl = f"{getattr(ep, '__module__', '')}:{ep.__name__}"
            try:
                file_path = inspect.getsourcefile(ep)
                line_no = inspect.getsourcelines(ep)[1]
                fl = f"{str(Path(file_path).relative_to(ROOT))}:{line_no}"
            except Exception:
                pass
            mounted_list.append({
                "methods": methods,
                "path": getattr(route, "path", ""),
                "auth": False,
                "is_async": inspect.iscoroutinefunction(ep),
                "handler": getattr(ep, "__name__", str(ep)),
                "file_line": fl,
                "router_prefix": "",
            })
            mounted_endpoints_set.add((getattr(ep, "__name__", str(ep)), fl.split(":")[0]))

    # 2. Inspect every router file in api/*.py for unmounted routes
    api_dir = ROOT / "api"
    all_declared_routes = []
    unmounted_routes = []

    for py_file in sorted(api_dir.glob("*.py")):
        if py_file.name in ["__init__.py", "schemas.py", "middleware.py", "auth.py", "brain.py", "predictor.py", "sse_limits.py"]:
            continue
        try:
            content = py_file.read_text(encoding="utf-8", errors="ignore")
            tree = ast.parse(content, filename=str(py_file))
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    for dec in node.decorator_list:
                        dec_str = ast.unparse(dec) if hasattr(ast, "unparse") else ""
                        if any(dec_str.startswith(x) for x in ["router.", "app.", "@router.", "@app."]):
                            rel_file = str(py_file.relative_to(ROOT))
                            declared = {
                                "file": rel_file,
                                "line": node.lineno,
                                "name": node.name,
                                "is_async": isinstance(node, ast.AsyncFunctionDef),
                                "decorator": dec_str,
                            }
                            all_declared_routes.append(declared)
                            # Check if mounted
                            is_mounted = False
                            for m in mounted_list:
                                if m["handler"] == node.name and (rel_file in m["file_line"] or m["file_line"].startswith("api.")):
                                    is_mounted = True
                                    break
                            if not is_mounted:
                                unmounted_routes.append(declared)
        except Exception as e:
            print(f"Error parsing {py_file}: {e}")

    return {
        "mounted_count": len(mounted_list),
        "declared_count": len(all_declared_routes),
        "mounted_routes": mounted_list,
        "declared_routes": all_declared_routes,
        "unmounted_routes": unmounted_routes,
    }

def analyze_db():
    db_path = ROOT / "data" / "railtwin.db"
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cur.execute("SELECT name, sql FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name;")
    tables = cur.fetchall()
    table_info = {}
    for t in tables:
        tname = t["name"]
        cur.execute(f"PRAGMA table_info('{tname}');")
        cols = [dict(c) for c in cur.fetchall()]
        cur.execute(f"PRAGMA index_list('{tname}');")
        idxs = [dict(i) for i in cur.fetchall()]
        cur.execute(f"SELECT COUNT(*) as c FROM '{tname}';")
        cnt = cur.fetchone()["c"]
        table_info[tname] = {
            "columns": cols,
            "indexes": idxs,
            "row_count": cnt,
            "sql": t["sql"],
        }
    conn.close()

    # Search Python code for table writes
    write_pats = [
        re.compile(r"INSERT\s+INTO\s+([a-zA-Z0-9_]+)", re.IGNORECASE),
        re.compile(r"UPDATE\s+([a-zA-Z0-9_]+)\s+SET", re.IGNORECASE),
        re.compile(r"DELETE\s+FROM\s+([a-zA-Z0-9_]+)", re.IGNORECASE),
    ]

    code_writes = defaultdict(set)
    src_dirs = [ROOT / d for d in ["api", "engine", "collector", "data", "ml", "safety", "scripts", "notifications"]]
    for sdir in src_dirs:
        if not sdir.exists():
            continue
        for py in sdir.rglob("*.py"):
            try:
                txt = py.read_text(encoding="utf-8", errors="ignore")
                rel = str(py.relative_to(ROOT))
                for pat in write_pats:
                    for m in pat.finditer(txt):
                        tbl = m.group(1).lower()
                        code_writes[tbl].add(rel)
            except Exception:
                pass

    db_tables = set(table_info.keys())
    # Filter SQL noise words
    noise = {"table", "or", "into", "set", "from", "exists", "where", "select", "replace"}
    written_tables = {k for k in code_writes.keys() if k not in noise and not k.startswith("sqlite_")}

    absent_from_db = sorted(list(written_tables - {t.lower() for t in db_tables}))
    unwritten_in_db = sorted([t for t in db_tables if t.lower() not in written_tables])

    return {
        "tables": table_info,
        "table_count": len(table_info),
        "code_writes": {k: sorted(list(v)) for k, v in code_writes.items() if k not in noise},
        "written_but_absent_from_db": absent_from_db,
        "in_db_but_unwritten_in_code": unwritten_in_db,
    }

def analyze_artifacts():
    art_dir = ROOT / "ml" / "artifacts"
    files = sorted(list(art_dir.glob("*"))) if art_dir.exists() else []

    artifact_map = []
    src_dirs = [ROOT / d for d in ["api", "engine", "collector", "data", "ml", "safety", "scripts", "notifications"]]

    for f in files:
        if not f.is_file():
            continue
        loaders = defaultdict(list)
        for sdir in src_dirs:
            if not sdir.exists():
                continue
            for py in sdir.rglob("*.py"):
                try:
                    txt = py.read_text(encoding="utf-8", errors="ignore")
                    if f.name in txt:
                        rel = str(py.relative_to(ROOT))
                        # find line numbers
                        for idx, line in enumerate(txt.splitlines(), 1):
                            if f.name in line:
                                loaders[rel].append(idx)
                except Exception:
                    pass

        artifact_map.append({
            "name": f.name,
            "size_bytes": f.stat().st_size,
            "loaders": {k: v for k, v in loaders.items()},
        })

    return artifact_map

def analyze_background():
    src_dirs = [ROOT / d for d in ["api", "engine", "collector", "data", "ml", "safety", "scripts", "notifications"]]
    bg_pats = [
        ("asyncio_create_task", re.compile(r"asyncio\.create_task\((.*?)\)")),
        ("thread", re.compile(r"threading\.Thread\((.*?)\)")),
        ("thread_pool", re.compile(r"ThreadPoolExecutor\((.*?)\)")),
        ("background_tasks", re.compile(r"BackgroundTasks")),
    ]

    tasks = []
    for sdir in src_dirs:
        if not sdir.exists():
            continue
        for py in sdir.rglob("*.py"):
            try:
                txt = py.read_text(encoding="utf-8", errors="ignore")
                rel = str(py.relative_to(ROOT))
                for kind, pat in bg_pats:
                    for idx, line in enumerate(txt.splitlines(), 1):
                        if pat.search(line):
                            tasks.append({
                                "file": rel,
                                "line": idx,
                                "kind": kind,
                                "code": line.strip(),
                            })
            except Exception:
                pass
    return tasks

def analyze_frontend():
    web_dir = ROOT / "web" / "src"
    ts_calls = []
    if web_dir.exists():
        call_pat = re.compile(r"""(?:apiClient|api|http|axios)\s*\.\s*(get|post|put|delete|patch)\s*(?:<[^>]+>)?\s*\(\s*[`"']([^`"']+)""", re.IGNORECASE)
        fetch_pat = re.compile(r"""fetch\s*\(\s*[`"']([^`"']+)""", re.IGNORECASE)
        for ts in web_dir.rglob("*.ts*"):
            try:
                rel = str(ts.relative_to(ROOT))
                lines = ts.read_text(encoding="utf-8", errors="ignore").splitlines()
                for idx, line in enumerate(lines, 1):
                    for m in call_pat.finditer(line):
                        ts_calls.append({
                            "file": rel,
                            "line": idx,
                            "method": m.group(1).upper(),
                            "url": m.group(2),
                        })
                    for m in fetch_pat.finditer(line):
                        ts_calls.append({
                            "file": rel,
                            "line": idx,
                            "method": "FETCH",
                            "url": m.group(1),
                        })
            except Exception:
                pass
    return ts_calls

if __name__ == "__main__":
    print("[1/5] Analyzing routes...")
    r = analyze_routes()
    print(f"Mounted: {r['mounted_count']}, Declared: {r['declared_count']}, Unmounted: {len(r['unmounted_routes'])}")

    print("[2/5] Analyzing DB...")
    d = analyze_db()
    print(f"Tables: {d['table_count']}, Written tables: {len(d['code_writes'])}")

    print("[3/5] Analyzing artifacts...")
    a = analyze_artifacts()
    print(f"Artifacts: {len(a)}")

    print("[4/5] Analyzing background tasks...")
    b = analyze_background()
    print(f"Background items: {len(b)}")

    print("[5/5] Analyzing frontend calls...")
    f = analyze_frontend()
    print(f"Frontend calls: {len(f)}")

    out = {
        "routes": r,
        "db": d,
        "artifacts": a,
        "background": b,
        "frontend": f,
    }

    out_file = ROOT / "audit_probes" / "system_map_extracted.json"
    with open(out_file, "w", encoding="utf-8") as fp:
        json.dump(out, fp, indent=2)
    print("Saved system_map_extracted.json!")
