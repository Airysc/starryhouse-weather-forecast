"""列出觀測資料集裡離觀星園最近的測站與其資料時間，看更新頻率。
用法：CWA_API_KEY=xxx python tools/nearby_stations.py O-A0001-001 O-A0003-001 O-A0002-001
"""
import os, sys, math, requests
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.config import load_config
key = os.environ["CWA_API_KEY"]
cfg = load_config(); site = cfg["location"]

def dist(lat, lon):
    p = math.pi / 180
    a = 0.5 - math.cos((lat - site["latitude"]) * p) / 2 + math.cos(site["latitude"] * p) * math.cos(lat * p) * (1 - math.cos((lon - site["longitude"]) * p)) / 2
    return 12742 * math.asin(math.sqrt(a))

for ds in sys.argv[1:] or ["O-A0001-001", "O-A0003-001", "O-A0002-001"]:
    r = requests.get(f"https://opendata.cwa.gov.tw/api/v1/rest/datastore/{ds}", params={"Authorization": key, "format": "JSON"}, timeout=60)
    js = r.json()
    print(f"\n=== {ds}  HTTP {r.status_code} success={js.get('success')}")
    rows = []
    for stn in js.get("records", {}).get("Station", []):
        lat = lon = None
        for co in stn.get("GeoInfo", {}).get("Coordinates", []):
            if co.get("CoordinateName") == "WGS84":
                lat, lon = float(co["StationLatitude"]), float(co["StationLongitude"])
        if lat is None: continue
        rows.append((dist(lat, lon), stn.get("StationName"), stn.get("StationId"), stn.get("ObsTime", {}).get("DateTime"), stn.get("GeoInfo", {}).get("StationAltitude"), list((stn.get("WeatherElement") or {}).keys())[:6]))
    for d, n, i, t, alt, keys in sorted(rows)[:8]:
        print(f"  {d:5.1f} km  {n:6s} {i}  {t}  海拔 {alt}  {keys}")
