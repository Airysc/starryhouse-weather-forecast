"""氣象署雷達回波 / 衛星雲圖：抓最新一張 + 前 N 小時 GIF"""
import io
from datetime import datetime, timedelta, timezone
import requests
from PIL import Image

UA = {"User-Agent": "Mozilla/5.0 (starryhouse-weather-forecast)"}


def _fmt(url: str, t_local: datetime) -> str:
    t_utc = t_local.astimezone(timezone.utc)
    return url.format(
        ts_local_compact=t_local.strftime("%Y%m%d%H%M"),
        ts_local_dash=t_local.strftime("%Y-%m-%d-%H-%M"),
        ts_utc_compact=t_utc.strftime("%Y%m%d%H%M"),
        ts_utc_dash=t_utc.strftime("%Y-%m-%d-%H-%M"),
    )


def _floor(t: datetime, step_min: int) -> datetime:
    return t.replace(minute=(t.minute // step_min) * step_min, second=0, microsecond=0)


def fetch_frames(product: dict, now_local: datetime, hours_back: int, step_min: int) -> list[tuple[datetime, bytes]]:
    frames = []
    t = _floor(now_local, step_min)
    t_start = t - timedelta(hours=hours_back)
    # 從最舊往最新抓；最新的幾幀可能還沒發布，容許 404
    cur = t_start
    while cur <= t:
        url = _fmt(product["url"], cur)
        try:
            r = requests.get(url, headers=UA, timeout=20)
            if r.status_code == 200 and r.headers.get("content-type", "").startswith("image"):
                frames.append((cur, r.content))
        except requests.RequestException:
            pass
        cur += timedelta(minutes=step_min)
    return frames


def make_gif(frames: list[tuple[datetime, bytes]], frame_ms: int, max_w: int = 900) -> bytes | None:
    if not frames:
        return None
    imgs = []
    for _, b in frames:
        im = Image.open(io.BytesIO(b)).convert("RGB")
        if im.width > max_w:
            im = im.resize((max_w, int(im.height * max_w / im.width)))
        imgs.append(im.quantize(colors=128))
    buf = io.BytesIO()
    durations = [frame_ms] * (len(imgs) - 1) + [frame_ms * 4]  # 最後一幀停久一點
    imgs[0].save(buf, format="GIF", save_all=True, append_images=imgs[1:], duration=durations, loop=0, optimize=True)
    return buf.getvalue()


def collect(cfg: dict, now_local: datetime, is_daylight: bool) -> dict[str, dict]:
    """回傳 {product_key: {label, page, latest_png, latest_time, gif, n_frames}}"""
    im = cfg["imagery"]
    out = {}
    for key, p in im["products"].items():
        if p.get("daylight_only") and not is_daylight:
            continue
        if key == "sat_ir" and is_daylight and "sat_vis" in im["products"]:
            continue  # 白天用真實色，晚上用紅外線
        frames = fetch_frames(p, now_local, im["hours_back"], im["step_min"])
        entry = {"label": p["label"], "page": p.get("page"), "n_frames": len(frames),
                 "latest_png": None, "latest_time": None, "gif": None}
        if frames:
            entry["latest_time"], entry["latest_png"] = frames[-1]
            entry["gif"] = make_gif(frames, im["gif_frame_ms"])
        out[key] = entry
    return out
