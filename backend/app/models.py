from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


Market = Literal["US", "TW", "TWO", "ETF", "OTHER"]


class UniverseStock(BaseModel):
    symbol: str
    name: str
    market: Market = "OTHER"
    industry: str = "Unknown"


class ScreenerFilters(BaseModel):
    require_bullish_alignment: bool = True
    min_score: float = Field(default=55, ge=0, le=100)
    max_pe: float = Field(default=60, ge=0)
    min_roe: float = Field(default=-100)
    min_revenue_growth: float = Field(default=-100)
    min_momentum_60d: float = Field(default=-100)
    min_volume_ratio: float = Field(default=0)


class ScreenerStock(BaseModel):
    symbol: str
    name: str
    market: Market
    industry: str
    currency: str | None = None
    price: float | None = None
    change_percent: float | None = None
    pe: float | None = None
    dividend_yield: float | None = None
    pbr: float | None = None
    roe: float | None = None
    gross_margin: float | None = None
    debt_to_equity: float | None = None
    ma5: float | None = None
    ma20: float | None = None
    ma60: float | None = None
    is_bullish_alignment: bool = False
    alignment_gap: float | None = None
    momentum_60d: float | None = None
    volume_ratio_20d: float | None = None
    drawdown_1y: float | None = None
    score: float
    tags: list[str] = Field(default_factory=list)


class ScreenerPayload(BaseModel):
    generated_at: datetime
    source: str
    universe_size: int
    processed_size: int = 0
    failed_size: int = 0
    filters: ScreenerFilters
    stocks: list[ScreenerStock]
