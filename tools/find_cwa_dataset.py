"""跑一次，找出哪一個 F-B0053 資料集含有「清境農場」的 3 小時預報。
用法：CWA_API_KEY=xxx python tools/find_cwa_dataset.py [地點名稱]
先用 F-C0032-001 驗證金鑰，再逐一列出每個資料集的地點名稱（不要求完全相符，方便找出實際名稱）。
"""
import os, sys, requests

BASE = "https://opendata.cwa.gov.tw/api/v1/rest/datastore/"
key = os.environ["CWA_API_KEY"]
name = sys.argv[1] if len(sys.argv) > 1 else "清境農場"
needles = [name] + [name[:2]]  # 例如「清境農場」與「清境」


def get(ds, **params):
    params.update(Authorization=key, format="JSON")
    r = requests.get(BASE + ds, params=params, timeout=30)
    try:
        return r.status_code, r.json()
    except ValueError:
        return r.status_code, {"raw": r.text[:200]}


# 0. 驗證金鑰
code, js = get("F-C0032-001", locationName="南投縣")
print(f"key check (F-C0032-001): HTTP {code}, success={js.get('success')}, msg={js.get('message') or js.get('result', {}).get('message') or js.get('raw', '')}")
if js.get("success") not in (True, "true"):
    print("→ 金鑰無效或未生效，請確認 Secret 值（授權碼）")
    sys.exit(1)

# 1. 掃描 F-B0053 系列
for n in range(1, 100):
    ds = f"F-B0053-{n:03d}"
    code, js = get(ds)
    if js.get("success") not in (True, "true"):
        continue
    locs = js.get("records", {}).get("Locations") or []
    for L in locs:
        items = L.get("Location") or []
        names = [x.get("LocationName") for x in items]
        hits = [x for x in items if any(k in (x.get("LocationName") or "") for k in needles)]
        line = f"{ds}: {L.get('LocationsName')}  地點數={len(names)}"
        if hits:
            x = hits[0]
            wes = x.get("WeatherElement") or []
            times = (wes[0].get("Time") or []) if wes else []
            span = f"{times[0].get('StartTime', '')} ~ {times[0].get('EndTime', '')}" if times else ""
            line += f"  ★ 符合={[h.get('LocationName') for h in hits]}  筆數={len(times)}  第一筆={span}  因子={[w.get('ElementName') for w in wes]}"
        else:
            line += f"  地點例={names[:6]}"
        print(line)
print("done — 選「★ 且筆數約 24、時距 3 小時、因子含 Weather 與 ProbabilityOfPrecipitation」的那個填入 config.yaml（forecast_location 也要改成實際名稱）")
