import urllib.request
import urllib.parse
import json

query = """
[out:json][timeout:60];
(
  relation["route"="train"]["ref"="12003"](25.0,77.0,29.0,83.5);
  relation["route"="train"]["ref"="12301"](25.0,77.0,29.0,83.5);
  relation["route"="train"]["ref"="22436"](25.0,77.0,29.0,83.5);
  relation["route"="train"]["name"~"Shatabdi|Rajdhani|Vande",i](25.0,77.0,29.0,83.5);
);
out body;
>;
out skel qt;
"""

url = "https://overpass-api.de/api/interpreter"
req = urllib.request.Request(
    url,
    data=query.encode("utf-8"),
    headers={"User-Agent": "RailTwinX-TrackGeometryExtractor/1.0"}
)

try:
    with urllib.request.urlopen(req, timeout=45) as res:
        data = json.loads(res.read().decode("utf-8"))
        elements = data.get("elements", [])
        relations = [e for e in elements if e.get("type") == "relation"]
        ways = [e for e in elements if e.get("type") == "way"]
        nodes = {e["id"]: (e["lon"], e["lat"]) for e in elements if e.get("type") == "node"}
        print(f"Relations: {len(relations)}, Ways: {len(ways)}, Nodes: {len(nodes)}")
        for r in relations:
            print("Found route:", r.get("tags", {}).get("name", "Unknown").encode("ascii", "ignore").decode())
except Exception as e:
    print("Error:", e)
