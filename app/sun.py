from datetime import datetime, date
from zoneinfo import ZoneInfo
from astral import LocationInfo
from astral.sun import sun


def sun_times(cfg: dict, day: date) -> dict:
    s = cfg["location"]
    loc = LocationInfo(s["name"], "TW", s["timezone"], s["latitude"], s["longitude"])
    return sun(loc.observer, date=day, tzinfo=ZoneInfo(s["timezone"]))


def now_local(cfg: dict) -> datetime:
    return datetime.now(ZoneInfo(cfg["location"]["timezone"]))
