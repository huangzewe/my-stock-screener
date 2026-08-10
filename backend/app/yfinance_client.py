from __future__ import annotations

from dataclasses import dataclass
import time
from collections.abc import Iterator

import pandas as pd
import yfinance as yf

from .models import UniverseStock
from .taiwan_open_data import (
    fetch_taiwan_fundamentals,
    fetch_taiwan_trading_dates,
    fetch_taiwan_valuations,
)


@dataclass(frozen=True)
class MarketSnapshot:
    stock: UniverseStock
    history: pd.DataFrame
    info: dict


def fetch_snapshot(stock: UniverseStock, period: str = "1y") -> MarketSnapshot:
    ticker = yf.Ticker(stock.symbol)
    history = ticker.history(period=period, auto_adjust=False)

    try:
        info = ticker.get_info()
    except Exception:
        info = {}

    return MarketSnapshot(stock=stock, history=history, info=info or {})


def _chunks(stocks: list[UniverseStock], size: int) -> Iterator[list[UniverseStock]]:
    for index in range(0, len(stocks), size):
        yield stocks[index : index + size]


def _ticker_history(frame: pd.DataFrame, symbol: str, batch_size: int) -> pd.DataFrame:
    if frame.empty:
        return pd.DataFrame()
    if batch_size == 1 and not isinstance(frame.columns, pd.MultiIndex):
        return frame.copy()
    try:
        return frame[symbol].copy()
    except (KeyError, TypeError):
        return pd.DataFrame()


def _filter_taiwan_trading_days(history: pd.DataFrame, trading_dates: set) -> pd.DataFrame:
    if history.empty or not trading_dates:
        return history
    mask = [timestamp.date() in trading_dates for timestamp in history.index]
    return history.loc[mask].copy()


def fetch_snapshots(
    stocks: list[UniverseStock],
    *,
    period: str = "1y",
    batch_size: int = 80,
    attempts: int = 3,
) -> tuple[list[MarketSnapshot], list[str]]:
    """Fetch price histories in batches and enrich Taiwan stocks with official valuations."""
    valuations: dict[str, dict] = {}
    fundamentals: dict[str, dict] = {}
    trading_dates: set = set()
    if any(stock.market in {"TW", "TWO"} for stock in stocks):
        try:
            valuations = fetch_taiwan_valuations()
        except Exception as error:
            print(f"[warn] valuation data unavailable: {error}")
        try:
            fundamentals = fetch_taiwan_fundamentals()
        except Exception as error:
            print(f"[warn] fundamental data unavailable: {error}")
        try:
            trading_dates = fetch_taiwan_trading_dates()
        except Exception as error:
            print(f"[warn] official trading calendar unavailable: {error}")

    snapshots: list[MarketSnapshot] = []
    failed: list[str] = []

    for batch_number, batch in enumerate(_chunks(stocks, batch_size), start=1):
        pending = batch
        histories: dict[str, pd.DataFrame] = {}

        for attempt in range(attempts):
            symbols = [stock.symbol for stock in pending]
            if not symbols:
                break
            try:
                frame = yf.download(
                    symbols,
                    period=period,
                    group_by="ticker",
                    auto_adjust=False,
                    actions=False,
                    progress=False,
                    threads=True,
                    timeout=30,
                )
            except Exception as error:
                print(f"[warn] batch {batch_number} attempt {attempt + 1} failed: {error}")
                frame = pd.DataFrame()

            still_missing: list[UniverseStock] = []
            for stock in pending:
                history = _ticker_history(frame, stock.symbol, len(symbols))
                if history.empty or "Close" not in history or history["Close"].dropna().empty:
                    still_missing.append(stock)
                else:
                    histories[stock.symbol] = history

            pending = still_missing
            if pending and attempt + 1 < attempts:
                time.sleep(2**attempt)

        for stock in batch:
            history = histories.get(stock.symbol)
            if history is None:
                failed.append(stock.symbol)
                continue
            if stock.market in {"TW", "TWO"}:
                history = _filter_taiwan_trading_days(history, trading_dates)
                if history.empty:
                    failed.append(stock.symbol)
                    continue
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

        print(
            f"[progress] batch {batch_number}: "
            f"{len(histories)}/{len(batch)} histories downloaded"
        )

    return snapshots, failed
