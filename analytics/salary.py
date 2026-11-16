"""Salary statistics from DOU IT salary surveys (basis='survey', DA5)."""

from __future__ import annotations

import math

import pandas as pd

from analytics.jobs import iter_jobs
from analytics.salary_records import load_salary_records

MIN_SAMPLE_SIZE = 30
_SURVEY_LANG_SET: frozenset[str] = frozenset(
    {
        "python",
        "javascript",
        "typescript",
        "java",
        "c#/.net",
        "c++",
        "c",
        "go",
        "php",
        "sql",
        "kotlin",
        "swift",
        "bash",
        "dart",
        "ruby",
        "rust",
        "scala",
        "1c/bas",
        "abap",
        "apex",
        "node.js",
        "terraform",
    }
)


def _compute_survey_histogram(values: pd.Series, max_bins: int = 8) -> list[dict[str, int]]:
    """Group USD salaries into tidy $500/$1000 buckets summing to len(values)."""
    if values.empty:
        return []
    low = int(max(0, (values.min() // 500) * 500))
    p98 = float(values.quantile(0.98))
    high_raw = max(p98, float(values.min()) + 500.0)
    raw_span = max(1000.0, high_raw - low)
    raw_step = raw_span / max_bins
    # Snap step to clean $500 increments.
    step = max(500, int(math.ceil(raw_step / 500.0) * 500))
    num_bins = max(1, min(max_bins, int(math.ceil((high_raw - low) / step))))

    buckets: list[dict[str, int]] = []
    for i in range(num_bins):
        b_from = low + i * step
        b_to = b_from + step
        if i == num_bins - 1:
            count = int((values >= b_from).sum())
        else:
            count = int(((values >= b_from) & (values < b_to)).sum())
        buckets.append({"from": int(b_from), "to": int(b_to), "count": count})
    return buckets


def _select_survey_cohort(
    df: pd.DataFrame,
    position: str,
    survey_langs: list[str],
    experience_years: float | None,
) -> tuple[pd.DataFrame, dict]:
    """Filter DOU survey records, widening automatically when sample size < 30."""
    pos_clean = position.strip() if position else ""
    has_pos = bool(pos_clean) and (df["position"] == pos_clean).any()
    has_langs = bool(survey_langs)
    has_exp = experience_years is not None

    def _filter(
        use_pos: bool,
        use_langs: bool,
        exp_half_width: float | None,
    ) -> pd.DataFrame:
        mask = pd.Series(True, index=df.index)
        if use_pos and pos_clean:
            mask &= df["position"] == pos_clean
        if use_langs and survey_langs:
            mask &= df["main_language"].isin(survey_langs)
        if exp_half_width is not None and experience_years is not None:
            lo = max(0.0, float(experience_years) - exp_half_width)
            hi = float(experience_years) + exp_half_width
            mask &= df["experience_years"].notna() & (df["experience_years"] >= lo) & (df["experience_years"] <= hi)
        return df.loc[mask]

    candidates: list[tuple[bool, bool, float | None, str]] = []
    if has_pos and has_langs and has_exp:
        candidates.append((True, True, 1.5, "exact"))
    if has_pos and has_exp:
        candidates.append((True, False, 1.5, "position+experience"))
        candidates.append((True, False, 3.0, "position+experience_wide"))
    if has_pos and has_langs:
        candidates.append((True, True, None, "position+skills"))
    if has_pos:
        candidates.append((True, False, None, "position"))
    if has_langs and has_exp:
        candidates.append((False, True, 2.0, "skills+experience"))
    if has_langs:
        candidates.append((False, True, None, "skills"))
    candidates.append((False, False, None, "all_survey"))

    chosen = df
    chosen_meta = (False, False, None, "all_survey")
    for use_pos, use_langs, exp_w, mode in candidates:
        sub = _filter(use_pos, use_langs, exp_w)
        if len(sub) >= MIN_SAMPLE_SIZE or mode == "all_survey":
            chosen = sub
            chosen_meta = (use_pos, use_langs, exp_w, mode)
            break

    used_pos, used_langs, used_exp_w, mode = chosen_meta
    filters = {
        "position": pos_clean if used_pos else None,
        "skills": list(survey_langs) if used_langs else [],
        "experience_years": float(experience_years) if (used_exp_w is not None and experience_years is not None) else None,
        "experience_window": used_exp_w,
        "mode": mode,
        "widened": mode not in {"exact", "position+experience", "position+skills", "position"} or (has_pos and not used_pos) or (has_langs and not used_langs) or (has_exp and used_exp_w is None),
    }
    return chosen, filters


def salary_stats(
    position: str,
    skills: list[str],
    experience_years: float | None = None,
) -> dict:
    """Compute SalaryStats strictly from normalized DOU salary surveys."""
    df = load_salary_records()
    survey_langs = [s.strip().lower() for s in (skills or []) if s and s.strip().lower() in _SURVEY_LANG_SET]

    cohort, filters = _select_survey_cohort(
        df=df,
        position=position or "",
        survey_langs=survey_langs,
        experience_years=experience_years,
    )
    salaries = cohort["salary_usd"].dropna().astype(float)
    if salaries.empty:
        salaries = df["salary_usd"].dropna().astype(float)

    return {
        "median": float(round(salaries.median(), 1)),
        "mean": float(round(salaries.mean(), 1)),
        "p25": float(round(salaries.quantile(0.25), 1)),
        "p75": float(round(salaries.quantile(0.75), 1)),
        "count": int(len(salaries)),
        "basis": "survey",
        "filters": filters,
        "histogram": _compute_survey_histogram(salaries),
    }


def vacancy_salary_stats(position: str, skills: list[str]) -> dict | None:
    """Auxiliary helper: compute SalaryStats from salaried active vacancies."""
    cats = [position] if position and position.strip() else None
    jobs = list(iter_jobs(categories=cats, skills=skills or None, require_salary=True))
    salaries = sorted(j["salary_mid"] for j in jobs if j["salary_mid"] is not None)
    if not salaries and cats:
        jobs = list(iter_jobs(categories=cats, require_salary=True))
        salaries = sorted(j["salary_mid"] for j in jobs if j["salary_mid"] is not None)
    if not salaries:
        return None

    n = len(salaries)
    median = float(salaries[n // 2] if n % 2 == 1 else (salaries[n // 2 - 1] + salaries[n // 2]) / 2)
    mean = round(sum(salaries) / n, 1)
    p25 = float(salaries[max(0, int(0.25 * (n - 1)))])
    p75 = float(salaries[min(n - 1, int(0.75 * (n - 1)))])
    hist = _compute_survey_histogram(pd.Series(salaries, dtype=float))

    return {
        "median": median,
        "mean": mean,
        "p25": p25,
        "p75": p75,
        "count": n,
        "basis": "vacancies",
        "filters": {"position": position, "skills": list(skills)},
        "histogram": hist,
    }
