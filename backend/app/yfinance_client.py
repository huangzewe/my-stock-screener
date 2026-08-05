from __future__ import annotations

from dataclasses import dataclass

import pandas as pd
import yfinance as yf

from .models import UniverseStock


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
