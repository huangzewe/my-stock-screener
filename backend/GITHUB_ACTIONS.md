# GitHub Actions cloud email setup

這個專案可以用 GitHub Actions 在雲端每天寄出台股多頭排列篩選結果。電腦不需要開機，只要 GitHub repository 存在、Actions 開啟、Secrets 設定完成即可。

## 排程

Workflow 檔案：`.github/workflows/taiwan-screener-email.yml`

- 每天台灣時間 `08:30`
- 每天台灣時間 `22:00`
- 也可以在 GitHub 的 `Actions` 頁面用 `Run workflow` 手動測試

## 你需要在 GitHub 設定的 Secrets

到你的 GitHub repository：

`Settings` -> `Secrets and variables` -> `Actions` -> `New repository secret`

新增這些 repository secrets：

```text
SCREENER_EMAIL_TO
SMTP_HOST
SMTP_PORT
SMTP_USERNAME
SMTP_PASSWORD
SMTP_FROM
SMTP_FROM_NAME
```

Gmail 範例：

```text
SCREENER_EMAIL_TO=收件信箱
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=寄件 Gmail
SMTP_PASSWORD=Gmail App Password
SMTP_FROM=寄件 Gmail
SMTP_FROM_NAME=台股多頭篩選器
```

請使用 Gmail App Password，不要使用一般登入密碼。

## 第一次測試

1. 把這個專案 push 到 GitHub。
2. 到 GitHub repository 的 `Actions` 分頁。
3. 選 `Taiwan Bullish Screener Email`。
4. 按 `Run workflow`。
5. 確認收到 email。

如果手動測試成功，之後就會自動在每天台灣時間 `08:30` 和 `22:00` 寄出。
