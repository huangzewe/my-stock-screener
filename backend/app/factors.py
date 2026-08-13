from __future__ import annotations

import math
from statistics import median

import pandas as pd

from .models import ScreenerStock
from .yfinance_client import MarketSnapshot


PREFERRED_TECH_INDUSTRIES = {
    "半導體業",
    "電腦及週邊設備業",
    "電子零組件業",
    "其他電子業",
    "通信網路業",
    "資訊服務業",
    "數位雲端",
    "光電業",
}


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


def _percent_metric(info: dict, ratio_key: str, percent_key: str) -> float | None:
    """Read an explicit percent-point value before a decimal ratio fallback."""
    if percent_key in info:
        number = _clean_number(info.get(percent_key))
        return round(number, 2) if number is not None else None
    return _percent(info.get(ratio_key))


def _score_component(
    value: float | None,
    low: float,
    high: float,
    *,
    inverse: bool = False,
) -> float | None:
    if value is None or high == low:
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


def _growth_value_component(peg: float | None, fcf_yield: float | None) -> float | None:
    if peg is not None:
        return _score_component(peg, 0.5, 3.0, inverse=True)
    return _score_component(fcf_yield, 0, 10)


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

    change_3d_percent = None
    if last_close is not None and len(close) >= 4:
        start_3d = _clean_number(close.iloc[-4])
        if start_3d:
            change_3d_percent = round(((last_close - start_3d) / start_3d) * 100, 2)

    ma5 = _clean_number(close.tail(5).mean()) if len(close) >= 5 else None
    ma20 = _clean_number(close.tail(20).mean()) if len(close) >= 20 else None
    ma60 = _clean_number(close.tail(60).mean()) if len(close) >= 60 else None
    trend_available = last_close is not None and ma5 is not None and ma20 is not None and ma60 is not None
    is_bullish_alignment = bool(trend_available and last_close > ma5 > ma20 > ma60)
    trend_component = (100.0 if is_bullish_alignment else 0.0) if trend_available else None

    alignment_gap = None
    if last_close is not None and ma60:
        alignment_gap = round(((last_close - ma60) / ma60) * 100, 2)

    momentum_60d = None
    if last_close is not None and len(close) >= 61:
        start_60 = _clean_number(close.iloc[-61])
        if start_60:
            momentum_60d = round(((last_close - start_60) / start_60) * 100, 2)

    momentum_120d = None
    if last_close is not None and len(close) >= 121:
        start_120 = _clean_number(close.iloc[-121])
        if start_120:
            momentum_120d = round(((last_close - start_120) / start_120) * 100, 2)

    volume_ratio_20d = None
    if not volume.empty and len(volume) >= 20:
        average_volume = _clean_number(volume.tail(20).mean())
        last_volume = _clean_number(volume.iloc[-1])
        if average_volume and last_volume is not None:
            volume_ratio_20d = round(last_volume / average_volume, 2)

    drawdown_1y = None
    if last_close is not None and len(close) >= 200:
        high_1y = _clean_number(close.tail(260).max())
        if high_1y:
            drawdown_1y = round(((last_close - high_1y) / high_1y) * 100, 2)

    info = snapshot.info
    pe = _clean_number(info.get("trailingPE") or info.get("forwardPE"))
    dividend_yield = _percent_metric(info, "dividendYield", "dividendYieldPercent")
    pbr = _clean_number(info.get("priceToBook"))
    peg = _clean_number(info.get("pegRatio"))
    fcf_yield = _percent(info.get("freeCashflowYield"))
    roe = _percent_metric(info, "returnOnEquity", "returnOnEquityPercent")
    gross_margin = _percent_metric(info, "grossMargins", "grossMarginsPercent")
    revenue_growth = _percent_metric(info, "revenueGrowth", "revenueGrowthPercent")
    eps_growth = _percent(info.get("earningsGrowth"))
    debt_to_equity = _clean_number(info.get("debtToEquity"))

    pe_component = _score_component(pe, 10, 60, inverse=True)
    pbr_component = _score_component(pbr, 1, 10, inverse=True)
    growth_value_component = _growth_value_component(peg, fcf_yield)
    roe_component = _score_component(roe, 5, 35)
    gross_margin_component = _score_component(gross_margin, 20, 70)
    revenue_component = _score_component(revenue_growth, -10, 40)
    eps_component = _score_component(eps_growth, -20, 60)
    debt_component = _score_component(debt_to_equity, 0, 150, inverse=True)
    momentum_60_component = _score_component(momentum_60d, -20, 40)
    momentum_120_component = _score_component(momentum_120d, -25, 60)
    volume_component = _score_component(volume_ratio_20d, 0.5, 2.2)
    drawdown_component = _score_component(drawdown_1y, -40, 0)

    value_parts = [
        (pe_component, 0.40),
        (pbr_component, 0.25),
        (growth_value_component, 0.35),
    ]
    quality_parts = [
        (roe_component, 0.25),
        (gross_margin_component, 0.20),
        (revenue_component, 0.20),
        (eps_component, 0.25),
        (debt_component, 0.10),
    ]
    momentum_parts = [
        (momentum_60_component, 0.30),
        (momentum_120_component, 0.20),
        (volume_component, 0.10),
        (drawdown_component, 0.15),
        (trend_component, 0.25),
    ]

    global_parts = [
        (pe_component, 0.15 * 0.40),
        (pbr_component, 0.15 * 0.25),
        (growth_value_component, 0.15 * 0.35),
        (roe_component, 0.40 * 0.25),
        (gross_margin_component, 0.40 * 0.20),
        (revenue_component, 0.40 * 0.20),
        (eps_component, 0.40 * 0.25),
        (debt_component, 0.40 * 0.10),
        (momentum_60_component, 0.45 * 0.30),
        (momentum_120_component, 0.45 * 0.20),
        (volume_component, 0.45 * 0.10),
        (drawdown_component, 0.45 * 0.15),
        (trend_component, 0.45 * 0.25),
    ]

    value_score = _weighted_score(value_parts)
    quality_growth_score = _weighted_score(quality_parts)
    momentum_score = _weighted_score(momentum_parts)
    total_score = _weighted_score(global_parts) or 0
    available_weight = sum(weight for component, weight in global_parts if component is not None)

    tags: list[str] = []
    if snapshot.stock.industry in PREFERRED_TECH_INDUSTRIES:
        tags.append("科技優先")
    if is_bullish_alignment:
        tags.append("多頭排列")
    if revenue_growth is not None and revenue_growth >= 20:
        tags.append("營收成長")
    if momentum_60d is not None and momentum_60d >= 15:
        tags.append("動能強")

    reasons: list[str] = []
    if snapshot.stock.industry in PREFERRED_TECH_INDUSTRIES:
        reasons.append("符合科技產業偏好")
    if quality_growth_score is not None and quality_growth_score >= 65:
        reasons.append("品質與成長表現強")
    if momentum_score is not None and momentum_score >= 65:
        reasons.append("中期股價動能強")
    if is_bullish_alignment:
        reasons.append("股價維持多頭排列")
    if revenue_growth is not None and revenue_growth >= 20:
        reasons.append("營收年增率突出")
    if value_score is not None and value_score >= 70:
        reasons.append("估值相對合理")
    reasons = reasons[:3] or ["依現有資料計算後綜合表現相對穩定"]

    risks: list[str] = []
    if revenue_growth is not None and revenue_growth < -10:
        risks.append("營收年增明顯衰退")
    if eps_growth is not None and eps_growth < -20:
        risks.append("EPS 年增明顯衰退")
    if pe is not None and pe <= 15 and (
        (revenue_growth is not None and revenue_growth < 0)
        or (eps_growth is not None and eps_growth < 0)
    ):
        risks.append("低 PE 可能反映景氣循環下行")
    if available_weight < 0.70:
        risks.append("可用資料偏少，分數不確定性較高")

    return ScreenerStock(
        symbol=snapshot.stock.symbol,
        name=snapshot.stock.name,
        market=snapshot.stock.market,
        industry=snapshot.stock.industry,
        currency=info.get("currency"),
        price=round(last_close, 2) if last_close is not None else None,
        change_percent=change_percent,
        change_3d_percent=change_3d_percent,
        pe=round(pe, 2) if pe is not None else None,
        dividend_yield=dividend_yield,
        pbr=round(pbr, 2) if pbr is not None else None,
        peg=round(peg, 2) if peg is not None else None,
        free_cashflow_yield=fcf_yield,
        roe=roe,
        gross_margin=gross_margin,
        revenue_growth_yoy=revenue_growth,
        eps_growth_yoy=eps_growth,
        debt_to_equity=round(debt_to_equity, 2) if debt_to_equity is not None else None,
        ma5=round(ma5, 2) if ma5 is not None else None,
        ma20=round(ma20, 2) if ma20 is not None else None,
        ma60=round(ma60, 2) if ma60 is not None else None,
        is_bullish_alignment=is_bullish_alignment,
        alignment_gap=alignment_gap,
        momentum_60d=momentum_60d,
        momentum_120d=momentum_120d,
        volume_ratio_20d=volume_ratio_20d,
        drawdown_1y=drawdown_1y,
        score=round(total_score, 1),
        value_score=round(value_score, 1) if value_score is not None else None,
        quality_growth_score=(
            round(quality_growth_score, 1) if quality_growth_score is not None else None
        ),
        momentum_score=round(momentum_score, 1) if momentum_score is not None else None,
        data_completeness=round(available_weight * 100, 1),
        ranking_reasons=reasons,
        risks=risks,
        tags=tags,
    )


def postprocess_rankings(stocks: list[ScreenerStock]) -> list[ScreenerStock]:
    industry_pe: dict[str, list[float]] = {}
    for stock in stocks:
        if stock.pe is not None and stock.pe > 0:
            industry_pe.setdefault(stock.industry, []).append(stock.pe)

    industry_medians = {
        industry: median(values)
        for industry, values in industry_pe.items()
        if len(values) >= 5
    }

    for stock in stocks:
        peer_pe = industry_medians.get(stock.industry)
        insufficient_growth = (
            (stock.revenue_growth_yoy is None or stock.revenue_growth_yoy < 15)
            and (stock.eps_growth_yoy is None or stock.eps_growth_yoy < 20)
        )
        if (
            stock.pe is not None
            and peer_pe is not None
            and stock.pe > max(40, peer_pe * 1.5)
            and insufficient_growth
        ):
            stock.risks.append("估值明顯高於同業，現有成長資料支撐不足")
        stock.risks = list(dict.fromkeys(stock.risks))[:3]

    return stocks
