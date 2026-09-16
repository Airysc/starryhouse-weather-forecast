"""中央氣象署開放資料：育樂區 3 小時預報 + 自動氣象站觀測"""
import math
from datetime import datetime
import requests

BASE = "https://opendata.cwa.gov.tw/api/v1/rest/datastore/"


def _get(dataset: str, key: str, **params) -> dict:
    params["Authorization"] = key
    params.setdefault("format", "JSON")
    r = requests.get(BASE + dataset, params=params, timeout=30)
    r.raise_for_status()
    js = r.json()
    if js.get("success") not in (True, "true"):
        raise RuntimeError(f"CWA API error: {js}")
    return js["records"]


def _num(v):
    try:
        return int(float(v))
    except (TypeError, ValueError):
        return None


def forecast_3h(cfg: dict, key: str) -> list[dict]:
    """回傳 [{start, end, weather, pop, temp, rh}]，依時間排序。"""
    c = cfg["cwa"]
    rec = _get(c["forecast_dataset"], key, LocationName=c["forecast_location"])
    locs = rec.get("Locations") or rec.get("locations") or []
    loc = None
    for L in locs:
        for x in L.get("Location") or L.get("location") or []:
            if (x.get("LocationName") or x.get("locationName")) == c["forecast_location"]:
                loc = x
    if loc is None:
        raise RuntimeError(f"location {c['forecast_location']} not in dataset {c['forecast_dataset']}")

    slots: dict[str, dict] = {}
    for we in loc.get("WeatherElement") or loc.get("weatherElement") or []:
        for t in we.get("Time") or we.get("time") or []:
            st = t.get("StartTime") or t.get("startTime")
            en = t.get("EndTime") or t.get("endTime")
            if not st or not en:
                continue
            slot = slots.setdefault(st, {"start": st, "end": en})
            for ev in t.get("ElementValue") or t.get("elementValue") or []:
                slot.update(ev)
    out = []
    for st in sorted(slots):
        s = slots[st]
        out.append({
            "start": s["start"], "end": s["end"],
            "weather": s.get("Weather"),
            "pop": _num(s.get("ProbabilityOfPrecipitation")),
            "temp": _num(s.get("Temperature")),
            "rh": _num(s.get("RelativeHumidity")),
            "desc": s.get("WeatherDescription"),
        })
    return out


def _dist_km(lat1, lon1, lat2, lon2):
    p = math.pi / 180
    a = 0.5 - math.cos((lat2 - lat1) * p) / 2 + math.cos(lat1 * p) * math.cos(lat2 * p) * (1 - math.cos((lon2 - lon1) * p)) / 2
    return 12742 * math.asin(math.sqrt(a))


def observation(cfg: dict, key: str) -> dict:
    """最近（或指定）自動氣象站的即時觀測。"""
    c, site = cfg["cwa"], cfg["location"]
    rec = _get(c["obs_dataset"], key)
    best, best_d = None, 1e9
    for stn in rec.get("Station", []):
        name = stn.get("StationName")
        if c.get("obs_station_name"):
            if name != c["obs_station_name"]:
                continue
            best, best_d = stn, 0
            break
        lat = lon = None
        for co in stn.get("GeoInfo", {}).get("Coordinates", []):
            if co.get("CoordinateName") == "WGS84":
                lat, lon = float(co["StationLatitude"]), float(co["StationLongitude"])
        if lat is None:
            continue
        d = _dist_km(site["latitude"], site["longitude"], lat, lon)
        if d < best_d:
            best, best_d = stn, d
    if best is None:
        raise RuntimeError("no station found")
    we = best.get("WeatherElement", {})
    return {
        "station": best.get("StationName"),
        "dist_km": round(best_d, 1),
        "time": best.get("ObsTime", {}).get("DateTime"),
        "temp": we.get("AirTemperature"),
        "rh": we.get("RelativeHumidity"),
        "wind": we.get("WindSpeed"),
        "weather": we.get("Weather"),
        "rain_now": (we.get("Now") or {}).get("Precipitation"),
    }
