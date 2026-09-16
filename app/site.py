"""把本次結果組成 build/：靜態頁 + data/latest.json + img/*.png|gif（每次全部重建，由 deploy-pages 整包部署）"""
import json
import shutil
from dataclasses import asdict
from .config import ROOT

SRC = ROOT / "site"
BUILD = ROOT / "build"


def write(ctx: dict) -> dict:
    if BUILD.exists():
        shutil.rmtree(BUILD)
    shutil.copytree(SRC, BUILD)
    (BUILD / "img").mkdir(exist_ok=True)
    (BUILD / "data").mkdir(exist_ok=True)

    images = {}
    for key, im in ctx["images"].items():
        e = {"label": im["label"], "page": im.get("page"), "n_frames": im["n_frames"],
             "latest_time": im["latest_time"].isoformat(timespec="minutes") if im.get("latest_time") else None,
             "latest": None, "gif": None}
        if im.get("latest_png"):
            (BUILD / "img" / f"{key}.png").write_bytes(im["latest_png"]); e["latest"] = f"img/{key}.png"
        if im.get("gif"):
            (BUILD / "img" / f"{key}.gif").write_bytes(im["gif"]); e["gif"] = f"img/{key}.gif"
        images[key] = e

    streams = []
    for s in ctx["streams"]:
        v = s.get("video")
        streams.append({"name": s["name"], "handle": s["handle"], "live": bool(v),
                        "video_id": v["id"] if v else None, "title": v.get("title") if v else None,
                        "channel_id": s.get("channel_id")})

    loc = ctx["cfg"]["location"]
    data = {
        "generated_at": ctx["now"].isoformat(timespec="minutes"),
        "site_name": loc["name"],
        "location": {"lat": loc["latitude"], "lon": loc["longitude"], "elevation_m": loc["elevation_m"]},
        "sunset": ctx["sun"]["sunset"].isoformat(timespec="minutes"),
        "sunrise": ctx["sun"]["sunrise"].isoformat(timespec="minutes"),
        "summary": ctx["summary"],
        "slots": [asdict(s) for s in ctx["slots"]],
        "obs": ctx["obs"],
        "images": images,
        "streams": streams,
        "seven_timer": ctx["cfg"]["site"]["seven_timer"].format(lat=loc["latitude"], lon=loc["longitude"]),
        "links": ctx["cfg"]["site"].get("links", []),
    }
    (BUILD / "data" / "latest.json").write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    return data
