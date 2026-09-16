"""把本次結果組成 build/：靜態頁 + data/latest.json + img/*.webp（每次全部重建，由 deploy-pages 整包部署）"""
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
             "latest": None, "frames": []}
        if im.get("latest"):
            (BUILD / "img" / f"{key}.webp").write_bytes(im["latest"]); e["latest"] = f"img/{key}.webp"
        for i, (t, b) in enumerate(im.get("frames") or []):
            name = f"img/{key}_{i:02d}.webp"
            (BUILD / name).write_bytes(b)
            e["frames"].append({"src": name, "time": t.isoformat(timespec="minutes")})
        images[key] = e

    mb = ctx["cfg"]["site"].get("meteoblue") or {}
    meteoblue = {"image": None, "widget_url": mb.get("widget_url"), "link": mb.get("link")}
    if ctx.get("meteoblue_img"):
        (BUILD / "img" / "meteoblue.webp").write_bytes(ctx["meteoblue_img"]); meteoblue["image"] = "img/meteoblue.webp"

    streams = []
    for s in ctx["streams"]:
        v = s.get("video")
        streams.append({"name": s["name"], "handle": s["handle"], "live": bool(v),
                        "video_id": v["id"] if v else None, "title": v.get("title") if v else None,
                        "channel_id": s.get("channel_id")})

    loc = ctx["cfg"]["location"]
    data = {
        "generated_at": ctx["now"].isoformat(timespec="seconds"),
        "site_name": loc["name"],
        "location": {"lat": loc["latitude"], "lon": loc["longitude"], "elevation_m": loc["elevation_m"]},
        "sunset": ctx["sun"]["sunset"].isoformat(timespec="minutes"),
        "sunrise": ctx["sun"]["sunrise"].isoformat(timespec="minutes"),
        "summary": ctx["summary"],
        "slots": [asdict(s) for s in ctx["slots"]],
        "forecast24": ctx["forecast24"],
        "clouds": ctx["clouds"],
        "astro7": ctx["astro7"],
        "obs": ctx["obs"],
        "images": images,
        "streams": streams,
        "meteoblue": meteoblue,
        "frame_ms": ctx["cfg"]["imagery"]["frame_ms"],
        "links": ctx["cfg"]["site"].get("links", []),
    }
    (BUILD / "data" / "latest.json").write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    return data
