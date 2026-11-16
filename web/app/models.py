"""Shared entities; field names follow docs/CONTRACTS.md section 2."""

from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from typing import Literal


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(kw_only=True)
class Job:
    id: str
    title: str
    company: str
    locations: list[str]
    is_remote: bool
    salary_text: str | None
    salary_min: int | None
    salary_max: int | None
    salary_mid: int | None
    categories: list[str]
    skills: list[str]
    snippet: str
    url: str
    posted_at: date
    tags: list[str] = field(default_factory=list)


@dataclass(kw_only=True)
class UserProfile:
    user_id: str
    position: str = ""
    skills: list[str] = field(default_factory=list)
    experience_years: float = 0.0
    english_level: str = "none"
    remote_only: bool = False
    cv_text: str | None = None
    onboarding_completed: bool = False
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)


@dataclass(kw_only=True)
class CvParseResult:
    raw_text: str
    detected_position: str | None
    detected_skills: list[str]
    detected_experience_years: float | None
    detected_english_level: str | None
    warnings: list[str]


@dataclass(kw_only=True)
class JobMatch:
    job: Job
    score: float
    matched_skills: list[str]
    missing_skills: list[str]
    reason: str


@dataclass(kw_only=True)
class SwipeAction:
    user_id: str
    job_id: str
    action: Literal["like", "skip"]
    created_at: datetime = field(default_factory=utc_now)


@dataclass(kw_only=True)
class SavedJob(SwipeAction):
    job: Job


@dataclass(kw_only=True)
class SalaryRecord:
    survey: str
    salary_usd: float
    position: str
    main_language: str | None
    specialization: str | None
    experience_years: float | None
    english_level: str | None
    company_size: str | None


@dataclass(kw_only=True)
class SalaryStats:
    median: float
    mean: float
    p25: float
    p75: float
    count: int
    basis: Literal["survey"]
    filters: dict
    histogram: list[dict[str, int]]


@dataclass(kw_only=True)
class UpgradeSuggestion:
    skill: str
    salary_gain_usd: float
    salary_gain_pct: float
    new_jobs_count: int
    example_job_ids: list[str]
    sample_size: int


@dataclass(kw_only=True)
class InsightsReport:
    profile_salary: SalaryStats
    jobs_available: int
    top_upgrades: list[UpgradeSuggestion]
