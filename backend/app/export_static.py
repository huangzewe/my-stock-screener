from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from .factors import build_stock
from .models import ScreenerFilters, ScreenerPayload
from .screener import run_screener
from .universe import load_universe
from .yfinance_client import fetch_snapshot


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_UNIVERSE = PROJECT_ROOT / "backend" / "config" / "watchlist.sample.csv"
BACKEND_OUTPUT = PROJECT_ROOT / "backend" / "storage" / "screener-data.json"
FRONTEND_OUTPUT = PROJECT_ROOT / "public" / "data" / "screener-data.json"


def generate_payload(universe_path: Path, filters: ScreenerFilters) -> ScreenerPayload:
    universe = load_universe(universe_path)
    stocks = []

    for stock in universe:
        try:
            screener_stock = build_stock(fetch_snapshot(stock))
        except Exception as error:
            print(f"[warn] skip {stock.symbol}: {error}")
            continue
        if screener_stock:
            stocks.append(screener_stock)

    results = run_screener(stocks, filters)
    return ScreenerPayload(
        generated_at=datetime.now(timezone.utc),
        source="yfinance",
        universe_size=len(universe),
        filters=filters,
        stocks=results,
    )


def write_payload(payload: ScreenerPayload, paths: list[Path]) -> None:
    encoded = json.dumps(payload.model_dump(mode="json"), ensure_ascii=False, indent=2)
    for path in paths:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(encoded + "\n", encoding="utf-8")
        print(f"[ok] wrote {path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate stock screener data with yfinance.")
    parser.add_argument("--universe", type=Path, default=DEFAULT_UNIVERSE)
    parser.add_argument("--min-score", type=float, default=55)
    parser.add_argument("--max-pe", type=float, default=60)
    parser.add_argument("--min-roe", type=float, default=-100)
    parser.add_argument("--min-momentum-60d", type=float, default=-100)
    parser.add_argument("--min-volume-ratio", type=float, default=0)
    parser.add_argument("--include-non-bullish", action="store_true")
    args = parser.parse_args()

    filters = ScreenerFilters(
        require_bullish_alignment=not args.include_non_bullish,
        min_score=args.min_score,
        max_pe=args.max_pe,
        min_roe=args.min_roe,
        min_momentum_60d=args.min_momentum_60d,
        min_volume_ratio=args.min_volume_ratio,
    )
    payload = generate_payload(args.universe, filters)
    write_payload(payload, [BACKEND_OUTPUT, FRONTEND_OUTPUT])


if __name__ == "__main__":
    main()
