from __future__ import annotations

import argparse
from pathlib import Path

from .official_daily import MAX_HISTORY_DAYS, write_history_store
from .universe import load_full_taiwan_universe, write_universe
from .yfinance_client import fetch_snapshots


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT = PROJECT_ROOT / "backend" / "data" / "taiwan_history.json"
UNIVERSE_OUTPUT = PROJECT_ROOT / "backend" / "config" / "taiwan_universe.csv"


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed the rolling Taiwan market history cache.")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    universe = load_full_taiwan_universe()
    write_universe(UNIVERSE_OUTPUT, universe)
    snapshots, failed = fetch_snapshots(universe)
    records = {}
    latest_dates: list[str] = []

    for snapshot in snapshots:
        history = snapshot.history.dropna(subset=["Close"]).tail(MAX_HISTORY_DAYS)
        dates = [timestamp.date().isoformat() for timestamp in history.index]
        if not dates:
            continue
        latest_dates.append(dates[-1])
        records[snapshot.stock.symbol] = {
            "dates": dates,
            "closes": [round(float(value), 4) for value in history["Close"]],
            "volumes": [
                round(float(value), 4) if value == value else 0
                for value in history.get("Volume", [0] * len(history))
            ],
        }

    payload = {
        "latest_market_date": max(latest_dates) if latest_dates else None,
        "stocks": {symbol: records[symbol] for symbol in sorted(records)},
    }
    write_history_store(args.output, payload)
    print(f"[ok] seeded {len(records)} stocks; failed={len(failed)}; output={args.output}")


if __name__ == "__main__":
    main()
