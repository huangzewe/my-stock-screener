from __future__ import annotations

import argparse
import os
import smtplib
from dataclasses import dataclass
from email.headerregistry import Address
from email.message import EmailMessage
from html import escape
from pathlib import Path

from dotenv import load_dotenv

from .export_static import generate_payload
from .models import ScreenerFilters, ScreenerPayload, ScreenerStock
from .screener import run_screener


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_ENV = PROJECT_ROOT / ".env"


@dataclass(frozen=True)
class EmailConfig:
    host: str
    port: int
    username: str | None
    password: str | None
    sender: str
    sender_name: str
    recipients: list[str]
    use_tls: bool
    use_ssl: bool


def load_email_config(to_override: str | None = None) -> EmailConfig:
    load_dotenv(DEFAULT_ENV)

    recipients = to_override or os.getenv("SCREENER_EMAIL_TO", "")
    recipient_list = [email.strip() for email in recipients.split(",") if email.strip()]

    return EmailConfig(
        host=os.getenv("SMTP_HOST", ""),
        port=int(os.getenv("SMTP_PORT", "587")),
        username=os.getenv("SMTP_USERNAME") or None,
        password=os.getenv("SMTP_PASSWORD") or None,
        sender=os.getenv("SMTP_FROM") or os.getenv("SMTP_USERNAME") or "",
        sender_name=os.getenv("SMTP_FROM_NAME", "台股多頭篩選器"),
        recipients=recipient_list,
        use_tls=os.getenv("SMTP_USE_TLS", "true").lower() == "true",
        use_ssl=os.getenv("SMTP_USE_SSL", "false").lower() == "true",
    )


def validate_email_config(config: EmailConfig) -> None:
    missing = []
    if not config.host:
        missing.append("SMTP_HOST")
    if not config.sender:
        missing.append("SMTP_FROM or SMTP_USERNAME")
    if not config.recipients:
        missing.append("SCREENER_EMAIL_TO")
    if config.username and not config.password:
        missing.append("SMTP_PASSWORD")
    if missing:
        raise ValueError("Missing email settings: " + ", ".join(missing))


def market_label(market: str) -> str:
    return {
        "TW": "上市",
        "TWO": "上櫃",
        "ETF": "ETF",
    }.get(market, market)


def format_number(value: float | None, suffix: str = "") -> str:
    if value is None:
        return "-"
    return f"{value:,.2f}{suffix}"


def build_text(stocks: list[ScreenerStock], generated_at: str, universe_size: int) -> str:
    lines = [
        "台股多頭排列篩選結果",
        "",
        f"資料時間：{generated_at}",
        f"股票池：{universe_size} 檔",
        f"本期成長科技候選：{len(stocks)} 檔",
        "",
        "排序：科技產業偏好、總分、品質成長、動能、資料完整度",
        "",
    ]

    if not stocks:
        lines.append("今天沒有股票符合篩選條件。")
        return "\n".join(lines)

    for index, stock in enumerate(stocks, start=1):
        lines.extend(
            [
                f"{index}. {stock.symbol} {stock.name}（{market_label(stock.market)} / {stock.industry}）",
                f"   總分：{format_number(stock.score)}；價值：{format_number(stock.value_score)}；品質成長：{format_number(stock.quality_growth_score)}；動能：{format_number(stock.momentum_score)}",
                f"   資料完整度：{format_number(stock.data_completeness, '%')}",
                f"   排名理由：{'；'.join(stock.ranking_reasons) if stock.ranking_reasons else '-'}",
                f"   主要風險：{'；'.join(stock.risks) if stock.risks else '-'}",
                "",
            ]
        )

    lines.extend(["提醒：這是量化篩選清單，不是買賣建議。"])
    return "\n".join(lines)


