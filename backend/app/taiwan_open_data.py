from __future__ import annotations

import json
import time
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


TWSE_COMPANIES_URL = "https://openapi.twse.com.tw/v1/opendata/t187ap03_L"
TPEX_COMPANIES_URL = "https://www.tpex.org.tw/openapi/v1/mopsfin_t187ap03_O"
TWSE_VALUATIONS_URL = "https://openapi.twse.com.tw/v1/exchangeReport/BWIBBU_ALL"
TPEX_VALUATIONS_URL = "https://www.tpex.org.tw/openapi/v1/tpex_mainboard_peratio_analysis"


# Official industry codes shared by the TWSE and TPEx company datasets.
INDUSTRY_NAMES = {
    "01": "水泥工業",
    "02": "食品工業",
    "03": "塑膠工業",
    "04": "紡織纖維",
    "05": "電機機械",
    "06": "電器電纜",
    "07": "化學生技醫療",
    "08": "玻璃陶瓷",
    "09": "造紙工業",
    "10": "鋼鐵工業",
    "11": "橡膠工業",
    "12": "汽車工業",
    "14": "建材營造",
    "15": "航運業",
    "16": "觀光餐旅",
    "17": "金融保險",
    "18": "貿易百貨",
    "19": "綜合企業",
    "20": "其他",
    "21": "化學工業",
    "22": "生技醫療業",
    "23": "油電燃氣業",
    "24": "半導體業",
    "25": "電腦及週邊設備業",
    "26": "光電業",
    "27": "通信網路業",
    "28": "電子零組件業",
    "29": "電子通路業",
    "30": "資訊服務業",
    "31": "其他電子業",
    "32": "文化創意業",
    "33": "農業科技業",
    "34": "電子商務",
    "35": "綠能環保",
    "36": "數位雲端",
    "37": "運動休閒",
    "38": "居家生活",
}


def fetch_json(url: str, *, timeout: int = 60, attempts: int = 3) -> list[dict[str, Any]]:
    """Download a public market dataset with bounded retries."""
    last_error: Exception | None = None
    for attempt in range(attempts):
        try:
            request = Request(
                url,
                headers={
                    "Accept": "application/json",
                    "User-Agent": "taiwan-market-screener/1.0",
                },
            )
            with urlopen(request, timeout=timeout) as response:
                payload = json.load(response)
            if not isinstance(payload, list):
                raise ValueError(f"Expected a JSON list from {url}")
            return payload
        except (HTTPError, URLError, TimeoutError, ValueError, json.JSONDecodeError) as error:
            last_error = error
            if attempt + 1 < attempts:
                time.sleep(2**attempt)
    raise RuntimeError(f"Unable to download {url}: {last_error}") from last_error


def clean_number(value: object) -> float | None:
    if value is None:
        return None
    text = str(value).strip().replace(",", "")
    if not text or text in {"-", "--", "N/A"}:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def industry_name(code: object) -> str:
    normalized = str(code or "").strip().zfill(2)
    return INDUSTRY_NAMES.get(normalized, f"產業代碼 {normalized}" if normalized else "其他")


def fetch_taiwan_valuations() -> dict[str, dict[str, float | None]]:
    """Return current PE, dividend yield and PBR keyed by Yahoo symbol."""
    valuations: dict[str, dict[str, float | None]] = {}

    for row in fetch_json(TWSE_VALUATIONS_URL):
        code = str(row.get("Code") or "").strip()
        if code:
            valuations[f"{code}.TW"] = {
                "trailingPE": clean_number(row.get("PEratio")),
                "dividendYield": clean_number(row.get("DividendYield")),
                "priceToBook": clean_number(row.get("PBratio")),
            }

    for row in fetch_json(TPEX_VALUATIONS_URL):
        code = str(row.get("SecuritiesCompanyCode") or "").strip()
        if code:
            valuations[f"{code}.TWO"] = {
                "trailingPE": clean_number(row.get("PriceEarningRatio")),
                "dividendYield": clean_number(row.get("YieldRatio")),
                "priceToBook": clean_number(row.get("PriceBookRatio")),
            }

    return valuations
