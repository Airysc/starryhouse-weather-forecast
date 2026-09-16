"""確認 config.yaml 裡雷達 / 衛星圖網址格式是否正確：列出過去 3 小時哪些時間點抓得到。
用法：python tools/probe_images.py
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.config import load_config
from app.sun import now_local
from app.imagery import fetch_frames, _fmt, _floor
from datetime import timedelta

cfg = load_config()
now = now_local(cfg)
for key, p in cfg["imagery"]["products"].items():
    frames = fetch_frames(p, now, cfg["imagery"]["hours_back"], cfg["imagery"]["step_min"])
    print(f"\n[{key}] {p['label']}  抓到 {len(frames)} 幀")
    print("  範例網址：", _fmt(p["url"], _floor(now - timedelta(minutes=30), cfg["imagery"]["step_min"])))
    for t, b in frames[-3:]:
        print(f"  {t:%m/%d %H:%M}  {len(b)//1024} KB")
    if not frames:
        print("  → 0 幀：網址格式或時區可能不對，開官網頁面用 DevTools 看實際圖片網址後修改 config.yaml 的 url，"
              "可用的占位符：{ts_local_compact} {ts_local_dash} {ts_utc_compact} {ts_utc_dash}")
