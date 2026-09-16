"""跑一次，找出哪一個 F-B0053 資料集含有「清境農場」的 3 小時預報。
用法：CWA_API_KEY=xxx python tools/find_cwa_dataset.py [地點名稱]
先用 F-C0032-001 驗證金鑰；再對 F-B0053-001~100 同時試 datastore 與 fileapi 兩種端點，列出地點名稱。
"""
import os, sys, requests

DATASTORE = "https://opendata.cwa.gov.tw/api/v1/rest/datastore/"
FILEAPI = "https://opendata.cwa.gov.tw/fileapi/v1/opendataapi/"
key = os.environ["CWA_API_KEY"]
name = sys.argv[1] if len(sys.argv) > 1 else "清境農場"
needles = [name, name[:2]]


def jget(url, **params):
    r = requests.get(url, params=params, timeout=60)
    try:
        return r.status_code, r.json()
    except ValueError:
        return r.status_code, {"raw": r.text[:120].replace("\n", " ")}


def walk_names(obj, out):
    """遞迴找所有 LocationName / locationName"""
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k in ("LocationName", "locationName") and isinstance(v, str):
                out.append(v)
            else:
                walk_names(v, out)
    elif isinstance(obj, list):
        for v in obj:
            walk_names(v, out)


code, js = jget(DATASTORE + "F-C0032-001", Authorization=key, format="JSON", locationName="南投縣")
print(f"key check: HTTP {code} success={js.get('success')}")
if js.get("success") not in (True, "true"):
    print("→ 金鑰無效", js); sys.exit(1)

shown_msg = 0
for n in range(1, 101):
    ds = f"F-B0053-{n:03d}"
    c1, j1 = jget(DATASTORE + ds, Authorization=key, format="JSON")
    ok1 = j1.get("success") in (True, "true")
    if not ok1 and shown_msg < 3:
        print(f"{ds} datastore HTTP {c1}: {str(j1)[:160]}"); shown_msg += 1
    c2, j2 = jget(FILEAPI + ds, Authorization=key, downloadType="WEB", format="JSON")
    ok2 = c2 == 200 and "raw" not in j2
    if not ok1 and not ok2:
        if n <= 3:
            print(f"{ds} fileapi HTTP {c2}: {str(j2)[:160]}")
        continue
    names = []
    walk_names(j1 if ok1 else j2, names)
    hits = [x for x in names if any(k in x for k in needles)]
    src = "datastore" if ok1 else "fileapi"
    print(f"{ds} [{src}] 地點數={len(names)} 例={names[:5]}" + (f"  ★ 符合={hits}" if hits else ""))
print("done")
