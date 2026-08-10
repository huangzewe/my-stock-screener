from __future__ import annotations

import csv
import re
from pathlib import Path

from .models import UniverseStock
from .taiwan_open_data import (
    TPEX_COMPANIES_URL,
    TWSE_COMPANIES_URL,
    fetch_json,
    industry_name,
)


EXCLUDED_INDUSTRIES = frozenset(
    {
        "紡織纖維",
        "建材營造",
        "貿易百貨",
        "居家生活",
        "生技醫療業",
        "綠能環保",
        "橡膠工業",
        "金融保險",
        "運動休閒",
    }
)


def load_universe(path: Path) -> list[UniverseStock]:
    with path.open("r", encoding="utf-8-sig", newline="") as file:
        rows = csv.DictReader(file)
        return [
            UniverseStock(
                symbol=(row.get("symbol") or "").strip(),
                name=(row.get("name") or "").strip(),
                market=(row.get("market") or "OTHER").strip() or "OTHER",
                industry=(row.get("industry") or "Unknown").strip() or "Unknown",
            )
            for row in rows
            if (row.get("symbol") or "").strip()
        ]


def _valid_common_stock_code(value: object) -> bool:
    # Company master data only contains companies; a four-digit numeric code
    # excludes ETFs, ETNs, warrants and other exchange-traded products.
    code = str(value or "").strip()
    return bool(re.fullmatch(r"\d{4}", code)) and not code.startswith("0")


def load_full_taiwan_universe() -> list[UniverseStock]:
    """Build the complete listed and OTC company universe from official data."""
    stocks: list[UniverseStock] = []

    for row in fetch_json(TWSE_COMPANIES_URL):
        code = str(row.get("公司代號") or "").strip()
        if not _valid_common_stock_code(code):
            continue
        industry = industry_name(row.get("產業別"))
        if industry in EXCLUDED_INDUSTRIES:
            continue
        stocks.append(
            UniverseStock(
                symbol=f"{code}.TW",
                name=str(row.get("公司簡稱") or row.get("公司名稱") or code).strip(),
                market="TW",
                industry=industry,
            )
        )

    for row in fetch_json(TPEX_COMPANIES_URL):
        code = str(row.get("SecuritiesCompanyCode") or "").strip()
        if not _valid_common_stock_code(code):
            continue
        industry = industry_name(row.get("SecuritiesIndustryCode"))
        if industry in EXCLUDED_INDUSTRIES:
            continue
        stocks.append(
            UniverseStock(
                symbol=f"{code}.TWO",
                name=str(row.get("CompanyAbbreviation") or row.get("CompanyName") or code).strip(),
                market="TWO",
                industry=industry,
            )
        )

    unique = {stock.symbol: stock for stock in stocks}
    return sorted(unique.values(), key=lambda stock: (stock.market, stock.symbol))


def write_universe(path: Path, stocks: list[UniverseStock]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=["symbol", "name", "market", "industry"])
        writer.writeheader()
        for stock in stocks:
            writer.writerow(stock.model_dump())
