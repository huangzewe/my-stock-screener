from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from backend.app.report_history import (
    calculate_notification_streaks,
    load_report_history,
    save_report_history,
)


class ReportHistoryTests(unittest.TestCase):
    def test_streak_requires_presence_in_each_previous_report(self):
        reports = [
            {"report_date": "2026-08-10", "symbols": ["2330.TW", "2454.TW"]},
            {"report_date": "2026-08-11", "symbols": ["2330.TW"]},
            {"report_date": "2026-08-12", "symbols": ["2330.TW", "2454.TW"]},
        ]

        streaks = calculate_notification_streaks(["2330.TW", "2454.TW"], reports)

        self.assertEqual(streaks["2330.TW"], 4)
        self.assertEqual(streaks["2454.TW"], 2)

    def test_same_report_date_is_replaced(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "history.json"
            save_report_history(path, [], report_date="2026-08-13", symbols=["2330.TW"])
            reports = load_report_history(path)
            save_report_history(
                path,
                reports,
                report_date="2026-08-13",
                symbols=["2454.TW"],
            )

            updated = load_report_history(path)
            self.assertEqual(len(updated), 1)
            self.assertEqual(updated[0]["symbols"], ["2454.TW"])


if __name__ == "__main__":
    unittest.main()
