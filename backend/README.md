# 台股全市場成長科技篩選後端

這個後端採「盤後批次更新」設計：以臺灣證交所與櫃買中心的全市場資料更新行情與基本面，計算價值、品質成長、動能及資料完整度，最後輸出 `public/data/screener-data.json` 給網站與每日 Email 使用。

## 目前範圍

- 支援完整上市、上櫃普通股，代號格式為上市 `2330.TW`、上櫃 `6488.TWO`
- 計算 MA5、MA20、MA60、60/120 日動能、20 日量比與一年高點回落
- 從官方 OpenAPI 取得 PE、殖利率、PBR、ROE、毛利率、營收年增率與負債權益比
- 缺值指標會移除權重後重新正規化，並另外揭露資料完整度
- 產生前端用 JSON
- 提供 FastAPI 讀取最新 JSON 的 API 骨架

## 安裝

```powershell
cd D:\codex_project
py -m venv .venv
.\.venv\Scripts\pip install -r backend\requirements.txt
```

如果沒有 `py`，可改用你的 Python 路徑。

## 產生篩選資料

```powershell
.\.venv\Scripts\python -m backend.app.export_static --universe backend\config\watchlist.sample.csv --min-score 0 --max-pe 999 --include-non-bullish
```

輸出位置：

- `backend/storage/screener-data.json`
- `public/data/screener-data.json`

網站會讀取完整 JSON，預設顯示排除指定產業後的 1,500 檔股票，再依科技產業偏好與總分排序。

## 寄出台股多頭排列 Email

先複製 `.env.example` 成 `.env`，填入 SMTP 設定與收件人。建議建立一個專門寄信的 Gmail 或 Outlook 帳號，例如「台股多頭篩選器」，再用該帳號的 SMTP 或 App Password 寄信。Gmail 建議使用 App Password，不要使用一般登入密碼。

```powershell
Copy-Item .env.example .env
notepad .env
```

先預覽信件內容：

```powershell
.\.venv\Scripts\python -m backend.app.email_report --dry-run
```

寄出信件：

```powershell
.\.venv\Scripts\python -m backend.app.email_report
```

每日信件預設寄出科技產業優先的前 50 名，並列出單日及近三日漲跌、三大分數、資料完整度、排名理由與主要風險。連續三次以上入選者會以紅字提醒；追蹤紀錄保存在 `backend/data/email_report_history.json`。

`.env` 主要設定：

```env
SCREENER_EMAIL_TO=junge3e3@gmail.com
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=你的專用寄件Gmail
SMTP_PASSWORD=你的Gmail App Password
SMTP_FROM=你的專用寄件Gmail
SMTP_FROM_NAME=台股多頭篩選器
SMTP_USE_TLS=true
SMTP_USE_SSL=false
```

## 啟動 API

```powershell
.\.venv\Scripts\uvicorn backend.app.main:app --reload --port 8000
```

API：

- `GET /health`
- `GET /api/screener/results`
- `POST /api/screener/run`

## 注意

這套後端定位為個人量化研究工具，不作為買賣建議。PEG、自由現金流殖利率與 EPS 年增率若官方批次資料暫缺，會依規則排除該項權重，不會補成 0 分。
