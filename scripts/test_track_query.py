import urllib.request
import urllib.parse
import json

# Overpass query to find the actual railway tracks along the corridor
query = """
[out:json][timeout:30];
(
  relation["railway"="rail"]["name"~"Delhi|Kanpur|Howrah|Northern|NCR",i](25.0,77.0,29.0,83.5);
  relation["route"="train"]["ref"~"12003|12004|12301|12302|22436|22435"](25.0,77.0,29.0,83.5);
);
out geom;
"""

url = "https://overpass-api.de/api/interpreter"
req = urllib.request.Request(
    url,
    data=query.encode("utf-8"),
    headers={"User-Agent": "RailTwinX-TrackFinder/1.0"}
)

try:
    with urllib.request.urlopen(req, timeout=25) as res:
        data = json.loads(res.read().decode("utf-8"))
        elements = data.get("elements", [])
        print("Fetched elements:", len(elements))
        for el in elements[:5]:
            print("Element:", el.get("type"), el.get("tags", {}).get("name"), el.get("tags", {}).get("ref"))
except Exception as e:
    print("Error:", e)
