from __future__ import annotations

import argparse
from pathlib import Path

from .universe import load_full_taiwan_universe, write_universe


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT = PROJECT_ROOT / "backend" / "config" / "taiwan_universe.csv"


def main() -> None:
    parser = argparse.ArgumentParser(description="Refresh the complete TWSE and TPEx stock universe.")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    stocks = load_full_taiwan_universe()
    write_universe(args.output, stocks)
    listed = sum(stock.market == "TW" for stock in stocks)
    otc = sum(stock.market == "TWO" for stock in stocks)
    print(f"[ok] wrote {len(stocks)} stocks ({listed} listed, {otc} OTC) to {args.output}")


if __name__ == "__main__":
    main()
