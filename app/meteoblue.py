"""meteoblue widget 截圖：用無頭 Chromium 開 widget 網址，存成 WebP（失敗回傳 None，網頁退回 iframe）"""
import io
from PIL import Image


def screenshot(cfg: dict) -> bytes | None:
    mb = cfg.get("site", {}).get("meteoblue") or {}
    url = mb.get("widget_url")
    if not url:
        return None
    from playwright.sync_api import sync_playwright
    w, h = int(mb.get("width", 1100)), int(mb.get("height", 400))
    with sync_playwright() as p:
        b = p.chromium.launch()
        ctx = b.new_context(viewport={"width": w, "height": h}, device_scale_factor=float(mb.get("scale", 1.5)),
                            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0 Safari/537.36",
                            extra_http_headers={"Referer": cfg["site"]["url"]})
        pg = ctx.new_page()
        pg.goto(url, wait_until="networkidle", timeout=90000)
        pg.wait_for_timeout(2500)
        # 圖表畫好時 body 會有溫度軸文字；沒有就當失敗
        if "Temperature" not in pg.evaluate("document.body.innerText"):
            b.close()
            return None
        png = pg.screenshot(full_page=True)
        b.close()
    im = Image.open(io.BytesIO(png)).convert("RGB")
    buf = io.BytesIO()
    im.save(buf, format="WEBP", quality=int(mb.get("quality", 82)), method=4)
    return buf.getvalue()
