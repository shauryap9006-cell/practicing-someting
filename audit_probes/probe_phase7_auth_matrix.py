import json
import re
from pathlib import Path
from fastapi.testclient import TestClient

routes = json.load(open("audit_probes/routes_mounted.json"))

mutating_routes = []
open_mutating_routes = []

for r in routes:
    methods = r["methods"]
    is_mutating = any(m in ["POST", "PUT", "PATCH", "DELETE"] for m in methods)
    if is_mutating:
        mutating_routes.append(r)
        if not r["auth"]:
            open_mutating_routes.append(r)

print(f"Total mutating routes: {len(mutating_routes)}")
print(f"Open mutating routes (NO AUTH): {len(open_mutating_routes)}")
for om in open_mutating_routes:
    print(f"  {','.join(om['methods']):6} {om['path']} -> {om['location']} ({om['handler']})")

# 7.4 SQL Injection Scan: find f-strings, format, % in execute()
print("\nScanning for SQL formatting/interpolation near execute():")
root = Path.cwd()
code_dirs = [root / d for d in ["api", "engine", "collector", "data", "safety", "scripts", "notifications"]]

sql_inj_findings = []
for cdir in code_dirs:
    for py in cdir.rglob("*.py"):
        try:
            content = py.read_text(encoding="utf-8")
        except Exception:
            continue
        rel = str(py.relative_to(root))
        for idx, line in enumerate(content.splitlines(), 1):
            if "execute(" in line and ("f\"" in line or "f'" in line or ".format(" in line or " % " in line):
                sql_inj_findings.append(f"{rel}:{idx} -> {line.strip()}")

print(f"Total suspicious SQL execute calls: {len(sql_inj_findings)}")
for sf in sql_inj_findings:
    print(f"  {sf}")

with open("audit_probes/open_mutating_routes.json", "w") as f:
    json.dump(open_mutating_routes, f, indent=2)
with open("audit_probes/sql_injection_findings.json", "w") as f:
    json.dump(sql_inj_findings, f, indent=2)
