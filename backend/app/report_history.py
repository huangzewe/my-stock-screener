from __future__ import annotations

import json
from pathlib import Path


def load_report_history(path: Path) -> list[dict]:
    if not path.exists():
        return []
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, json.JSONDecodeError):
        return []
    reports = payload.get("reports", []) if isinstance(payload, dict) else []
    return [report for report in reports if isinstance(report, dict)]


def has_report_for_date(reports: list[dict], report_date: str) -> bool:
    return any(report.get("report_date") == report_date for report in reports)


def calculate_notification_streaks(
    current_symbols: list[str],
    previous_reports: list[dict],
) -> dict[str, int]:
    """Count consecutive report appearances, including the current report."""
    streaks: dict[str, int] = {}
    for symbol in current_symbols:
        streak = 1
        for report in reversed(previous_reports):
            symbols = set(report.get("symbols", []))
            if symbol not in symbols:
                break
            streak += 1
        streaks[symbol] = streak
    return streaks


def calculate_first_selected_prices(
    current_prices: dict[str, float | None],
    previous_reports: list[dict],
) -> dict[str, float | None]:
    """Return the earliest recorded selection price for each current symbol."""
    known_prices: dict[str, float] = {}
    for report in previous_reports:
        stored_prices = report.get("first_selected_prices", {})
        if not isinstance(stored_prices, dict):
            continue
        for symbol, price in stored_prices.items():
            if symbol not in known_prices and isinstance(price, (int, float)):
                known_prices[symbol] = float(price)

    return {
        symbol: known_prices.get(symbol, price)
        for symbol, price in current_prices.items()
    }


def save_report_history(
    path: Path,
    previous_reports: list[dict],
    *,
    report_date: str,
    symbols: list[str],
    prices: dict[str, float | None] | None = None,
    keep: int = 30,
) -> None:
    first_selected_prices: dict[str, float] = {}
    for report in previous_reports:
        stored_prices = report.get("first_selected_prices", {})
        if isinstance(stored_prices, dict):
            for symbol, price in stored_prices.items():
                if symbol not in first_selected_prices and isinstance(price, (int, float)):
                    first_selected_prices[symbol] = float(price)
    for symbol, price in (prices or {}).items():
        if symbol not in first_selected_prices and isinstance(price, (int, float)):
            first_selected_prices[symbol] = float(price)

    reports = [report for report in previous_reports if report.get("report_date") != report_date]
    reports.append(
        {
            "report_date": report_date,
            "symbols": symbols,
            # Keep the cumulative registry in every new entry so the original
            # baseline survives report retention and temporary deselection.
            "first_selected_prices": first_selected_prices,
        }
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({"reports": reports[-keep:]}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
