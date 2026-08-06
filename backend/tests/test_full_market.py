from __future__ import annotations

import unittest
from unittest.mock import patch

import pandas as pd

from backend.app.factors import build_stock
from backend.app.models import UniverseStock
from backend.app.universe import load_full_taiwan_universe
from backend.app.yfinance_client import MarketSnapshot


class FullMarketUniverseTests(unittest.TestCase):
    @patch("backend.app.universe.fetch_json")
    def test_builds_listed_and_otc_yahoo_symbols(self, fetch_json_mock) -> None:
        fetch_json_mock.side_effect = [
            [
                {"公司代號": "2330", "公司簡稱": "台積電", "產業別": "24"},
                {"公司代號": "0050", "公司簡稱": "ETF", "產業別": ""},
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


if __name__ == "__main__":
    unittest.main()
