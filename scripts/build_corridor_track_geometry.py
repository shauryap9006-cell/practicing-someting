import urllib.request
import json
import os
import math

# Corridor segments bounding boxes
SECTIONS = [
    {"name": "NDLS_GZB", "bbox": "28.58,77.20,28.69,77.46"},
    {"name": "GZB_ALJN", "bbox": "27.85,77.40,28.70,78.15"},
    {"name": "ALJN_TDL", "bbox": "27.15,78.00,27.95,78.30"},
    {"name": "TDL_ETW", "bbox": "26.70,78.20,27.25,79.08"},
    {"name": "ETW_CNB", "bbox": "26.40,79.00,26.85,80.40"},
    {"name": "CNB_PRYJ", "bbox": "25.40,80.30,26.50,81.90"},
    {"name": "PRYJ_DDU", "bbox": "25.10,81.80,25.50,83.18"},
    {"name": "CNB_LKO", "bbox": "26.40,80.30,26.90,80.98"},
]

def fetch_section_tracks(bbox):
    query = f"""
    [out:json][timeout:25];
    way["railway"="rail"]["usage"="main"]({bbox});
    out geom;
    """
    req = urllib.request.Request(
        "https://overpass-api.de/api/interpreter",
        data=query.encode("utf-8"),
        headers={"User-Agent": "RailTwinX-TrackBuilder/1.0"}
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as res:
            data = json.loads(res.read().decode("utf-8"))
            return data.get("elements", [])
    except Exception as e:
        print(f"Error fetching bbox {bbox}:", e)
        return []

print("Fetching tracks for corridor...")
all_ways = []
for sec in SECTIONS:
    print(f"Fetching {sec['name']}...")
    ways = fetch_section_tracks(sec["bbox"])
    print(f"  Got {len(ways)} track segments")
    all_ways.extend(ways)

print(f"Total track segments: {len(all_ways)}")
