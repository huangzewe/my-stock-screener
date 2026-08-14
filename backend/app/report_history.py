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


def save_report_history(
    path: Path,
    previous_reports: list[dict],
    *,
    report_date: str,
    symbols: list[str],
    keep: int = 30,
) -> None:
    reports = [report for report in previous_reports if report.get("report_date") != report_date]
    reports.append({"report_date": report_date, "symbols": symbols})
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({"reports": reports[-keep:]}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
