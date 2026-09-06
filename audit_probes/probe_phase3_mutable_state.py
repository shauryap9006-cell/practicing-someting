import ast
from pathlib import Path

ROOT = Path.cwd()
code_dirs = [ROOT / d for d in ["api", "engine", "notifications"]]

findings = []

for cdir in code_dirs:
    for py in cdir.rglob("*.py"):
        try:
            content = py.read_text(encoding="utf-8")
            tree = ast.parse(content)
        except Exception:
            continue
            
        module_assigns = {}
        for node in tree.body:
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        val = node.value
                        if isinstance(val, (ast.Dict, ast.List, ast.Set)):
                            module_assigns[target.id] = (node.lineno, type(val).__name__)
                            
        # Now check if any function/method mutates these module-level variables
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                for subnode in ast.walk(node):
                    # Check subscript assign: var[x] = y
                    if isinstance(subnode, ast.Assign):
                        for target in subnode.targets:
                            if isinstance(target, ast.Subscript) and isinstance(target.value, ast.Name):
                                var_name = target.value.id
                                if var_name in module_assigns:
                                    findings.append({
                                        "file": str(py.relative_to(ROOT)),
                                        "line": subnode.lineno,
                                        "var": var_name,
                                        "def_line": module_assigns[var_name][0],
                                        "type": "subscript_assign",
                                        "scope_fn": node.name
                                    })
                    # Check method calls: var.append, var.pop, var.add, var.update
                    elif isinstance(subnode, ast.Call):
                        if isinstance(subnode.func, ast.Attribute) and isinstance(subnode.func.value, ast.Name):
                            var_name = subnode.func.value.id
                            method = subnode.func.attr
                            if var_name in module_assigns and method in ["append", "pop", "add", "update", "clear", "remove"]:
                                findings.append({
                                    "file": str(py.relative_to(ROOT)),
                                    "line": subnode.lineno,
                                    "var": var_name,
                                    "def_line": module_assigns[var_name][0],
                                    "type": f"method_{method}",
                                    "scope_fn": node.name
                                })

print(f"Total global mutable state mutation sites found: {len(findings)}")
for f in findings:
    print(f"  {f['file']}:{f['line']} mutates '{f['var']}' (defined line {f['def_line']}) via {f['type']} inside {f['scope_fn']}()")
