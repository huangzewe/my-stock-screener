from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from .factors import build_stock, postprocess_rankings
from .models import ScreenerFilters, ScreenerPayload
from .official_daily import snapshots_from_history, update_history_store
from .screener import run_screener
from .universe import load_full_taiwan_universe, load_universe, write_universe
from .yfinance_client import fetch_snapshots


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_UNIVERSE = PROJECT_ROOT / "backend" / "config" / "watchlist.sample.csv"
FULL_TAIWAN_UNIVERSE = PROJECT_ROOT / "backend" / "config" / "taiwan_universe.csv"
TAIWAN_HISTORY = PROJECT_ROOT / "backend" / "data" / "taiwan_history.json"
BACKEND_OUTPUT = PROJECT_ROOT / "backend" / "storage" / "screener-data.json"
FRONTEND_OUTPUT = PROJECT_ROOT / "public" / "data" / "screener-data.json"


def generate_payload(
    universe_path: Path | None,
    filters: ScreenerFilters,
    *,
    full_taiwan_market: bool = False,
    official_daily: bool = False,
) -> ScreenerPayload:
    if full_taiwan_market:
        universe = load_full_taiwan_universe()
        write_universe(FULL_TAIWAN_UNIVERSE, universe)
    elif universe_path is not None:
        universe = load_universe(universe_path)
    else:
        universe = load_universe(DEFAULT_UNIVERSE)

    stocks = []

    if official_daily:
        history_payload, latest_market_date = update_history_store(TAIWAN_HISTORY, universe)
        snapshots, failed_symbols = snapshots_from_history(universe, history_payload)
        print(f"[ok] official market history updated through {latest_market_date}")
    else:
        snapshots, failed_symbols = fetch_snapshots(universe)
    for snapshot in snapshots:
        try:
            screener_stock = build_stock(snapshot)
        except Exception as error:
            print(f"[warn] skip {snapshot.stock.symbol}: {error}")
            failed_symbols.append(snapshot.stock.symbol)
            continue
        if screener_stock:
            stocks.append(screener_stock)

    stocks = postprocess_rankings(stocks)

    results = run_screener(stocks, filters)
    return ScreenerPayload(
        generated_at=datetime.now(timezone.utc),
        source=(
            "TWSE/TPEx official daily"
            if official_daily
            else "TWSE/TPEx + yfinance"
            if full_taiwan_market
            else "yfinance"
        ),
        universe_size=len(universe),
        processed_size=len(stocks),
        failed_size=len(set(failed_symbols)),
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
    parser.add_argument(
        "--full-taiwan-market",
        action="store_true",
        help="Refresh and scan every TWSE and TPEx company.",
    )
    parser.add_argument(
        "--official-daily",
        action="store_true",
        help="Update from the exchanges' bulk daily quotes and the rolling history cache.",
    )
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
    payload = generate_payload(
        args.universe,
        filters,
        full_taiwan_market=args.full_taiwan_market,
        official_daily=args.official_daily,
    )
    write_payload(payload, [BACKEND_OUTPUT, FRONTEND_OUTPUT])


if __name__ == "__main__":
    main()
