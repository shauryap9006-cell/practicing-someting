import json
import os

with open('data/gis/railway_stations_geojson.geojson', 'r', encoding='utf-8') as f:
    data = json.load(f)

code_map = {}
for feat in data['features']:
    props = feat.get('properties')
    geom = feat.get('geometry')
    if props and geom and props.get('code'):
        code_map[props['code']] = {
            'name': props.get('name'),
            'coordinates': geom['coordinates'],
            'zone': props.get('zone'),
            'state': props.get('state'),
        }

# Detailed sequence of physical stations along NDLS - DDU trunk
trunk_codes = [
    'NDLS', 'CSB', 'TKJ', 'ANVR', 'SBB', 'GZB', 'MIU', 'DER', 'BRKY', 'AJR', 'DKDE', 
    'WAIR', 'CHL', 'SKQ', 'KRJ', 'DAR', 'KAMP', 'SOM', 'KLA', 'MWUE', 'ALJN', 'DAQ', 
    'MXK', 'SNS', 'HRS', 'CMR', 'JLS', 'PORA', 'BRN', 'MTI', 'TDL', 'HNG', 'FZD', 
    'MNR', 'SKB', 'KAA', 'BDN', 'BBL', 'JGR', 'ETW', 'EKL', 'BNT', 'SHW', 'UCH', 
    'BHTN', 'SAMT', 'SHM', 'ULD', 'ACH', 'PHD', 'KNS', 'JK', 'AAP', 'RURA', 'MTO', 
    'RMW', 'BPU', 'PNKD', 'GOY', 'CNB', 'CPB', 'CHK', 'ROA', 'SSL', 'SJT', 'BKO', 
    'AUNG', 'KBN', 'FTP', 'RAMA', 'MWH', 'KKS', 'SNIE', 'KGA', 'SRO', 'ASCE', 'KUW', 
    'BRE', 'BDNP', 'MNJ', 'SYWN', 'BMU', 'MRE', 'SFG', 'PRYJ', 'NYN', 'KCN', 'BEP', 
    'MJA', 'UND', 'MNF', 'JIA', 'GAE', 'BEO', 'BDL', 'MZP', 'JHG', 'PRE', 'CAR', 
    'KYT', 'AHL', 'NPBR', 'GAQ', 'JEP', 'DDU'
]

# Intermediate curve vertices for high precision around major yards & river crossings
extra_curve_points = {
    'TKJ_ANVR': [
        [77.2510, 28.6230], # Pragati Maidan curve
        [77.2620, 28.6250], # Yamuna rail bridge
        [77.2882, 28.6322], # Mandawali
    ],
    'SBB_GZB': [
        [77.3950, 28.6630], # Hindon rail bridge curve
    ],
    'CNB_CPB': [
        [80.3650, 26.4650], # Ganga rail bridge approach
    ],
    'PRYJ_NYN': [
        [81.8450, 25.4200], # Yamuna railway bridge Prayagraj
    ]
}

trunk_coords = []
for i, code in enumerate(trunk_codes):
    if code in code_map:
        coords = code_map[code]['coordinates']
        trunk_coords.append(coords)
        
        # Insert extra curve points if present
        if i < len(trunk_codes) - 1:
            next_code = trunk_codes[i+1]
            pair_key = f"{code}_{next_code}"
            if pair_key in extra_curve_points:
                trunk_coords.extend(extra_curve_points[pair_key])

# Kanpur to Lucknow branch line
lko_branch_codes = ['CNB', 'CPB', 'MGW', 'ON', 'SIC', 'POF', 'AMS', 'MKG', 'LKO']
lko_coords = []
for code in lko_branch_codes:
    if code in code_map:
        lko_coords.append(code_map[code]['coordinates'])

out_data = {
    'trunk_NDLS_DDU': trunk_coords,
    'branch_CNB_LKO': lko_coords,
    'total_points': len(trunk_coords),
    'stations': {c: code_map[c] for c in trunk_codes if c in code_map}
}

os.makedirs('web/src/data', exist_ok=True)
with open('web/src/data/corridor_track_geometry.json', 'w', encoding='utf-8') as f:
    json.dump(out_data, f, indent=2)

print(f"Successfully generated web/src/data/corridor_track_geometry.json with {len(trunk_coords)} accurate track points!")
