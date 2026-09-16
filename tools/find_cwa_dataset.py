"""跑一次，找出哪一個 F-B0053 資料集含有「清境農場」的 3 小時預報。
用法：CWA_API_KEY=xxx python tools/find_cwa_dataset.py [地點名稱]
"""
import os, sys, requests

key = os.environ["CWA_API_KEY"]
name = sys.argv[1] if len(sys.argv) > 1 else "清境農場"
for n in range(1, 90):
    ds = f"F-B0053-{n:03d}"
    try:
        r = requests.get(f"https://opendata.cwa.gov.tw/api/v1/rest/datastore/{ds}",
                         params={"Authorization": key, "LocationName": name, "format": "JSON"}, timeout=30)
        js = r.json()
    except Exception as e:
        print(ds, "error", e); continue
    if js.get("success") not in (True, "true"):
        continue
    locs = js.get("records", {}).get("Locations") or []
    for L in locs:
        for x in L.get("Location") or []:
            if x.get("LocationName") == name:
                wes = x.get("WeatherElement") or []
                times = (wes[0].get("Time") or []) if wes else []
                span = ""
                if len(times) > 1:
                    span = f"{times[0].get('StartTime','')} ~ {times[0].get('EndTime','')}"
                names = [w.get("ElementName") for w in wes]
                print(f"{ds}: {L.get('LocationsName')} / {name}  筆數={len(times)}  第一筆={span}  因子={names}")
print("done — 選「筆數約 24、時距 3 小時、因子含 Weather 與 ProbabilityOfPrecipitation」的那個填入 config.yaml")
