from dataclasses import dataclass


@dataclass
class Slot:
    start: str          # 'HH:MM'
    end: str
    weather: str | None
    pop: int | None
    low_cloud: int | None = None   # Open-Meteo 低雲量 %
    cloud: int | None = None       # Open-Meteo 總雲量 %
    level: str = "?"               # good / ok / bad / ?


LEVEL_LABEL = {"good": "適合", "ok": "勉強", "bad": "不適合", "?": "無資料"}
LEVEL_ICON = {"good": "✅", "ok": "⚠️", "bad": "❌", "?": "❔"}


def classify(weather: str | None, pop: int | None, sc: dict) -> str:
    if weather is None:
        return "?"
    w = weather
    if any(k in w for k in sc["bad_weather_keywords"]):
        return "bad"
    if pop is not None and pop > sc["ok_pop_max"]:
        return "bad"
    # 「多雲時晴」要先於「多雲」判斷
    if any(k in w for k in sc["good_weather_keywords"]) and (pop is None or pop <= sc["good_pop_max"]):
        return "good"
    if any(k in w for k in sc["good_weather_keywords"] + sc["ok_weather_keywords"]) and (pop is None or pop <= sc["ok_pop_max"]):
        return "ok"
    return "bad"


def summarize(slots: list[Slot]) -> str:
    """一句話結論，重點看前半夜（前 2 個時段）。"""
    if not slots or all(s.level == "?" for s in slots):
        return "氣象署預報取得失敗，請自行查看官網。"
    first_half = [s for s in slots[:2] if s.level != "?"]
    good = sum(1 for s in first_half if s.level == "good")
    ok = sum(1 for s in first_half if s.level == "ok")
    bad = sum(1 for s in first_half if s.level == "bad")
    if bad == 0 and good >= 1 and ok == 0:
        head = "今晚前半夜適合觀測"
    elif bad == 0:
        head = "今晚前半夜勉強可觀測，注意雲量變化"
    elif bad >= 1 and good + ok >= 1:
        head = "今晚天氣不穩，部分時段不適合"
    else:
        head = "今晚不適合觀測"
    goods = [f"{s.start}–{s.end}" for s in slots if s.level == "good"]
    tail = f"，整晚適合時段：{'、'.join(goods)}" if goods else ""
    return head + tail + "。"
