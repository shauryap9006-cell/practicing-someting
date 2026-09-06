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
from fastapi.routing import APIRoute, _IncludedRouter

def get_all_routes(router_or_app, prefix=''):
    all_routes = []
    for r in router_or_app.routes:
        if isinstance(r, _IncludedRouter):
            p = prefix + (r.include_context.prefix if hasattr(r, 'include_context') and r.include_context else '')
            all_routes.extend(get_all_routes(r.original_router, p))
        elif isinstance(r, APIRoute):
            all_routes.append({
                'full_path': prefix + r.path,
                'path': r.path,
                'methods': list(r.methods),
                'endpoint': r.endpoint,
                'name': r.endpoint.__name__,
                'module': r.endpoint.__module__,
                'async': inspect.iscoroutinefunction(r.endpoint),
                'dependencies': [str(d) for d in r.dependencies]
            })
        elif hasattr(r, 'routes'):
            all_routes.extend(get_all_routes(r, prefix + getattr(r, 'path', '')))
    return all_routes

mounted_routes = get_all_routes(app)
print(f'Total mounted routes: {len(mounted_routes)}')

mounted_endpoints = set((r['module'], r['name']) for r in mounted_routes)

import api
router_modules = []
for _, name, _ in pkgutil.iter_modules(api.__path__):
    if 'route' in name:
        router_modules.append(f'api.{name}')

unmounted = []
all_router_endpoints = []
for mod_name in sorted(router_modules):
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
                all_router_endpoints.append((mod_name, fn_name, r.methods, r.path))
                if (r.endpoint.__module__, fn_name) not in mounted_endpoints:
                    unmounted.append((mod_name, fn_name, r.methods, r.path))

print(f'Total endpoints declared across all router files: {len(all_router_endpoints)}')
print(f'Total unmounted endpoints: {len(unmounted)}')
for u in unmounted:
    print(f'  UNMOUNTED: {u}')
