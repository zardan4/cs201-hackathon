"""DA0 fixture-backed stub for DOU salary records (full DA3 loader pending)."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"


def load_salary_records() -> pd.DataFrame:
    """Return normalized salary survey records (fixture stub until DA3)."""
    fixture_path = FIXTURES_DIR / "salary_records.json"
    with fixture_path.open("r", encoding="utf-8") as fh:
        rows = json.load(fh)
    return pd.DataFrame(rows)
