"""Open-Meteo 逐時雲量（輔助欄位）"""
import requests


def hourly_clouds(cfg: dict) -> dict[str, dict]:
    """回傳 {'YYYY-MM-DDTHH:00': {cloud, low, mid, high, pop}}"""
    s = cfg["location"]
    r = requests.get("https://api.open-meteo.com/v1/forecast", params={
        "latitude": s["latitude"], "longitude": s["longitude"], "elevation": s["elevation_m"],
        "hourly": "cloud_cover,cloud_cover_low,cloud_cover_mid,cloud_cover_high,precipitation_probability",
        "timezone": s["timezone"], "forecast_days": 3,
    }, timeout=30)
    r.raise_for_status()
    h = r.json()["hourly"]
    out = {}
    for i, t in enumerate(h["time"]):
        out[t] = {
            "cloud": h["cloud_cover"][i], "low": h["cloud_cover_low"][i],
            "mid": h["cloud_cover_mid"][i], "high": h["cloud_cover_high"][i],
            "pop": h["precipitation_probability"][i],
        }
    return out


def avg_for_slot(clouds: dict, start_iso: str, hours: int = 3) -> dict | None:
    """把 3 小時預報時段對應到 Open-Meteo 逐時值取平均。start_iso 形如 '2026-09-16T18:00:00+08:00'"""
    from datetime import datetime, timedelta
    try:
        t0 = datetime.fromisoformat(start_iso.replace(" ", "T"))
    except ValueError:
        return None
    vals = []
    for k in range(hours):
        key = (t0 + timedelta(hours=k)).strftime("%Y-%m-%dT%H:00")
        if key in clouds:
            vals.append(clouds[key])
    if not vals:
        return None
    return {f: round(sum(v[f] for v in vals if v[f] is not None) / len(vals)) for f in ("cloud", "low", "mid", "high")}
