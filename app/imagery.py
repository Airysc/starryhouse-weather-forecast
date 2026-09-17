"""氣象署雷達回波 / 衛星雲圖：抓最新一張 + 前 N 小時動畫幀（皆縮圖轉 WebP，由網頁 JS 輪播）"""
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


def to_webp(b: bytes, max_w: int, quality: int) -> bytes:
    im = Image.open(io.BytesIO(b)).convert("RGB")
    if im.width > max_w:
        im = im.resize((max_w, int(im.height * max_w / im.width)), Image.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, format="WEBP", quality=quality, method=4)
    return buf.getvalue()


def pick_frames(frames: list, n: int) -> list:
    """從 frames 均勻抽 n 幀，一定包含最後一幀"""
    if len(frames) <= n:
        return frames
    idx = sorted({round(i * (len(frames) - 1) / (n - 1)) for i in range(n)})
    return [frames[i] for i in idx]


def collect(cfg: dict, now_local: datetime, is_daylight: bool) -> dict[str, dict]:
    """回傳 {product_key: {label, page, latest(bytes webp), latest_time, frames: [(time, bytes webp)], n_frames}}"""
    im = cfg["imagery"]
    out = {}
    for key, p in im["products"].items():
        frames = fetch_frames(p, now_local, im["hours_back"], im["step_min"])
        entry = {"label": p["label"], "page": p.get("page"), "n_frames": 0, "latest": None, "latest_time": None, "frames": []}
        if frames:
            entry["latest_time"] = frames[-1][0]
            entry["latest"] = to_webp(frames[-1][1], im["max_width"], im["quality"])
            picked = pick_frames(frames, im["anim_frames"])
            entry["frames"] = [(t, to_webp(b, im["anim_width"], im["anim_quality"])) for t, b in picked]
            entry["n_frames"] = len(entry["frames"])
        out[key] = entry
    return out
