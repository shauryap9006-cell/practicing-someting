import ast
from pathlib import Path

api_dir = Path("api")
blocking_calls = ["execute", "fetchall", "fetchone", "transaction", "read_sql", "predict", "sleep", "open", "read_text", "write_text"]

violations = []

for py_file in api_dir.glob("*.py"):
    if not py_file.name.endswith(".py"):
        continue
    try:
        tree = ast.parse(py_file.read_text(encoding="utf-8"))
    except Exception:
        continue
        
    for node in ast.walk(tree):
        if isinstance(node, ast.AsyncFunctionDef):
            # Check if this is a route handler (has decorators like @router.get, @app.get, etc.)
            is_route = any(
                isinstance(d, ast.Call) and getattr(d.func, "attr", "") in ["get", "post", "put", "delete", "patch"]
                for d in node.decorator_list
            )
            if not is_route:
                continue
                
            # Inspect body for blocking calls
            found_blocking = []
            for subnode in ast.walk(node):
                if isinstance(subnode, ast.Call):
                    func_name = ""
                    if isinstance(subnode.func, ast.Attribute):
                        func_name = subnode.func.attr
                    elif isinstance(subnode.func, ast.Name):
                        func_name = subnode.func.id
                        
                    if func_name in blocking_calls:
                        found_blocking.append((func_name, getattr(subnode, "lineno", node.lineno)))
                        
            if found_blocking:
                violations.append({
                    "file": str(py_file),
                    "handler": node.name,
                    "line": node.lineno,
                    "blocking_calls": found_blocking
                })

print(f"Total async def route handlers with blocking calls: {len(violations)}")
for v in violations:
    calls = ", ".join([f"{c[0]} (line {c[1]})" for c in v['blocking_calls'][:3]])
    print(f"  {Path(v['file']).name}:{v['line']} async def {v['handler']} -> blocking calls: {calls}")
