"""SwipeJob analytics library: data loading, skill extraction, and job matching."""

from analytics.config import SWIPE_REQUIRES_SALARY
from analytics.cv import parse_cv
from analytics.jobs import (
    build_jobs,
    clear_cache,
    extract_job_id,
    iter_jobs,
    load_jobs,
    parse_categories,
    parse_locations,
    parse_salary,
)
from analytics.matching import iter_ranked_jobs, rank_jobs, score_job
from analytics.salary import salary_stats, vacancy_salary_stats
from analytics.salary_records import load_salary_records
from analytics.skills import (
    all_positions,
    all_skills,
    extract_job_skills,
    extract_skills,
    extract_tags,
)
from analytics.upgrade import recommend_upgrades

__all__ = [
    "SWIPE_REQUIRES_SALARY",
    "all_positions",
    "all_skills",
    "build_jobs",
    "clear_cache",
    "extract_job_id",
    "extract_job_skills",
    "extract_skills",
    "extract_tags",
    "iter_jobs",
    "iter_ranked_jobs",
    "load_jobs",
    "load_salary_records",
    "parse_categories",
    "parse_cv",
    "parse_locations",
    "parse_salary",
    "rank_jobs",
    "recommend_upgrades",
    "salary_stats",
    "score_job",
    "vacancy_salary_stats",
]
