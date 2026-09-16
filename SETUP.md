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
OWNER=$(gh api user -q .login)
gh repo create starryhouse-weather-forecast --public --description "清境觀星園觀測天氣網頁"
sed -i "s#https://OWNER.github.io/#https://${OWNER}.github.io/#" config.yaml
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

## 4. 找出氣象署資料集代碼、驗證圖片網址
兩支工具需要金鑰，改在 Actions 執行。先臨時加一個 workflow：
```bash
cat > .github/workflows/tools.yml << 'YAML'
name: tools
on:
  workflow_dispatch:
    inputs:
      tool: { type: choice, options: [find_cwa_dataset, probe_images], default: find_cwa_dataset }
jobs:
  run:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.12" }
      - run: pip install -q -r requirements.txt
      - env: { CWA_API_KEY: "${{ secrets.CWA_API_KEY }}" }
        run: python tools/${{ github.event.inputs.tool }}.py
YAML
git add -A && git commit -m "tools workflow" && git push
REPO="${OWNER}/starryhouse-weather-forecast"
gh workflow run tools -R "$REPO" -f tool=find_cwa_dataset && sleep 75
gh run view -R "$REPO" $(gh run list -R "$REPO" --workflow tools -L1 --json databaseId -q '.[0].databaseId') --log | grep "F-B0053"
```
選「筆數約 24、時距 3 小時、因子含 Weather 與 ProbabilityOfPrecipitation」的 `F-B0053-0XX` 填入 `config.yaml` → `cwa.forecast_dataset`，push，再跑：
```bash
gh workflow run tools -R "$REPO" -f tool=probe_images && sleep 75
gh run view -R "$REPO" $(gh run list -R "$REPO" --workflow tools -L1 --json databaseId -q '.[0].databaseId') --log | grep -A4 "^\["
```
任一產品 0 幀：請使用者開該產品的官網頁（`config.yaml` 的 `page`），用 DevTools → Network 找實際圖片網址貼回，把時間部分改成占位符 `{ts_local_compact}` `{ts_local_dash}` `{ts_utc_compact}` `{ts_utc_dash}` 之一，更新 `url` 後重跑。`sat_vis` 夜間 0 幀正常，以 `sat_ir` 為準。
完成後可刪除 `tools.yml`。

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
