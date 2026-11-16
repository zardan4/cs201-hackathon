"""DA0 fixture-backed stub for skill upgrade recommendations (full DA6 pending)."""

from __future__ import annotations

import json
from pathlib import Path

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"


def recommend_upgrades(
    position: str,
    skills: list[str],
    top_n: int = 5,
) -> list[dict]:
    """Return top_n UpgradeSuggestion dicts (fixture stub until DA6)."""
    fixture_path = FIXTURES_DIR / "upgrade_suggestions.json"
    with fixture_path.open("r", encoding="utf-8") as fh:
        suggestions: list[dict] = json.load(fh)
    existing = {s.strip().lower() for s in skills}
    filtered = [item for item in suggestions if item["skill"].lower() not in existing]
    return filtered[:top_n]
