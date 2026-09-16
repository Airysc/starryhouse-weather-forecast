"""每 10 分鐘執行：收集資料 → 產生 build/ → 由 workflow 部署到 GitHub Pages

  python -m app.main            # 產生 build/
  python -m app.main --print    # 同時把 latest.json 印出來
"""
import argparse
import json
import sys
from datetime import datetime, timedelta

import requests

from . import cwa, openmeteo, imagery, youtube, site, seventimer, meteoblue
from .config import load_config, secret
from .scoring import Slot, classify, summarize
from .sun import now_local, sun_times


def log(*a):
    print(*a, file=sys.stderr, flush=True)


def build_slots(cfg: dict, fc: list[dict], clouds: dict | None, now: datetime) -> list[Slot]:
    w, sc = cfg["window"], cfg["scoring"]
    # 觀測窗口：今天 18:00 起；若已過午夜且還在窗口內，起點回推到昨天
    start = now.replace(hour=w["start_hour"], minute=0, second=0, microsecond=0)
    if now.hour < w["end_hour"]:
        start -= timedelta(days=1)
    end = (start + timedelta(days=1)).replace(hour=w["end_hour"])
    slots = []
    for f in fc:
        try:
            t0 = datetime.fromisoformat(f["start"].replace(" ", "T"))
            t1 = datetime.fromisoformat(f["end"].replace(" ", "T"))
        except ValueError:
            continue
        if t0.tzinfo is None:
            t0, t1 = t0.replace(tzinfo=now.tzinfo), t1.replace(tzinfo=now.tzinfo)
        if t0 < start or t0 >= end:
            continue
        s = Slot(start=t0.strftime("%H:%M"), end=t1.strftime("%H:%M"), weather=f["weather"], pop=f["pop"])
        s.level = classify(s.weather, s.pop, sc)
        if clouds:
            om = openmeteo.avg_for_slot(clouds, t0.isoformat())
            if om:
                s.low_cloud, s.cloud = om["low"], om["cloud"]
        slots.append(s)
    return slots


def _parse(ts: str, tz) -> datetime | None:
    try:
        t = datetime.fromisoformat(ts.replace(" ", "T"))
    except (ValueError, AttributeError):
        return None
    return t.replace(tzinfo=tz) if t.tzinfo is None else t


def build_forecast24(cfg: dict, fc: list[dict], hourly: list[dict], now: datetime) -> dict:
    """網頁用：從現在這個整點起 24 小時的逐時濕度，以及涵蓋這段時間的 3 小時時段（天氣、降雨、風級、判斷）。"""
    sc = cfg["scoring"]
    start = now.replace(minute=0, second=0, microsecond=0)
    end = start + timedelta(hours=24)
    hours = []
    for h in hourly:
        t = _parse(h["time"], now.tzinfo)
        if t and start <= t < end:
            hours.append({"time": t.isoformat(timespec="minutes"), "temp": h["temp"], "rh": h["rh"]})
    slots = []
    for f in fc:
        t0, t1 = _parse(f["start"], now.tzinfo), _parse(f["end"], now.tzinfo)
        if not t0 or not t1 or t1 <= start or t0 >= end:
            continue
        slots.append({"start": t0.isoformat(timespec="minutes"), "end": t1.isoformat(timespec="minutes"),
                      "weather": f["weather"], "wcode": f.get("wcode"), "pop": f["pop"],
                      "wind": f.get("wind"), "beaufort": f.get("beaufort"),
                      "level": classify(f["weather"], f["pop"], sc)})
    return {"start": start.isoformat(timespec="minutes"), "hours": hours, "slots": slots}


def previous_state(cfg: dict) -> dict:
    """讀線上上一版 latest.json，取回直播 ID 快取。"""
    try:
        r = requests.get(cfg["site"]["url"].rstrip("/") + "/data/latest.json", timeout=15)
        if r.ok:
            return {s["handle"]: {"last_id": s.get("video_id"), "last_title": s.get("title"), "channel_id": s.get("channel_id")}
                    for s in r.json().get("streams", []) if s.get("handle")}
    except Exception as e:
        log("previous latest.json unavailable:", e)
    return {}


def collect(cfg: dict) -> dict:
    now = now_local(cfg)
    sun = sun_times(cfg, now.date())
    is_daylight = sun["sunrise"] < now < sun["sunset"]
    cwa_key, yt_key = secret("CWA_API_KEY"), secret("YOUTUBE_API_KEY")

    fc, hourly, clouds, obs = [], [], None, None
    try:
        if cwa_key:
            f = cwa.forecast(cfg, cwa_key)
            fc, hourly = f["slots"], f["hourly"]
    except Exception as e:
        log("CWA forecast failed:", e)
    try:
        clouds = openmeteo.hourly_clouds(cfg)
    except Exception as e:
        log("Open-Meteo failed:", e)
    try:
        obs = cwa.observation(cfg, cwa_key) if cwa_key else None
    except Exception as e:
        log("CWA obs failed:", e)
    slots = build_slots(cfg, fc, clouds, now)
    forecast24 = build_forecast24(cfg, fc, hourly, now)

    # 雲量與視寧度格狀表：Open-Meteo 逐時 48 小時 + 7Timer 每 3 小時
    start = now.replace(minute=0, second=0, microsecond=0)
    cloud_rows = []
    for k in range(48):
        t = start + timedelta(hours=k)
        v = (clouds or {}).get(t.strftime("%Y-%m-%dT%H:00"))
        cloud_rows.append({"time": t.isoformat(timespec="minutes"), **({"low": v["low"], "mid": v["mid"], "high": v["high"], "pop": v["pop"]} if v else {"low": None, "mid": None, "high": None, "pop": None})})
    astro7 = []
    try:
        astro7 = [a for a in seventimer.astro(cfg) if start - timedelta(hours=3) < datetime.fromisoformat(a["time"]) < start + timedelta(hours=48)]
    except Exception as e:
        log("7Timer failed:", e)

    images = {}
    try:
        images = imagery.collect(cfg, now, is_daylight)
    except Exception as e:
        log("imagery failed:", e)

    mb_img = None
    try:
        mb_img = meteoblue.screenshot(cfg)
        log("meteoblue screenshot:", "ok" if mb_img else "none")
    except Exception as e:
        log("meteoblue screenshot failed:", e)

    prev = previous_state(cfg)
    streams = []
    for sc in cfg.get("streams", []):
        cache = prev.get(sc["handle"], {})
        entry = {"name": sc["name"], "handle": sc["handle"], "video": None}
        try:
            entry["video"] = youtube.resolve(sc, yt_key, cache)
        except Exception as e:
            log(f"stream {sc['handle']} failed:", e)
        entry["channel_id"] = cache.get("channel_id")
        streams.append(entry)

    return {"cfg": cfg, "now": now, "sun": sun, "slots": slots, "summary": summarize(slots),
            "forecast24": forecast24, "clouds": cloud_rows, "astro7": astro7,
            "obs": obs, "images": images, "streams": streams, "meteoblue_img": mb_img}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--print", action="store_true")
    ap.add_argument("--config")
    a = ap.parse_args()
    cfg = load_config(a.config)
    data = site.write(collect(cfg))
    log("built:", data["generated_at"], "|", data["summary"])
    if a.print:
        print(json.dumps(data, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