def build_html(stocks: list[ScreenerStock], generated_at: str, universe_size: int) -> str:
    rows = []
    for stock in stocks:
        rows.append(
            "<tr>"
            f"<td><strong>{escape(stock.symbol)}</strong><br><span>{escape(stock.name)}</span></td>"
            f"<td>{escape(stock.industry)}</td>"
            f"<td>{format_number(stock.score)}</td>"
            f"<td>{format_number(stock.value_score)}</td>"
            f"<td>{format_number(stock.quality_growth_score)}</td>"
            f"<td>{format_number(stock.momentum_score)}</td>"
            f"<td>{format_number(stock.data_completeness, '%')}</td>"
            f"<td>{escape('；'.join(stock.ranking_reasons) or '-')}</td>"
            f"<td>{escape('；'.join(stock.risks) or '-')}</td>"
            "</tr>"
        )

    if not rows:
        rows.append('<tr><td colspan="9">今天沒有股票符合篩選條件。</td></tr>')

    return f"""<!doctype html>
<html lang="zh-Hant">
<body style="font-family: Arial, 'Noto Sans TC', sans-serif; color: #1e293b;">
  <h2>台股成長科技選股排名</h2>
  <p>排序：<strong>科技產業偏好、總分、品質成長、動能、資料完整度</strong></p>
  <p>資料時間：{escape(generated_at)}<br>股票池：{universe_size} 檔<br>本期候選：{len(stocks)} 檔</p>
  <table cellpadding="8" cellspacing="0" border="1" style="border-collapse: collapse; border-color: #dbe3ea; font-size: 14px;">
    <thead style="background: #eefaf7;">
      <tr>
        <th>股票</th>
        <th>產業</th>
        <th>總分</th>
        <th>價值</th>
        <th>品質成長</th>
        <th>動能</th>
        <th>完整度</th>
        <th>排名理由</th>
        <th>主要風險</th>
      </tr>
    </thead>
    <tbody>
      {''.join(rows)}
    </tbody>
  </table>
  <p style="color:#64748b;font-size:12px;">提醒：這是量化篩選清單，不是買賣建議。</p>
</body>
</html>"""


def create_message(config: EmailConfig, subject: str, text: str, html: str) -> EmailMessage:
    message = EmailMessage()
    message["Subject"] = subject
    if "@" in config.sender:
        username, domain = config.sender.rsplit("@", 1)
        message["From"] = Address(display_name=config.sender_name, username=username, domain=domain)
    else:
        message["From"] = config.sender
    message["To"] = ", ".join(config.recipients)
    message.set_content(text)
    message.add_alternative(html, subtype="html")
    return message


def send_message(config: EmailConfig, message: EmailMessage) -> None:
    validate_email_config(config)
    smtp_class = smtplib.SMTP_SSL if config.use_ssl else smtplib.SMTP
    with smtp_class(config.host, config.port, timeout=30) as smtp:
        if config.use_tls and not config.use_ssl:
            smtp.starttls()
        if config.username:
            smtp.login(config.username, config.password or "")
        smtp.send_message(message)


def main() -> None:
    parser = argparse.ArgumentParser(description="Email Taiwan bullish-alignment screener results.")
    parser.add_argument(
        "--universe",
        type=Path,
        default=None,
        help="Optional CSV override. By default the complete TWSE/TPEx market is refreshed.",
    )
    parser.add_argument(
        "--data",
        type=Path,
        help="Use an existing screener JSON file instead of downloading the market again.",
    )
    parser.add_argument("--to", help="Recipient email. Overrides SCREENER_EMAIL_TO.")
    parser.add_argument("--min-score", type=float, default=0)
    parser.add_argument("--max-pe", type=float, default=999)
    parser.add_argument("--min-roe", type=float, default=-100)
    parser.add_argument("--min-momentum-60d", type=float, default=-100)
    parser.add_argument("--min-volume-ratio", type=float, default=0)
    parser.add_argument("--limit", type=int, default=50)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    filters = ScreenerFilters(
        require_bullish_alignment=False,
        min_score=args.min_score,
        max_pe=args.max_pe,
        min_roe=args.min_roe,
        min_momentum_60d=args.min_momentum_60d,
        min_volume_ratio=args.min_volume_ratio,
    )
    if args.data:
        payload = ScreenerPayload.model_validate_json(args.data.read_text(encoding="utf-8"))
        stocks = run_screener(payload.stocks, filters)
    else:
        payload = generate_payload(
            args.universe,
            filters,
            full_taiwan_market=args.universe is None,
        )
        stocks = payload.stocks
    stocks = stocks[: max(args.limit, 1)]
    generated_at = payload.generated_at.astimezone().strftime("%Y-%m-%d %H:%M")
    subject = f"台股成長科技選股：前 {len(stocks)} 名"
    text = build_text(stocks, generated_at, payload.universe_size)
    html = build_html(stocks, generated_at, payload.universe_size)

    if args.dry_run:
        print("Subject:", subject)
        print()
        print(text)
        return

    config = load_email_config(args.to)
    message = create_message(config, subject, text, html)
    send_message(config, message)
    print(f"[ok] sent report to {', '.join(config.recipients)}")


if __name__ == "__main__":
    main()
