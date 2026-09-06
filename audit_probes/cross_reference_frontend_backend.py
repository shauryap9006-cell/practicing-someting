import json
import re

backend_routes = json.load(open('audit_probes/routes_mounted.json'))
frontend_contracts = json.load(open('audit_probes/frontend_contracts.json'))

# Normalize paths for matching
# e.g. /v1/trains/{train_no}/journey and /v1/trains/${number}/journey
def pattern_for_route(p):
    # replace {param} or ${param} with regex [^/]+
    p = re.sub(r'\{[^}]+\}', '[^/]+', p)
    p = re.sub(r'\$\{[^}]+\}', '[^/]+', p)
    return '^' + p + '$'

matches = []
mismatches = []

backend_patterns = []
for br in backend_routes:
    pat = pattern_for_route(br['path'])
    backend_patterns.append((re.compile(pat), br))

for fc in frontend_contracts:
    f_url = fc['url']
    # Clean template expressions like ${encodeURIComponent(pnr)} -> ${pnr}
    cleaned_url = re.sub(r'\$\{[^}]+\}', '{param}', f_url)
    cleaned_pat = re.compile(pattern_for_route(cleaned_url))
    
    found = False
    matching_backend = []
    for reg, br in backend_patterns:
        # Check if f_url matches backend route pattern OR cleaned_pat matches backend path
        if reg.match(f_url) or cleaned_pat.match(br['path']):
            matching_backend.append(br)
            found = True
            
    if found:
        matches.append({'frontend': fc, 'backend': matching_backend})
    else:
        mismatches.append({'frontend': fc, 'reason': 'Route path not found in backend'})

print(f"Total frontend endpoints checked: {len(frontend_contracts)}")
print(f"Matches: {len(matches)}")
print(f"Mismatches: {len(mismatches)}")

for m in mismatches:
    print(f"MISMATCH: {m['frontend']['method']} {m['frontend']['url']} at {m['frontend']['calls'][0]}")

with open('audit_probes/frontend_backend_cross_check.json', 'w') as f:
    json.dump({'matches': matches, 'mismatches': mismatches}, f, indent=2)
