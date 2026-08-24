# 台股全市場每日排程

這個專案會透過 GitHub Actions 在每個台股交易日更新完整市場資料，電腦不需要保持開機。

## 排程內容

- 每個交易日台灣時間 22:00 開始確認資料；若官方整批行情尚未完成，會每 15 分鐘重試，正式資料完成後才寄信。
- 星期二至星期六台灣時間 09:00 會再執行一次補寄檢查；前一交易日若已寄過會直接跳過，若晚到的官方資料剛完成則自動補寄。
- 若收件端漏信，可由手動排程指定保存該交易日資料的 Git commit 與交易日，使用 `--force` 原樣重寄；歷史重寄不會覆蓋網站的最新行情。
- 從證交所與櫃買中心取得最新上市、上櫃公司清單。
- 排除 ETF、ETN、權證等非普通股商品。
- 排除紡織纖維、建材營造、貿易百貨、居家生活、生技醫療業、綠能環保、橡膠工業、金融保險、運動休閒。
- 從證交所與櫃買中心整批取得官方收盤行情，更新滾動歷史後計算均線、動能、量比、回撤與綜合分數。
- 更新 `public/data/screener-data.json`，網站重新整理後會讀取最新資料。
- 將科技產業優先的前 50 名股票、正式收盤價與風險說明寄到設定的 Email；同一市場交易日只寄一次。

排程檔案：`.github/workflows/taiwan-screener-email.yml`

## GitHub Secrets

在 repository 的 `Settings` → `Secrets and variables` → `Actions` 設定：

```text
SCREENER_EMAIL_TO
SCREENER_EMAIL_ADDITIONAL_TO
SMTP_HOST
SMTP_PORT
SMTP_USERNAME
SMTP_PASSWORD
SMTP_FROM
SMTP_FROM_NAME
```

`SCREENER_EMAIL_ADDITIONAL_TO` 可填多個以逗號分隔的收件人，不會取代原本的 `SCREENER_EMAIL_TO`。

Gmail 常用設定：

```text
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=你的 Gmail
SMTP_PASSWORD=Gmail 應用程式密碼
SMTP_FROM=你的 Gmail
SMTP_FROM_NAME=台股全市場篩選器
```

可以在 GitHub 的 `Actions` 頁面選擇 `Daily Taiwan Market Screener`，使用 `Run workflow` 手動測試。即使 Email 設定失敗，網站資料更新步驟也會先完成並推送。

## 本機執行

更新完整股票池：

```powershell
.\.venv\Scripts\python -m backend.app.refresh_universe
```

產生完整網站資料：

```powershell
.\.venv\Scripts\python -m backend.app.export_static --full-taiwan-market --official-daily --min-score 0 --max-pe 999 --include-non-bullish
```

使用 `--universe path/to/file.csv` 可以改回自訂股票清單。
