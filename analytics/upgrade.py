"""Recommend high-ROI missing skills using DOU salary surveys and salaried vacancies (DA6)."""

from __future__ import annotations

import pandas as pd

from analytics.jobs import iter_jobs
from analytics.matching import score_job
from analytics.salary import MIN_SAMPLE_SIZE, salary_stats
from analytics.salary_records import load_salary_records
from analytics.skills import all_skills

UNLOCK_SCORE_THRESHOLD = 0.65

# Management/title entries should not crowd out concrete technical skills.
_TITLE_LIKE_SKILLS: frozenset[str] = frozenset(
    {
        "architecture",
        "engineering management",
        "product management",
        "project management",
    }
)

# Maps non-language skills onto DOU survey cohorts (cohort_key, filter kind & value).
_SKILL_COHORT_MAP: dict[str, tuple[str, str, object]] = {
    "devops": ("cohort:devops", "position", "DevOps"),
    "kubernetes": ("cohort:devops", "position", "DevOps"),
    "docker": ("cohort:devops", "position", "DevOps"),
    "aws": ("cohort:devops", "position", "DevOps"),
    "azure": ("cohort:devops", "position", "DevOps"),
    "gcp": ("cohort:devops", "position", "DevOps"),
    "ci/cd": ("cohort:devops", "position", "DevOps"),
    "ansible": ("cohort:devops", "position", "DevOps"),
    "data engineering": ("cohort:data_eng", "position", "Data Engineer"),
    "spark": ("cohort:data_eng", "position", "Data Engineer"),
    "airflow": ("cohort:data_eng", "position", "Data Engineer"),
    "kafka": ("cohort:data_eng", "position", "Data Engineer"),
    "snowflake": ("cohort:data_eng", "position", "Data Engineer"),
    "big data": ("cohort:data_eng", "position", "Data Engineer"),
    "ai/ml": ("cohort:aiml", "positions", ("AI/ML", "Data Science")),
    "llm": ("cohort:aiml", "positions", ("AI/ML", "Data Science")),
    "pytorch": ("cohort:aiml", "positions", ("AI/ML", "Data Science")),
    "tensorflow": ("cohort:aiml", "positions", ("AI/ML", "Data Science")),
    "langchain": ("cohort:aiml", "positions", ("AI/ML", "Data Science")),
    "nlp": ("cohort:aiml", "positions", ("AI/ML", "Data Science")),
    "computer vision": ("cohort:aiml", "positions", ("AI/ML", "Data Science")),
    "data science": ("cohort:ds", "position", "Data Science"),
    "automation qa": ("cohort:aqa", "aqa", None),
    "playwright": ("cohort:aqa", "aqa", None),
    "selenium": ("cohort:aqa", "aqa", None),
    "cybersecurity": ("cohort:security", "position", "Security"),
    "embedded": ("cohort:embedded", "position", "Embedded"),
    "firmware": ("cohort:embedded", "position", "Embedded"),
    "fpga": ("cohort:embedded", "position", "Embedded"),
    "scrum/agile": ("cohort:scrum", "position", "Scrum Master"),
    "dba": ("cohort:dba", "position", "DBA"),
    "data analysis": ("cohort:analyst", "position", "Analyst"),
    "power bi": ("cohort:analyst", "position", "Analyst"),
    "tableau": ("cohort:analyst", "position", "Analyst"),
    "react": ("cohort:frontend", "spec", "Front-end розробка"),
    "angular": ("cohort:frontend", "spec", "Front-end розробка"),
    "vue": ("cohort:frontend", "spec", "Front-end розробка"),
    "django": ("cohort:lang:python", "language", "python"),
    "fastapi": ("cohort:lang:python", "language", "python"),
    "flask": ("cohort:lang:python", "language", "python"),
    "spring": ("cohort:lang:java", "language", "java"),
    "laravel": ("cohort:lang:php", "language", "php"),
}


def _survey_cohort_for_skill(
    df: pd.DataFrame,
    position: str,
    skill: str,
) -> tuple[str, pd.Series, bool] | None:
    """Return (cohort_key, salary_usd Series, is_within_position) if sample_size >= 30."""
    pos_clean = position.strip() if position else ""
    if pos_clean:
        pos_df = df[df["position"] == pos_clean]
        if skill in {"automation qa", "playwright", "selenium"} and pos_clean == "QA":
            in_pos_aqa = pos_df.loc[pos_df["main_language"].notna(), "salary_usd"]
            if len(in_pos_aqa) >= MIN_SAMPLE_SIZE:
                return f"pos:{pos_clean}:aqa", in_pos_aqa, True
        in_pos_lang = pos_df.loc[pos_df["main_language"] == skill, "salary_usd"]
        if len(in_pos_lang) >= MIN_SAMPLE_SIZE:
            return f"pos:{pos_clean}:lang:{skill}", in_pos_lang, True

    direct = df.loc[df["main_language"] == skill, "salary_usd"]
    if len(direct) >= MIN_SAMPLE_SIZE:
        return f"cohort:lang:{skill}", direct, False

    mapping = _SKILL_COHORT_MAP.get(skill)
    if mapping is None:
        return None
    cohort_key, kind, val = mapping
    if kind == "language":
        series = df.loc[df["main_language"] == val, "salary_usd"]
    elif kind == "position":
        series = df.loc[df["position"] == val, "salary_usd"]
    elif kind == "positions":
        series = df.loc[df["position"].isin(val), "salary_usd"]
    elif kind == "spec":
        series = df.loc[df["specialization"] == val, "salary_usd"]
    elif kind == "aqa":
        series = df.loc[(df["position"] == "QA") & df["main_language"].notna(), "salary_usd"]
    else:
        return None

    if len(series) < MIN_SAMPLE_SIZE:
        return None
    return cohort_key, series, False


