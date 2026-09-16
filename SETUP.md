# StarryHouse Weather Forecast — 網頁 repo 部署指引（給 Claude Code 執行）

標示 **[人工]** 的步驟由使用者在瀏覽器完成；Claude Code 全程不接觸金鑰值。工作目錄為本專案根目錄。

## 0. 環境
```bash
python3 --version && git --version && gh --version && gh auth status
pip install -r requirements.txt
python3 -m py_compile app/*.py tools/*.py
```

## 1. 建立公開 repo 並推送
```bash
OWNER=$(gh api user -q .login)   # 放 organization 則改成 org 名稱，Pages 網址會是 https://<org 小寫>.github.io/
gh repo create starryhouse-weather-forecast --public --description "清境觀星園觀測天氣網頁"
sed -i '' "s#https://OWNER.github.io/#https://${OWNER}.github.io/#" config.yaml   # macOS；Linux 去掉 ''
git init -b main && git add -A && git commit -m "init StarryHouse Weather Forecast"
git remote add origin "https://github.com/${OWNER}/starryhouse-weather-forecast.git"
git push -u origin main
```

## 2. 啟用 GitHub Pages（來源：GitHub Actions）
```bash
gh api -X POST "repos/${OWNER}/starryhouse-weather-forecast/pages" -f build_type=workflow
```
若回傳 409 表示已啟用；若失敗，請使用者到 repo → Settings → Pages → Source 選 **GitHub Actions**。

## 3. 金鑰 **[人工，不要交給 Claude Code]**
Claude Code 在此停下，請使用者自行到 repo → Settings → Secrets and variables → Actions 新增：

| Secret | 取得方式 |
|---|---|
| `CWA_API_KEY` | https://opendata.cwa.gov.tw 註冊 → 會員 → 取得授權碼 |
| `YOUTUBE_API_KEY` | GCP 專案 → 啟用 YouTube Data API v3 → 建立 API 金鑰（可略過） |

使用者回覆「已設定」後，Claude Code 只檢查名稱：`gh secret list -R "${OWNER}/starryhouse-weather-forecast"`

## 4. 資料集代碼與圖片網址（已完成，僅供日後參考）
- 育樂預報 F-B0053 系列只提供檔案下載（fileapi），datastore 端點一律 404。`config.yaml` 已填 `F-B0053-017`（農場 3 天逐 3 小時，清境農場）；想改用鳶峰停車場（2,750 m）則填 `F-B0053-071`。
- 雷達／衛星圖網址已驗證（衛星為 `.jpg`、時間戳皆為台灣時間）。
- 要重新檢查時，用 `tools` workflow（手動觸發）在 Actions 上跑：
```bash
REPO="${OWNER}/starryhouse-weather-forecast"
gh workflow run tools -R "$REPO" -f tool=find_cwa_dataset                      # 掃描 F-B0053 全系列、列出地點名稱
gh workflow run tools -R "$REPO" -f tool=inspect_cwa_dataset -f args="F-B0053-017 清境農場"   # 看某資料集的因子與筆數
gh workflow run tools -R "$REPO" -f tool=probe_images                          # 驗證圖片網址（不需金鑰，本機也能跑）
gh run view -R "$REPO" $(gh run list -R "$REPO" --workflow tools -L1 --json databaseId -q '.[0].databaseId') --log
```

## 5. 首次部署與驗證
```bash
gh workflow run "StarryHouse Weather Forecast (build & deploy)" -R "$REPO" && sleep 120
gh run list -R "$REPO" -L1
curl -s "https://${OWNER}.github.io/starryhouse-weather-forecast/data/latest.json" | head -c 600
```
瀏覽器開 `https://${OWNER}.github.io/starryhouse-weather-forecast/`，確認八個區塊都有內容；缺的區塊回報 log 錯誤行。

## 完成條件
- 最新一次 run 為 success，且之後每 10 分鐘自動執行
- 網頁即時觀測、預報表、雷達、衛星有資料；天文時刻可切換日期
- `data/latest.json` 可公開讀取（通知 repo 會用）
