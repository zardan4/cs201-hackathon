"""Score, rank, and yield matching vacancies from best to worst."""

from __future__ import annotations

from itertools import islice
from pathlib import Path
from typing import Iterable, Iterator

from analytics.config import SWIPE_REQUIRES_SALARY
from analytics.jobs import DEFAULT_CACHE_PATH, DEFAULT_CSV_PATH, iter_jobs

_SKILL_WEIGHT = 0.8
_CATEGORY_WEIGHT = 0.2
_TAG_BONUS = 0.05


def _build_reason(
    matched_skills: list[str],
    total_job_skills: int,
    matched_category: str | None,
    is_remote: bool,
) -> str:
    if matched_skills:
        preview = ", ".join(matched_skills[:3])
        if len(matched_skills) > 3:
            preview = f"{preview} +{len(matched_skills) - 3}"
        return f"{preview} · {len(matched_skills)} з {total_job_skills} навичок"
    if matched_category:
        suffix = " · віддалено" if is_remote else ""
        return f"Категорія: {matched_category}{suffix}"
    return "Віддалено" if is_remote else "Підходить за фільтрами"


def score_job(
    job: dict,
    position: str = "",
    user_skills: set[str] = frozenset(),
    target_categories: set[str] = frozenset(),
    target_tags: set[str] = frozenset(),
) -> tuple[float, list[str], list[str], str]:
    """Compute match score (0..1), matched/missing skills, and reason for one job."""
    job_skills = list(job.get("skills") or [])
    job_skill_set = {s.lower() for s in job_skills}

    matched_skills = [s for s in job_skills if s.lower() in user_skills]
    missing_skills = [s for s in job_skills if s.lower() not in user_skills]

    skill_score = (len(matched_skills) / len(job_skill_set)) if job_skill_set else 0.0

    wanted_cats = set(target_categories)
    if position and position.strip():
        wanted_cats.add(position.strip().lower())

    matched_category: str | None = None
    for cat in job.get("categories") or []:
        if cat.lower() in wanted_cats:
            matched_category = cat
            break

    category_bonus = _CATEGORY_WEIGHT if matched_category is not None else 0.0
    job_tags = {t.lower() for t in (job.get("tags") or [])}
    tag_bonus = _TAG_BONUS if (target_tags and (job_tags & target_tags)) else 0.0

    score = round(min(1.0, _SKILL_WEIGHT * skill_score + category_bonus + tag_bonus), 4)
    reason = _build_reason(
        matched_skills=matched_skills,
        total_job_skills=len(job_skill_set),
        matched_category=matched_category,
        is_remote=bool(job.get("is_remote")),
    )
    return score, matched_skills, missing_skills, reason


def iter_ranked_jobs(
    position: str = "",
    skills: Iterable[str] = (),
    exclude_ids: set[str] | None = None,
    *,
    categories: list[str] | None = None,
    locations: list[str] | None = None,
    remote_only: bool = False,
    min_salary: int | None = None,
    tags: list[str] | None = None,
    min_score: float = 0.0,
    require_salary: bool | None = None,
    csv_path: Path = DEFAULT_CSV_PATH,
    cache_path: Path = DEFAULT_CACHE_PATH,
) -> Iterator[dict]:
    """Filter vacancies and yield JobMatch dicts ordered from best match to worst."""
    user_skills = {s.strip().lower() for s in skills if s and s.strip()}
    target_categories = {c.strip().lower() for c in categories if c and c.strip()} if categories else set()
    target_tags = {t.strip().lower() for t in tags if t and t.strip()} if tags else set()
    salaried_only = SWIPE_REQUIRES_SALARY if require_salary is None else require_salary

    candidates = iter_jobs(
        categories=categories,
        locations=locations,
        remote_only=remote_only,
        exclude_ids=exclude_ids,
        min_salary=min_salary,
        tags=tags,
        require_salary=salaried_only,
        csv_path=csv_path,
        cache_path=cache_path,
    )

    scored: list[tuple[tuple, dict]] = []
    for job in candidates:
        score, matched, missing, reason = score_job(
            job,
            position=position,
            user_skills=user_skills,
            target_categories=target_categories,
            target_tags=target_tags,
        )
        if score < min_score:
            continue
        sort_key = (
            score,
            len(matched),
            -len(missing),
            job["posted_at"],
            job["salary_mid"] is not None,
            job["id"],
        )
        scored.append(
            (
                sort_key,
                {
                    "job": job,
                    "score": score,
                    "matched_skills": matched,
                    "missing_skills": missing,
                    "reason": reason,
                },
            )
        )

    scored.sort(key=lambda item: item[0], reverse=True)
    for _, match in scored:
        yield match


def rank_jobs(
    position: str,
    skills: list[str],
    exclude_ids: set[str],
    remote_only: bool = False,
    limit: int = 50,
    *,
    categories: list[str] | None = None,
    locations: list[str] | None = None,
    min_salary: int | None = None,
    tags: list[str] | None = None,
    min_score: float = 0.0,
    require_salary: bool | None = None,
    csv_path: Path = DEFAULT_CSV_PATH,
    cache_path: Path = DEFAULT_CACHE_PATH,
) -> list[dict]:
    """Return up to ``limit`` JobMatch dicts ordered from best match to worst."""
    if limit <= 0:
        return []
    ranked = iter_ranked_jobs(
        position=position,
        skills=skills,
        exclude_ids=exclude_ids,
        categories=categories,
        locations=locations,
        remote_only=remote_only,
        min_salary=min_salary,
        tags=tags,
        min_score=min_score,
        require_salary=require_salary,
        csv_path=csv_path,
        cache_path=cache_path,
    )
    return list(islice(ranked, limit))
