from __future__ import annotations

from .models import ScreenerFilters, ScreenerStock


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


def _passes_min(value: float | None, minimum: float, *, disabled_at: float) -> bool:
    if minimum <= disabled_at:
        return True
    if value is None:
        return False
    return value >= minimum


def _passes_max(value: float | None, maximum: float) -> bool:
    return value is None or maximum >= 999 or value <= maximum


def run_screener(stocks: list[ScreenerStock], filters: ScreenerFilters) -> list[ScreenerStock]:
    results = [
        stock
        for stock in stocks
        if (not filters.require_bullish_alignment or stock.is_bullish_alignment)
        and stock.score >= filters.min_score
        and _passes_max(stock.pe, filters.max_pe)
        and _passes_min(stock.roe, filters.min_roe, disabled_at=-100)
        and _passes_min(stock.momentum_60d, filters.min_momentum_60d, disabled_at=-100)
        and _passes_min(stock.volume_ratio_20d, filters.min_volume_ratio, disabled_at=0)
    ]
    return sorted(
        results,
        key=lambda stock: (
            stock.industry in PREFERRED_TECH_INDUSTRIES,
            stock.score,
            stock.quality_growth_score or -999,
            stock.momentum_score or -999,
            stock.data_completeness,
        ),
        reverse=True,
    )
