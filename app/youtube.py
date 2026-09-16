"""找出頻道目前正在直播、標題符合關鍵字的影片"""
import json
import re
import subprocess
import requests

API = "https://www.googleapis.com/youtube/v3/"


def _channel_id(handle: str, key: str) -> str | None:
    r = requests.get(API + "channels", params={"part": "id", "forHandle": handle, "key": key}, timeout=20)
    if r.ok and r.json().get("items"):
        return r.json()["items"][0]["id"]
    return None


def _match(title: str, keywords: list[str]) -> bool:
    return any(k in title for k in keywords)


def find_live_api(handle: str, keywords: list[str], key: str, cache: dict) -> dict | None:
    cid = cache.get("channel_id") or _channel_id(handle, key)
    if not cid:
        return None
    cache["channel_id"] = cid
    r = requests.get(API + "search", params={
        "part": "snippet", "channelId": cid, "eventType": "live", "type": "video", "maxResults": 10, "key": key,
    }, timeout=20)
    r.raise_for_status()
    items = r.json().get("items", [])
    hits = [i for i in items if _match(i["snippet"]["title"], keywords)]
    if not hits:
        return None
    hits.sort(key=lambda i: i["snippet"].get("publishedAt", ""), reverse=True)
    h = hits[0]
    return {"id": h["id"]["videoId"], "title": h["snippet"]["title"], "source": "api"}


def find_live_ytdlp(handle: str, keywords: list[str]) -> dict | None:
    try:
        p = subprocess.run(
            ["yt-dlp", "--flat-playlist", "-j", "--quiet", "--no-warnings", f"https://www.youtube.com/@{handle}/streams"],
            capture_output=True, text=True, timeout=90)
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return None
    for line in p.stdout.splitlines():
        try:
            e = json.loads(line)
        except json.JSONDecodeError:
            continue
        if e.get("live_status") == "is_live" and _match(e.get("title", ""), keywords):
            return {"id": e["id"], "title": e["title"], "source": "yt-dlp"}
    return None


def find_live_page(page_url: str) -> dict | None:
    """備援：從 tw.live 之類的頁面抓嵌入的 YouTube ID"""
    try:
        html = requests.get(page_url, headers={"User-Agent": "Mozilla/5.0"}, timeout=20).text
    except requests.RequestException:
        return None
    m = re.search(r"(?:youtube\.com/embed/|youtu\.be/|v=)([A-Za-z0-9_-]{11})", html)
    return {"id": m.group(1), "title": "(from fallback page)", "source": "page"} if m else None


def still_live(video_id: str) -> bool:
    try:
        p = subprocess.run(["yt-dlp", "-j", "--quiet", "--no-warnings", "--no-download", f"https://www.youtube.com/watch?v={video_id}"],
                           capture_output=True, text=True, timeout=60)
        return p.returncode == 0 and json.loads(p.stdout).get("live_status") == "is_live"
    except Exception:
        return False


def resolve(stream_cfg: dict, key: str | None, cache: dict) -> dict | None:
    """依序：上次 ID 仍在播 → Data API → yt-dlp → 備援頁面"""
    kws = stream_cfg["keywords"]
    last = cache.get("last_id")
    if last and still_live(last):
        return {"id": last, "title": cache.get("last_title", ""), "source": "cache"}
    found = None
    if key:
        try:
            found = find_live_api(stream_cfg["handle"], kws, key, cache)
        except Exception:
            found = None
    if not found:
        found = find_live_ytdlp(stream_cfg["handle"], kws)
    if not found and stream_cfg.get("fallback_page"):
        found = find_live_page(stream_cfg["fallback_page"])
    if found:
        cache["last_id"], cache["last_title"] = found["id"], found["title"]
    return found
