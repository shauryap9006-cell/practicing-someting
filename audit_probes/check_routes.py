import os
import sys
import inspect
import importlib
import pkgutil
from pathlib import Path

ROOT = Path.cwd()
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "docs"))

from api.main import app
from fastapi.routing import APIRoute

print(f'Total mounted routes in app: {len(app.routes)}')
mounted_endpoints = set()
route_list = []
for r in app.routes:
    if isinstance(r, APIRoute):
        methods = ','.join(sorted(r.methods))
        is_async = inspect.iscoroutinefunction(r.endpoint)
        auth = any('auth' in str(d).lower() or 'user' in str(d).lower() or 'token' in str(d).lower() for d in r.dependencies)
        try:
            src_file = inspect.getsourcefile(r.endpoint)
            lines, start_line = inspect.getsourcelines(r.endpoint)
            src_loc = f'{Path(src_file).name}:{start_line}'
        except Exception:
            src_loc = 'unknown'
        route_list.append({
            'methods': methods,
            'path': r.path,
            'auth': auth,
            'async': is_async,
            'handler': r.endpoint.__name__,
            'location': src_loc,
            'module': r.endpoint.__module__
        })
        mounted_endpoints.add((r.endpoint.__module__, r.endpoint.__name__))

# Check all router modules in api/
import api
router_modules = []
for _, name, _ in pkgutil.iter_modules(api.__path__):
    if 'route' in name:
        router_modules.append(f'api.{name}')

unmounted = []
for mod_name in router_modules:
    try:
        mod = importlib.import_module(mod_name)
    except Exception as e:
        print(f'Error importing {mod_name}: {e}')
        continue
    if hasattr(mod, 'router'):
        router = getattr(mod, 'router')
        for r in router.routes:
            if isinstance(r, APIRoute):
                fn_name = r.endpoint.__name__
                if (r.endpoint.__module__, fn_name) not in mounted_endpoints:
                    unmounted.append({
                        'module': mod_name,
                        'handler': fn_name,
                        'methods': ','.join(sorted(r.methods)),
                        'path': r.path
                    })

print(f'Unmounted routes count: {len(unmounted)}')
for u in unmounted:
    print(f'  UNMOUNTED: {u}')

import json
with open('audit_probes/routes_mounted.json', 'w') as f:
    json.dump(route_list, f, indent=2)
with open('audit_probes/routes_unmounted.json', 'w') as f:
    json.dump(unmounted, f, indent=2)
print('Saved route inventories to audit_probes/')
