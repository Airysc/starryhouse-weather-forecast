"""印出某觀測資料集裡某測站的完整 WeatherElement。用法：python tools/dump_station.py O-A0003-001 屯原"""
import os, sys, json, requests
key = os.environ["CWA_API_KEY"]; ds, name = sys.argv[1:3]
js = requests.get(f"https://opendata.cwa.gov.tw/api/v1/rest/datastore/{ds}", params={"Authorization": key, "format": "JSON", "StationName": name}, timeout=60).json()
for stn in js.get("records", {}).get("Station", []):
    print(json.dumps({k: stn[k] for k in ("StationName", "StationId", "ObsTime", "WeatherElement") if k in stn}, ensure_ascii=False, indent=1))
