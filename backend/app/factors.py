from __future__ import annotations

import math

import pandas as pd

from .models import ScreenerStock
from .yfinance_client import MarketSnapshot


def _clean_number(value: object) -> float | None:
    if value is None:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(number) or math.isinf(number):
        return None
    return number


def _percent(value: object) -> float | None:
    number = _clean_number(value)
    if number is None:
        return None
    if abs(number) <= 1.5:
        number *= 100
    return round(number, 2)


def _dividend_yield_percent(value: object) -> float | None:
    number = _clean_number(value)
    if number is None:
        return None
    if abs(number) <= 0.2:
        number *= 100
    return round(number, 2)


def _score_component(value: float | None, low: float, high: float, inverse: bool = False) -> float | None:
    if value is None:
        return None
    if high == low:
        return None
    normalized = max(0, min(1, (value - low) / (high - low)))
    if inverse:
        normalized = 1 - normalized
    return normalized * 100


def _weighted_score(parts: list[tuple[float | None, float]]) -> float | None:
    available = [(value, weight) for value, weight in parts if value is not None]
    total_weight = sum(weight for _, weight in available)
    if not available or total_weight <= 0:
        return None
    return sum(value * weight for value, weight in available) / total_weight


def build_stock(snapshot: MarketSnapshot) -> ScreenerStock | None:
    history = snapshot.history.copy()
    if history.empty or "Close" not in history:
        return None

    history = history.dropna(subset=["Close"])
    if history.empty:
        return None

    close = history["Close"]
    volume = history["Volume"] if "Volume" in history else pd.Series(dtype="float64")
    last_close = _clean_number(close.iloc[-1])
    previous_close = _clean_number(close.iloc[-2]) if len(close) > 1 else None
    change_percent = None
    if last_close is not None and previous_close:
        change_percent = round(((last_close - previous_close) / previous_close) * 100, 2)

    ma5 = _clean_number(close.tail(5).mean()) if len(close) >= 5 else None
    ma20 = _clean_number(close.tail(20).mean()) if len(close) >= 20 else None
    ma60 = _clean_number(close.tail(60).mean()) if len(close) >= 60 else None
    is_bullish_alignment = (
        last_close is not None
        and ma5 is not None
        and ma20 is not None
        and ma60 is not None
        and last_close > ma5 > ma20 > ma60
    )
    alignment_gap = None
    if last_close is not None and ma60:
        alignment_gap = round(((last_close - ma60) / ma60) * 100, 2)

    start_60 = _clean_number(close.iloc[-60]) if len(close) >= 60 else None
    momentum_60d = None
    if last_close is not None and start_60:
        momentum_60d = round(((last_close - start_60) / start_60) * 100, 2)

    volume_ratio_20d = None
    if not volume.empty and len(volume) >= 20:
        avg_volume = _clean_number(volume.tail(20).mean())
        last_volume = _clean_number(volume.iloc[-1])
        if avg_volume and last_volume is not None:
            volume_ratio_20d = round(last_volume / avg_volume, 2)

    high_1y = _clean_number(close.max())
    drawdown_1y = None
    if last_close is not None and high_1y:
        drawdown_1y = round(((last_close - high_1y) / high_1y) * 100, 2)

    info = snapshot.info
    pe = _clean_number(info.get("trailingPE") or info.get("forwardPE"))
    dividend_yield = _dividend_yield_percent(info.get("dividendYield"))
    pbr = _clean_number(info.get("priceToBook"))
    roe = _percent(info.get("returnOnEquity"))
    gross_margin = _percent(info.get("grossMargins"))
    debt_to_equity = _clean_number(info.get("debtToEquity"))

    trend_bonus = 100 if is_bullish_alignment else 0
    value_score = _weighted_score(
        [
            (_score_component(pe, 5, 45, inverse=True), 0.55),
            (_score_component(dividend_yield, 0, 6), 0.25),
            (_score_component(pbr, 0.5, 8, inverse=True), 0.2),
        ]
    )
    quality_score = _weighted_score(
        [
            (_score_component(roe, 0, 35), 0.45),
            (_score_component(gross_margin, 10, 70), 0.35),
            (_score_component(debt_to_equity, 0, 160, inverse=True), 0.2),
        ]
    )
    momentum_score = _weighted_score(
        [
            (_score_component(momentum_60d, -20, 40), 0.5),
            (_score_component(volume_ratio_20d, 0.5, 2.2), 0.15),
            (_score_component(drawdown_1y, -45, 0), 0.1),
            (trend_bonus, 0.25),
        ]
    )
    total_score = round(
        _weighted_score(
            [
                (value_score, 0.2),
                (quality_score, 0.3),
                (momentum_score, 0.5),
            ]
        )
        or 0,
        1,
    )

    tags = []
    if is_bullish_alignment:
        tags.append("多頭排列")
    if momentum_60d is not None and momentum_60d >= 15:
        tags.append("動能")
    if pe is not None and pe <= 20:
        tags.append("估值")
    if roe is not None and roe >= 18:
        tags.append("品質")
    if dividend_yield is not None and dividend_yield >= 3:
        tags.append("股息")

    return ScreenerStock(
        symbol=snapshot.stock.symbol,
        name=snapshot.stock.name,
        market=snapshot.stock.market,
        industry=snapshot.stock.industry,
        currency=info.get("currency"),
        price=round(last_close, 2) if last_close is not None else None,
        change_percent=change_percent,
        pe=round(pe, 2) if pe is not None else None,
        dividend_yield=dividend_yield,
        pbr=round(pbr, 2) if pbr is not None else None,
        roe=roe,
        gross_margin=gross_margin,
        debt_to_equity=round(debt_to_equity, 2) if debt_to_equity is not None else None,
        ma5=round(ma5, 2) if ma5 is not None else None,
        ma20=round(ma20, 2) if ma20 is not None else None,
        ma60=round(ma60, 2) if ma60 is not None else None,
        is_bullish_alignment=is_bullish_alignment,
        alignment_gap=alignment_gap,
        momentum_60d=momentum_60d,
        volume_ratio_20d=volume_ratio_20d,
        drawdown_1y=drawdown_1y,
        score=total_score,
        tags=tags,
    )
