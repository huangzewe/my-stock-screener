from __future__ import annotations

import csv
from pathlib import Path

from .models import UniverseStock


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
