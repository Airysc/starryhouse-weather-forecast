# StarryHouse Weather Forecast

清境觀星園觀測天氣網頁。GitHub Actions 每 10 分鐘重建並部署到 GitHub Pages，網頁任何時候打開都是最新：

1. 即時天氣（最近的氣象署自動氣象站，目前為梅峰站）
2. 即時影像（鳶峰全天域、觀星園直播；有開播就嵌入播放器）
3. 未來 24 小時預報（氣象署清境農場逐 3 小時：相對濕度、天氣 icon、降雨機率、蒲福風級、觀測判斷）
4. 天文時刻（日落／日出、天文曙暮光、月光與無月時段時間軸、月相；瀏覽器端計算，可選日期）
5. 雲量與視寧度預報（Open-Meteo 逐時高／中／低雲量與降雨率、7Timer! 視寧度與透明度，48 小時）
6. 雷達回波、衛星雲圖（最新 + 前 3 小時動畫）
7. 氣象圖（meteoblue 5 日 widget；build 時截圖存成 WebP，失敗則嵌 iframe）

`data/latest.json` 同時提供給通知系統（另一個 repo）讀取。

## 結構

```
config.yaml          座標、門檻、資料集代碼、圖片網址格式、直播頻道、頁尾連結
site/index.html      靜態頁（含天文計算 JS）；site/icons/ 氣象署天氣 icon 與來源 logo
app/                 收集資料並產生 build/
  main.py            入口
  cwa.py             氣象署育樂預報（fileapi）+ 自動氣象站
  openmeteo.py       逐時雲量
  seventimer.py      7Timer! 視寧度／透明度
  scoring.py         時段分級與一句話結論（供通知使用）
  imagery.py         雷達／衛星抓圖，縮圖轉 WebP + 動畫幀
  meteoblue.py       meteoblue widget 無頭瀏覽器截圖
  youtube.py         直播偵測（Data API → yt-dlp → 備援頁）
  site.py            組 build/
tools/               一次性工具：找資料集代碼、驗證圖片網址
.github/workflows/pages.yml   每 10 分鐘 build → deploy-pages
```

產出不會 commit 進 repo（用 deploy-pages 直接部署），所以 repo 不會因為每天上百次更新而膨脹。

## 設定

見 `SETUP.md`。需要的 Secrets：`CWA_API_KEY`（必要）、`YOUTUBE_API_KEY`（可選，沒有就退回 yt-dlp）。

## 判斷規則（config.yaml → scoring）

| 等級 | 條件 |
|---|---|
| ✅ 適合 | 天氣現象含「晴」或「多雲時晴」，且 3 小時降雨機率 ≤ 20% |
| ⚠️ 勉強 | 天氣現象「多雲」，降雨機率 ≤ 30% |
| ❌ 不適合 | 陰／雨／霧／雷，或降雨機率 > 30% |

## 已知限制

- GitHub 排程在尖峰時段常延遲幾分鐘、偶爾漏跑；頁面顯示更新時間。
- YouTube 對機房 IP 偶有機器人偵測，直播偵測失敗時顯示未開播並附頻道連結。
- 天文時刻以 SunCalc 在瀏覽器計算，未考慮海拔與地形遮蔽，與觀測值可能差 1–2 分鐘。
- 育樂預報以清境農場（約 1,750 m）為代表點，觀星園高約 300 m。
