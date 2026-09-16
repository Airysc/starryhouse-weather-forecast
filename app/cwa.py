"""中央氣象署開放資料：育樂區 3 小時預報 + 自動氣象站觀測"""
import math
from datetime import datetime
import requests

BASE = "https://opendata.cwa.gov.tw/api/v1/rest/datastore/"
FILEAPI = "https://opendata.cwa.gov.tw/fileapi/v1/opendataapi/"


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


def _find_location(obj, name: str):
    """fileapi 的 JSON 巢狀層級不固定，遞迴找 LocationName 相符的節點"""
    if isinstance(obj, dict):
        if (obj.get("LocationName") or obj.get("locationName")) == name:
            return obj
        for v in obj.values():
            r = _find_location(v, name)
            if r is not None:
                return r
    elif isinstance(obj, list):
        for v in obj:
            r = _find_location(v, name)
            if r is not None:
                return r
    return None


def forecast(cfg: dict, key: str) -> dict:
    """回傳 {"slots": [{start, end, weather, wcode, pop, temp, rh, wind, beaufort, desc}], "hourly": [{time, temp, rh}]}，皆依時間排序。

    F-B0053 系列（育樂預報）只提供檔案下載（fileapi），不在 datastore。
    3 小時因子（天氣現象、降雨機率、綜合描述）有 StartTime/EndTime；
    逐時因子（溫度、相對濕度）只有 DataTime，取時段起點那一筆。
    """
    c = cfg["cwa"]
    r = requests.get(FILEAPI + c["forecast_dataset"],
                     params={"Authorization": key, "downloadType": "WEB", "format": "JSON"}, timeout=60)
    r.raise_for_status()
    loc = _find_location(r.json(), c["forecast_location"])
    if loc is None:
        raise RuntimeError(f"location {c['forecast_location']} not in dataset {c['forecast_dataset']}")

    slots: dict[str, dict] = {}
    hourly: dict[str, dict] = {}
    for we in loc.get("WeatherElement") or loc.get("weatherElement") or []:
        for t in we.get("Time") or we.get("time") or []:
            ev = t.get("ElementValue") or t.get("elementValue") or {}
            if isinstance(ev, list):
                ev = {k: v for d in ev for k, v in d.items()}
            st = t.get("StartTime") or t.get("startTime")
            en = t.get("EndTime") or t.get("endTime")
            dt = t.get("DataTime") or t.get("dataTime")
            if st and en:
                slots.setdefault(st, {"start": st, "end": en}).update(ev)
            elif dt:
                hourly.setdefault(dt, {}).update(ev)
    def wind_for(st, en):
        """風速／風級的 DataTime 不一定對齊時段起點，取落在時段內的那筆，否則取起點前最近一筆"""
        inside = [t for t in sorted(hourly) if st <= t < en and "BeaufortScale" in hourly[t]]
        before = [t for t in sorted(hourly) if t <= st and "BeaufortScale" in hourly[t]]
        t = inside[0] if inside else (before[-1] if before else None)
        return hourly[t] if t else {}

    out = []
    for st in sorted(slots):
        s = {**wind_for(st, slots[st]["end"]), **hourly.get(st, {}), **slots[st]}
        out.append({
            "start": s["start"], "end": s["end"],
            "weather": s.get("Weather"),
            "wcode": s.get("WeatherCode"),
            "pop": _num(s.get("ProbabilityOfPrecipitation")),
            "temp": _num(s.get("Temperature")),
            "rh": _num(s.get("RelativeHumidity")),
            "wind": _num(s.get("WindSpeed")),
            "beaufort": _num(s.get("BeaufortScale")),
            "desc": s.get("WeatherDescription"),
        })
    hours = [{"time": t, "temp": _num(v.get("Temperature")), "rh": _num(v.get("RelativeHumidity"))}
             for t, v in sorted(hourly.items()) if "Temperature" in v or "RelativeHumidity" in v]
    return {"slots": out, "hourly": hours}


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
        "station_id": best.get("StationId"),
        "dist_km": round(best_d, 1),
        "time": best.get("ObsTime", {}).get("DateTime"),
        "temp": we.get("AirTemperature"),
        "rh": we.get("RelativeHumidity"),
        "wind": we.get("WindSpeed"),
        "weather": we.get("Weather"),
        "rain_now": (we.get("Now") or {}).get("Precipitation"),
    }
