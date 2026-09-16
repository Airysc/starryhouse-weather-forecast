"""7Timer! ASTRO：每 3 小時的視寧度／透明度（免金鑰）"""
from datetime import datetime, timedelta, timezone
import requests


def astro(cfg: dict) -> list[dict]:
    """回傳 [{time(當地 ISO), hours=3, cloud(1-9), seeing(1-8), transparency(1-8)}]"""
    s = cfg["location"]
    r = requests.get("https://www.7timer.info/bin/astro.php",
                     params={"lon": s["longitude"], "lat": s["latitude"], "ac": 0, "unit": "metric", "output": "json", "tzshift": 0},
                     timeout=30)
    r.raise_for_status()
    js = r.json()
    init = datetime.strptime(js["init"], "%Y%m%d%H").replace(tzinfo=timezone.utc)
    from zoneinfo import ZoneInfo
    tz = ZoneInfo(s["timezone"])
    out = []
    for d in js.get("dataseries", []):
        t = (init + timedelta(hours=int(d["timepoint"]))).astimezone(tz)
        out.append({"time": t.isoformat(timespec="minutes"), "hours": 3,
                    "cloud": d.get("cloudcover"), "seeing": d.get("seeing"), "transparency": d.get("transparency")})
    return out
