from __future__ import annotations

from .models import ScreenerFilters, ScreenerStock


def _passes_min(value: float | None, minimum: float) -> bool:
    return value is not None and value >= minimum


def _passes_max(value: float | None, maximum: float) -> bool:
    return value is not None and value <= maximum


def run_screener(stocks: list[ScreenerStock], filters: ScreenerFilters) -> list[ScreenerStock]:
    results = [
        stock
        for stock in stocks
        if (not filters.require_bullish_alignment or stock.is_bullish_alignment)
        and stock.score >= filters.min_score
        and _passes_max(stock.pe, filters.max_pe)
        and _passes_min(stock.roe, filters.min_roe)
        and _passes_min(stock.momentum_60d, filters.min_momentum_60d)
        and _passes_min(stock.volume_ratio_20d, filters.min_volume_ratio)
    ]
    return sorted(
        results,
        key=lambda stock: (
            stock.is_bullish_alignment,
            stock.score,
            stock.momentum_60d or -999,
            stock.alignment_gap or -999,
        ),
        reverse=True,
    )
