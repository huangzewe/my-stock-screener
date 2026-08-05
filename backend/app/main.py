from __future__ import annotations

import json
from pathlib import Path

from fastapi import FastAPI, HTTPException

from .models import ScreenerFilters, ScreenerPayload, ScreenerStock
from .screener import run_screener


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_PATH = PROJECT_ROOT / "backend" / "storage" / "screener-data.json"

app = FastAPI(title="Personal Stock Screener API", version="0.1.0")


def load_payload() -> ScreenerPayload:
    if not DATA_PATH.exists():
        raise HTTPException(status_code=404, detail="Screener data has not been generated yet.")
    return ScreenerPayload.model_validate(json.loads(DATA_PATH.read_text(encoding="utf-8")))


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/screener/results")
def get_results() -> ScreenerPayload:
    return load_payload()


@app.post("/api/screener/run")
def post_run_screener(filters: ScreenerFilters) -> ScreenerPayload:
    payload = load_payload()
    stocks = [ScreenerStock.model_validate(stock.model_dump()) for stock in payload.stocks]
    return ScreenerPayload(
        generated_at=payload.generated_at,
        source=payload.source,
        universe_size=payload.universe_size,
        filters=filters,
        stocks=run_screener(stocks, filters),
    )
