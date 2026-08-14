from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from urllib.parse import urlencode

import pandas as pd

from .models import UniverseStock
from .taiwan_open_data import (
    clean_number,
    fetch_json,
    fetch_taiwan_fundamentals,
    fetch_taiwan_valuations,
    _request_json,
)
from .yfinance_client import MarketSnapshot


TWSE_DAILY_URL = "https://openapi.twse.com.tw/v1/exchangeReport/STOCK_DAY_ALL"
TPEX_DAILY_URL = "https://www.tpex.org.tw/openapi/v1/tpex_mainboard_daily_close_quotes"
MAX_HISTORY_DAYS = 260
TWSE_REFERENCE_URL = "https://www.twse.com.tw/rwd/zh/afterTrading/STOCK_DAY"
TPEX_REFERENCE_URL = "https://www.tpex.org.tw/www/zh-tw/afterTrading/tradingStock"


def _roc_date(value: object) -> date:
    text = str(value or "").strip()
    if len(text) != 7 or not text.isdigit():
        raise ValueError(f"Invalid ROC date: {text}")
    return date(int(text[:3]) + 1911, int(text[3:5]), int(text[5:7]))


def _roc_slash_date(value: object) -> date:
    year, month, day = (int(part) for part in str(value or "").split("/"))
    return date(year + 1911, month, day)


def _reference_close(symbol: str, market_date: date) -> float | None:
    code = symbol.split(".", 1)[0]
    if symbol.endswith(".TW"):
        query = urlencode(
            {
                "date": market_date.strftime("%Y%m%d"),
                "stockNo": code,
                "response": "json",
            }
        )
        payload = _request_json(f"{TWSE_REFERENCE_URL}?{query}")
        rows = payload.get("data", []) if isinstance(payload, dict) else []
    else:
        query = urlencode(
            {
                "code": code,
                "date": market_date.strftime("%Y/%m/%d"),
                "response": "json",
            }
        )
        payload = _request_json(f"{TPEX_REFERENCE_URL}?{query}")
        tables = payload.get("tables", []) if isinstance(payload, dict) else []
        rows = tables[0].get("data", []) if tables else []

    for row in reversed(rows):
        try:
            if _roc_slash_date(row[0]) == market_date:
                return clean_number(row[6])
        except (TypeError, ValueError, IndexError):
            continue
    return None


def _validate_final_quotes(quotes: dict[str, tuple[date, float, float]]) -> None:
    """Reject bulk files whose date advanced before their prices finalized."""
    anchors = ("2330.TW", "6488.TWO")
    anchor_dates: set[date] = set()
    for symbol in anchors:
        quote = quotes.get(symbol)
        if quote is None:
            raise RuntimeError(f"Official bulk quote is missing validation anchor {symbol}")
        market_date, bulk_close, _ = quote
        anchor_dates.add(market_date)
        reference_close = _reference_close(symbol, market_date)
        if reference_close is None or abs(reference_close - bulk_close) > 0.001:
            raise RuntimeError(
                f"Official bulk quotes are not finalized for {market_date}: "
                f"{symbol} bulk={bulk_close}, official detail={reference_close}"
            )
    if len(anchor_dates) != 1:
        formatted_dates = ", ".join(sorted(value.isoformat() for value in anchor_dates))
        raise RuntimeError(
            f"TWSE and TPEx closing files do not share one market date: {formatted_dates}"
        )


def fetch_official_daily_quotes(
    *,
    validate_final: bool = True,
) -> dict[str, tuple[date, float, float]]:
    quotes: dict[str, tuple[date, float, float]] = {}

    for row in fetch_json(TWSE_DAILY_URL):
        code = str(row.get("Code") or "").strip()
        close = clean_number(row.get("ClosingPrice"))
        volume = clean_number(row.get("TradeVolume"))
        if len(code) == 4 and code.isdigit() and close is not None:
            quotes[f"{code}.TW"] = (_roc_date(row.get("Date")), close, volume or 0)

    for row in fetch_json(TPEX_DAILY_URL):
        code = str(row.get("SecuritiesCompanyCode") or "").strip()
        close = clean_number(row.get("Close"))
        volume = clean_number(row.get("TradingShares"))
        if len(code) == 4 and code.isdigit() and close is not None:
            quotes[f"{code}.TWO"] = (_roc_date(row.get("Date")), close, volume or 0)

    if validate_final:
        _validate_final_quotes(quotes)
    return quotes


def load_history_store(path: Path) -> dict:
    if not path.exists():
        return {"latest_market_date": None, "stocks": {}}
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload.get("stocks"), dict):
        raise ValueError(f"Invalid history store: {path}")
    return payload


def write_history_store(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def update_history_store(path: Path, universe: list[UniverseStock]) -> tuple[dict, str]:
    payload = load_history_store(path)
    records = payload["stocks"]
    allowed_symbols = {stock.symbol for stock in universe}
    quotes = fetch_official_daily_quotes()
    market_dates: list[date] = []

    for symbol, (market_date, close, volume) in quotes.items():
        if symbol not in allowed_symbols:
            continue
        market_dates.append(market_date)
        record = records.setdefault(symbol, {"dates": [], "closes": [], "volumes": []})
        iso_date = market_date.isoformat()
        dates = record.setdefault("dates", [])

        if dates and dates[-1] == iso_date:
            record["closes"][-1] = close
            record["volumes"][-1] = volume
        elif not dates or dates[-1] < iso_date:
            dates.append(iso_date)
            record.setdefault("closes", []).append(close)
            record.setdefault("volumes", []).append(volume)

        record["dates"] = record["dates"][-MAX_HISTORY_DAYS:]
        record["closes"] = record["closes"][-MAX_HISTORY_DAYS:]
        record["volumes"] = record["volumes"][-MAX_HISTORY_DAYS:]

    if not market_dates:
        raise RuntimeError("Official exchanges returned no common-stock quotes")

    latest_market_date = max(market_dates).isoformat()
    payload["latest_market_date"] = latest_market_date
    payload["stocks"] = {symbol: records[symbol] for symbol in sorted(records) if symbol in allowed_symbols}
    write_history_store(path, payload)
    return payload, latest_market_date


def snapshots_from_history(
    universe: list[UniverseStock],
    payload: dict,
) -> tuple[list[MarketSnapshot], list[str]]:
    valuations = fetch_taiwan_valuations()
    fundamentals = fetch_taiwan_fundamentals()
    records = payload.get("stocks", {})
    snapshots: list[MarketSnapshot] = []
    failed: list[str] = []

    for stock in universe:
        record = records.get(stock.symbol)
        if not record or not record.get("closes"):
            failed.append(stock.symbol)
            continue
        history = pd.DataFrame(
            {
                "Close": record["closes"],
                "Volume": record.get("volumes", [0] * len(record["closes"])),
            },
            index=pd.to_datetime(record["dates"]),
        )
        snapshots.append(
            MarketSnapshot(
                stock=stock,
                history=history,
                info={
                    **valuations.get(stock.symbol, {}),
                    **fundamentals.get(stock.symbol, {}),
                },
            )
        )

    return snapshots, failed
