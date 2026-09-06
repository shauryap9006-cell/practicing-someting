import json
import inspect
from pathlib import Path
from api.main import app
from fastapi.routing import APIRoute, _IncludedRouter

def get_all_routes(router_or_app, prefix=''):
    all_routes = []
    for r in router_or_app.routes:
        if isinstance(r, _IncludedRouter):
            p = prefix + (r.include_context.prefix if hasattr(r, 'include_context') and r.include_context else '')
            all_routes.extend(get_all_routes(r.original_router, p))
        elif isinstance(r, APIRoute):
            full_path = prefix + r.path
            is_async = inspect.iscoroutinefunction(r.endpoint)
            auth = any('auth' in str(d).lower() or 'user' in str(d).lower() or 'token' in str(d).lower() for d in r.dependencies)
            try:
                src_file = Path(inspect.getsourcefile(r.endpoint)).name
                lines, start_line = inspect.getsourcelines(r.endpoint)
                loc = f"{src_file}:{start_line}"
            except Exception:
                loc = "unknown"
            all_routes.append({
                'methods': sorted(list(r.methods)),
                'path': full_path,
                'auth': auth,
                'async': is_async,
                'handler': r.endpoint.__name__,
                'module': r.endpoint.__module__,
                'location': loc
            })
        elif hasattr(r, 'routes'):
            all_routes.extend(get_all_routes(r, prefix + getattr(r, 'path', '')))
    return all_routes

routes = get_all_routes(app)
print(f"Extracted {len(routes)} mounted routes")
with open('audit_probes/routes_mounted.json', 'w') as f:
    json.dump(routes, f, indent=2)
