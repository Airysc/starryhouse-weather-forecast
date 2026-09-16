"""列出某資料集某地點某因子的全部時間點與值。
用法：CWA_API_KEY=xxx python tools/dump_element.py F-B0053-017 清境農場 風速
"""
import os, sys, json, requests
key = os.environ["CWA_API_KEY"]
ds, name, elem = sys.argv[1:4]
js = requests.get(f"https://opendata.cwa.gov.tw/fileapi/v1/opendataapi/{ds}",
                  params={"Authorization": key, "downloadType": "WEB", "format": "JSON"}, timeout=60).json()

def find(o):
    if isinstance(o, dict):
        if o.get("LocationName") == name: return o
        for v in o.values():
            r = find(v)
            if r: return r
    elif isinstance(o, list):
        for v in o:
            r = find(v)
            if r: return r
loc = find(js)
for we in loc.get("WeatherElement", []):
    if we.get("ElementName") == elem:
        for t in we.get("Time", []):
            print(json.dumps(t, ensure_ascii=False))
