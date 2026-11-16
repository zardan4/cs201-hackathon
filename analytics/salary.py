"""DA0 stub for survey salary stats + live vacancy salary stats helper."""

from __future__ import annotations

import json
from pathlib import Path

from analytics.jobs import iter_jobs

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"


def _compute_histogram(values: list[int], bins: int = 6) -> list[dict]:
    if not values:
        return []
    low, high = min(values), max(values)
    if low == high:
        return [{"from": low, "to": high, "count": len(values)}]
    step = max(250, ((high - low) // bins // 100 + 1) * 100)
    start = (low // 100) * 100
    buckets: list[dict] = []
    cur = start
    while cur <= high:
        nxt = cur + step
        count = sum(1 for v in values if cur <= v < nxt)
        if count > 0 or buckets:
            buckets.append({"from": cur, "to": nxt, "count": count})
        cur = nxt
    return buckets


def salary_stats(
    position: str,
    skills: list[str],
    experience_years: float | None = None,
) -> dict:
    """Return SalaryStats dict from DA0 fixture (full DA5 survey implementation pending)."""
    fixture_path = FIXTURES_DIR / "salary_stats.json"
    with fixture_path.open("r", encoding="utf-8") as fh:
        data = json.load(fh)
    data["filters"] = {
        "position": position,
        "skills": list(skills),
        "experience_years": experience_years,
        "stub": True,
    }
    return data


def vacancy_salary_stats(position: str, skills: list[str]) -> dict | None:
    """Compute SalaryStats from active DOU vacancies with valid monthly salaries."""
    cats = [position] if position and position.strip() else None
    jobs = list(iter_jobs(categories=cats, skills=skills or None))
    salaries = sorted(j["salary_mid"] for j in jobs if j["salary_mid"] is not None)
    if not salaries and cats:
        jobs = list(iter_jobs(categories=cats))
        salaries = sorted(j["salary_mid"] for j in jobs if j["salary_mid"] is not None)
    if not salaries:
        return None

    n = len(salaries)
    median = float(salaries[n // 2] if n % 2 == 1 else (salaries[n // 2 - 1] + salaries[n // 2]) / 2)
    mean = round(sum(salaries) / n, 1)
    p25 = float(salaries[max(0, int(0.25 * (n - 1)))])
    p75 = float(salaries[min(n - 1, int(0.75 * (n - 1)))])

    return {
        "median": median,
        "mean": mean,
        "p25": p25,
        "p75": p75,
        "count": n,
        "basis": "vacancies",
        "filters": {"position": position, "skills": list(skills)},
        "histogram": _compute_histogram(salaries),
    }
