"""看一個 fileapi 資料集裡指定地點的結構：因子、筆數、前兩筆時間與值。
用法：CWA_API_KEY=xxx python tools/inspect_cwa_dataset.py F-B0053-013 清境農場 [更多 資料集 地點 ...]
"""
import os, sys, json, requests

key = os.environ["CWA_API_KEY"]
args = sys.argv[1:]
pairs = list(zip(args[::2], args[1::2]))


def walk(obj, pred, out):
    if isinstance(obj, dict):
        if pred(obj):
            out.append(obj)
        for v in obj.values():
            walk(v, pred, out)
    elif isinstance(obj, list):
        for v in obj:
            walk(v, pred, out)


for ds, name in pairs:
    r = requests.get(f"https://opendata.cwa.gov.tw/fileapi/v1/opendataapi/{ds}",
                     params={"Authorization": key, "downloadType": "WEB", "format": "JSON"}, timeout=60)
    js = r.json()
    top = list(js.keys())
    root = js[top[0]]
    print(f"\n=== {ds} / {name}   top-level keys={top}  dataset keys={list(root.get('dataset', root).keys())[:8]}")
    ds_obj = root.get("dataset", root)
    print("  datasetInfo:", json.dumps(ds_obj.get("datasetInfo", {}), ensure_ascii=False)[:300])
    locs = []
    walk(js, lambda o: (o.get("locationName") or o.get("LocationName")) == name, locs)
    if not locs:
        print("  地點不存在"); continue
    loc = locs[0]
    print("  location keys:", list(loc.keys()))
    print("  lat/lon:", loc.get("lat") or loc.get("Latitude"), loc.get("lon") or loc.get("Longitude"))
    wes = loc.get("weatherElement") or loc.get("WeatherElement") or []
    for we in wes:
        en = we.get("elementName") or we.get("ElementName")
        times = we.get("time") or we.get("Time") or []
        print(f"  因子 {en}: 筆數={len(times)}")
        for t in times[:2]:
            print("     ", json.dumps(t, ensure_ascii=False)[:260])