def _unlocked_jobs_for_skill(
    salaried_jobs: list[dict],
    base_scores: dict[str, float],
    position: str,
    user_skills: set[str],
    skill: str,
) -> tuple[int, list[str]]:
    """Count salaried jobs whose score crosses UNLOCK_SCORE_THRESHOLD when adding skill."""
    expanded_skills = user_skills | {skill}
    unlocked_ids: list[str] = []
    for job in salaried_jobs:
        if skill not in job["skills"]:
            continue
        if base_scores[job["id"]] >= UNLOCK_SCORE_THRESHOLD:
            continue
        new_score, _, _, _ = score_job(job, position=position, user_skills=expanded_skills)
        if new_score >= UNLOCK_SCORE_THRESHOLD:
            unlocked_ids.append(job["id"])
    return len(unlocked_ids), unlocked_ids[:3]


def recommend_upgrades(
    position: str,
    skills: list[str],
    top_n: int = 5,
) -> list[dict]:
    """Recommend top_n missing skills ranked by DOU survey salary gain and unlocked jobs."""
    if top_n <= 0:
        return []

    user_skills = {s.strip().lower() for s in (skills or []) if s and s.strip()}
    baseline = salary_stats(position=position or "", skills=list(user_skills), experience_years=None)
    base_median = float(baseline["median"]) if baseline["median"] > 0 else 1.0

    survey_df = load_salary_records()
    salaried_jobs = list(iter_jobs(require_salary=True))
    base_scores = {
        job["id"]: score_job(job, position=position or "", user_skills=user_skills)[0]
        for job in salaried_jobs
    }

    positive_by_cohort: dict[str, tuple[bool, dict]] = {}
    fallback_by_cohort: dict[str, dict] = {}

    for entry in all_skills():
        skill = entry["name"].lower()
        if skill in user_skills or skill in _TITLE_LIKE_SKILLS:
            continue

        cohort_res = _survey_cohort_for_skill(survey_df, position or "", skill)
        if cohort_res is None:
            continue
        cohort_key, series, is_within_pos = cohort_res

        cohort_median = float(series.median())
        gain_usd = round(cohort_median - base_median, 1)
        new_jobs_count, example_ids = _unlocked_jobs_for_skill(
            salaried_jobs=salaried_jobs,
            base_scores=base_scores,
            position=position or "",
            user_skills=user_skills,
            skill=skill,
        )
        suggestion = {
            "skill": skill,
            "salary_gain_usd": gain_usd,
            "salary_gain_pct": round((gain_usd / base_median) * 100.0, 1),
            "new_jobs_count": new_jobs_count,
            "example_job_ids": example_ids,
            "sample_size": int(len(series)),
        }

        if gain_usd > 0:
            prev_pair = positive_by_cohort.get(cohort_key)
            cur_rank = (is_within_pos, new_jobs_count, gain_usd)
            if prev_pair is None:
                positive_by_cohort[cohort_key] = (is_within_pos, suggestion)
            else:
                prev_within, prev = prev_pair
                prev_rank = (prev_within, prev["new_jobs_count"], prev["salary_gain_usd"])
                if cur_rank > prev_rank:
                    positive_by_cohort[cohort_key] = (is_within_pos, suggestion)
        else:
            prev_fb = fallback_by_cohort.get(cohort_key)
            if prev_fb is None or (new_jobs_count, gain_usd) > (prev_fb["new_jobs_count"], prev_fb["salary_gain_usd"]):
                fallback_by_cohort[cohort_key] = suggestion

    ranked_positive = [
        item
        for _, item in sorted(
            positive_by_cohort.values(),
            key=lambda pair: (
                pair[0],  # within-position upgrades first
                pair[1]["new_jobs_count"] > 0,
                pair[1]["salary_gain_usd"] + 40.0 * pair[1]["new_jobs_count"],
                pair[1]["salary_gain_usd"],
            ),
            reverse=True,
        )
    ]

    if len(ranked_positive) >= top_n:
        return ranked_positive[:top_n]

    seen_skills = {item["skill"] for item in ranked_positive}
    fallback_items: list[dict] = []
    for item in fallback_by_cohort.values():
        if item["skill"] in seen_skills:
            continue
        fallback_items.append(
            {
                **item,
                "salary_gain_usd": max(0.0, item["salary_gain_usd"]),
                "salary_gain_pct": max(0.0, item["salary_gain_pct"]),
            }
        )
    fallback_sorted = sorted(
        fallback_items,
        key=lambda item: (item["new_jobs_count"], item["salary_gain_usd"], item["sample_size"]),
        reverse=True,
    )
    return (ranked_positive + fallback_sorted)[:top_n]
