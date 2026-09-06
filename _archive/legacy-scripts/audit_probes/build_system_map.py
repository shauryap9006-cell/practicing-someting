"""RailTwin-X Audit Probe: System Map Builder (Phase 0).

Gathers:
1. Route Inventory & unmounted route cross-check
2. DB Schema Inventory & code write paths
3. ML Artifact Inventory & loader references
4. Startup Trace & import-time side-effects
5. Background Processes & tasks
6. Frontend Contract List from web/src
"""

import ast
import glob
import inspect
import json
import os
import re
import sqlite3
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

def build_route_inventory():
    from api.main import app
    from fastapi.routing import APIRoute

    mounted_routes = []
    for route in app.routes:
        if isinstance(route, APIRoute):
            mounted_routes.append({
                "path": route.path,
                "methods": sorted(list(route.methods - {"HEAD", "OPTIONS"})),
                "name": route.name,
                "endpoint": f"{route.endpoint.__module__}.{route.endpoint.__name__}",
                "is_async": inspect.iscoroutinefunction(route.endpoint),
            })

    # Now inspect source files in api/
    api_dir = ROOT / "api"
    source_routes = []
    for py_file in api_dir.glob("*.py"):
        if py_file.name in ["__init__.py", "schemas.py", "middleware.py", "auth.py", "brain.py", "predictor.py", "sse_limits.py"]:
            continue
        try:
            with open(py_file, "r", encoding="utf-8") as f:
                code = f.read()
            tree = ast.parse(code, filename=str(py_file))
            lines = code.splitlines()
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    for dec in node.decorator_list:
                        dec_str = ast.unparse(dec) if hasattr(ast, "unparse") else ""
                        if "router." in dec_str or "app." in dec_str:
                            source_routes.append({
                                "file": str(py_file.relative_to(ROOT)),
                                "line": node.lineno,
                                "name": node.name,
                                "is_async": isinstance(node, ast.AsyncFunctionDef),
                                "decorator": dec_str,
                            })
        except Exception as e:
            source_routes.append({"file": str(py_file.relative_to(ROOT)), "error": str(e)})

    return mounted_routes, source_routes

def build_db_schema_inventory():
    db_path = ROOT / "data" / "railtwin.db"
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # Get all tables
    cur.execute("SELECT name, sql FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name;")
    tables = cur.fetchall()

    schema_info = {}
    for t in tables:
        tname = t["name"]
        cur.execute(f"PRAGMA table_info('{tname}');")
        cols = cur.fetchall()
        cur.execute(f"PRAGMA index_list('{tname}');")
        idxs = cur.fetchall()
        cur.execute(f"SELECT COUNT(*) as cnt FROM '{tname}';")
        count = cur.fetchone()["cnt"]
        schema_info[tname] = {
            "columns": [{"name": c["name"], "type": c["type"], "notnull": c["notnull"], "pk": c["pk"]} for c in cols],
            "indexes": [dict(i) for i in idxs],
            "row_count": count,
        }
    conn.close()

    # Grep code for table writes
    write_patterns = [
        re.compile(r"INSERT\s+INTO\s+([a-zA-Z0-9_]+)", re.IGNORECASE),
        re.compile(r"UPDATE\s+([a-zA-Z0-9_]+)\s+SET", re.IGNORECASE),
        re.compile(r"DELETE\s+FROM\s+([a-zA-Z0-9_]+)", re.IGNORECASE),
    ]

    code_tables = defaultdict(lambda: {"writes": [], "reads": []})
    for ext in ["*.py", "*.sql"]:
        for fpath in ROOT.rglob(ext):
            if "node_modules" in str(fpath) or ".venv" in str(fpath) or "audit_probes" in str(fpath):
                continue
            try:
                content = fpath.read_text(encoding="utf-8", errors="ignore")
                for wp in write_patterns:
                    for match in wp.finditer(content):
                        tname = match.group(1).lower()
                        code_tables[tname]["writes"].append(str(fpath.relative_to(ROOT)))
            except Exception:
                pass

    return schema_info, code_tables

def build_artifact_inventory():
    art_dir = ROOT / "ml" / "artifacts"
    artifacts = []
    if art_dir.exists():
        for f in art_dir.glob("*"):
            if f.is_file():
                # search for usages
                usages = []
                for py in ROOT.rglob("*.py"):
                    if "audit_probes" in str(py):
                        continue
                    try:
                        c = py.read_text(encoding="utf-8", errors="ignore")
                        if f.name in c:
                            usages.append(str(py.relative_to(ROOT)))
                    except Exception:
                        pass
                artifacts.append({
                    "name": f.name,
                    "size_bytes": f.stat().st_size,
                    "usages": usages
                })
    return artifacts

def build_frontend_contracts():
    web_dir = ROOT / "web" / "src"
    api_calls = []
    if web_dir.exists():
        url_pat = re.compile(r"""(?:axios|fetch|apiClient|get|post|put|delete|patch)\s*\(\s*[`"']([^`"']+)""", re.IGNORECASE)
        # also template literals with url
        url_template_pat = re.compile(r"""(?:url|path|endpoint):\s*[`"']([^`"']+)""", re.IGNORECASE)
        for ts_file in web_dir.rglob("*.ts*"):
            try:
                content = ts_file.read_text(encoding="utf-8", errors="ignore")
                for line_no, line in enumerate(content.splitlines(), start=1):
                    for m in url_pat.finditer(line):
                        api_calls.append({
                            "file": str(ts_file.relative_to(ROOT)),
                            "line": line_no,
                            "raw": m.group(1),
                        })
                    for m in url_template_pat.finditer(line):
                        api_calls.append({
                            "file": str(ts_file.relative_to(ROOT)),
                            "line": line_no,
                            "raw": m.group(1),
                        })
            except Exception:
                pass
    return api_calls

if __name__ == "__main__":
    print("Collecting Route Inventory...")
    mounted, source = build_route_inventory()
    print(f"Mounted APIRoutes: {len(mounted)}, Source decorated functions: {len(source)}")

    print("Collecting DB Schema Inventory...")
    schema, code_tables = build_db_schema_inventory()
    print(f"DB Tables count: {len(schema)}")

    print("Collecting Artifact Inventory...")
    artifacts = build_artifact_inventory()
    print(f"Artifacts count: {len(artifacts)}")

    print("Collecting Frontend Contracts...")
    fe_calls = build_frontend_contracts()
    print(f"Frontend API calls found: {len(fe_calls)}")

    out = {
        "mounted_routes": mounted,
        "source_routes": source,
        "schema": schema,
        "code_tables": {k: list(set(v["writes"])) for k, v in code_tables.items()},
        "artifacts": artifacts,
        "frontend_calls": fe_calls,
    }
    with open(ROOT / "audit_probes" / "raw_system_map.json", "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)
    print("Saved to audit_probes/raw_system_map.json")
