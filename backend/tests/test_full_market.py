from __future__ import annotations

import unittest
from datetime import date
from unittest.mock import patch

import pandas as pd

from backend.app.factors import build_stock
from backend.app.models import UniverseStock
from backend.app.official_daily import fetch_official_daily_quotes
from backend.app.universe import load_full_taiwan_universe
from backend.app.yfinance_client import MarketSnapshot, _filter_taiwan_trading_days


class FullMarketUniverseTests(unittest.TestCase):
    @patch("backend.app.universe.fetch_json")
    def test_builds_listed_and_otc_yahoo_symbols(self, fetch_json_mock) -> None:
        fetch_json_mock.side_effect = [
            [
                {"公司代號": "2330", "公司簡稱": "台積電", "產業別": "24"},
                {"公司代號": "0050", "公司簡稱": "ETF", "產業別": ""},
                {"公司代號": "1402", "公司簡稱": "遠東新", "產業別": "04"},
            ],
            [
                {
                    "SecuritiesCompanyCode": "6488",
                    "CompanyAbbreviation": "環球晶",
                    "SecuritiesIndustryCode": "24",
                }
            ],
        ]

        stocks = load_full_taiwan_universe()

        self.assertEqual([stock.symbol for stock in stocks], ["2330.TW", "6488.TWO"])
        self.assertEqual(stocks[0].industry, "半導體業")


class FactorCoverageTests(unittest.TestCase):
    def test_missing_quality_metrics_are_reweighted_instead_of_scored_as_zero(self) -> None:
        dates = pd.date_range("2026-01-01", periods=80, freq="B")
        history = pd.DataFrame(
            {
                "Close": [100 + index for index in range(80)],
                "Volume": [1_000_000 for _ in range(80)],
            },
            index=dates,
        )
        snapshot = MarketSnapshot(
            stock=UniverseStock(
                symbol="2330.TW",
                name="台積電",
                market="TW",
                industry="半導體業",
            ),
            history=history,
            info={"trailingPE": 20, "dividendYield": 2, "priceToBook": 5},
        )

        stock = build_stock(snapshot)

        self.assertIsNotNone(stock)
        assert stock is not None
        self.assertIsNone(stock.roe)
        self.assertGreater(stock.score, 50)
        self.assertLessEqual(stock.score, 100)
        self.assertIsNotNone(stock.value_score)
        self.assertIsNone(stock.quality_growth_score)
        self.assertEqual(stock.data_completeness, 39.0)
        self.assertIn("可用資料偏少，分數不確定性較高", stock.risks)


class TradingCalendarTests(unittest.TestCase):
    def test_phantom_holiday_quote_is_removed_before_moving_average(self) -> None:
        history = pd.DataFrame(
            {"Close": [100, 999, 101], "Volume": [10, 10, 10]},
            index=pd.to_datetime(["2026-07-09", "2026-07-10", "2026-07-13"]),
        )

        filtered = _filter_taiwan_trading_days(
            history,
            {date(2026, 7, 9), date(2026, 7, 13)},
        )

        self.assertEqual(filtered["Close"].tolist(), [100, 101])

    @patch("backend.app.official_daily.fetch_json")
    def test_bulk_official_quotes_cover_listed_and_otc_stocks(self, fetch_json_mock) -> None:
        fetch_json_mock.side_effect = [
            [
                {
                    "Date": "1150807",
                    "Code": "2330",
                    "ClosingPrice": "2,370.00",
                    "TradeVolume": "12,345",
                }
            ],
            [
                {
                    "Date": "1150807",
                    "SecuritiesCompanyCode": "6488",
                    "Close": "880.00",
                    "TradingShares": "6,789",
                }
            ],
        ]

        quotes = fetch_official_daily_quotes()

        self.assertEqual(quotes["2330.TW"], (date(2026, 8, 7), 2370.0, 12345.0))
        self.assertEqual(quotes["6488.TWO"], (date(2026, 8, 7), 880.0, 6789.0))


if __name__ == "__main__":
    unittest.main()
