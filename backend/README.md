# yfinance 股票篩選後端規劃與第一版實作

這個後端先採「盤後批次更新」設計：用 Python + yfinance 抓資料、計算指標、跑篩選條件，最後輸出 `public/data/screener-data.json` 給網站讀取。之後若需要登入、個人策略、即時 API，再啟用 FastAPI 常駐服務。

## 目前範圍

- 支援美股 ticker，例如 `AAPL`、`MSFT`、`NVDA`
- 支援台股 Yahoo ticker 格式，例如上市 `2330.TW`、上櫃 `6488.TWO`
- 計算 MA20、MA60、60 日動能、20 日量比、近一年高點回落
- 從 yfinance 補估值/基本面欄位：PE、殖利率、PBR、ROE、毛利率、負債權益比
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

網站會讀取完整 JSON，但前端預設先套用「多頭排列」條件：`股價 > MA5 > MA20 > MA60`。

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

預設股票池是 `backend/config/taiwan_universe.sample.csv`，只寄出符合 `股價 > MA5 > MA20 > MA60` 的台股清單。

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

## 分階段實作路線

1. 第一版：用 yfinance 對固定股票池產生盤後 JSON。
2. 第二版：前端從 `public/data/screener-data.json` 載入真實資料。
3. 第三版：加入自訂股票池、策略檔與排程。
4. 第四版：加入 SQLite/PostgreSQL，保存歷史因子與篩選結果。
5. 第五版：FastAPI 變成正式後端，網站即時呼叫 API。

## 注意

yfinance 是開源工具，資料來自 Yahoo Finance 公開資料，PyPI 說明也標明它未由 Yahoo 認可，且資料用途需留意 Yahoo 的使用條款。這套後端先定位成個人研究與學習工具，不作為交易建議。
