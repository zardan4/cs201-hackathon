"""Load, normalize, cache, and stream DOU active vacancies."""

from __future__ import annotations

import os
import re
from datetime import date, datetime
from pathlib import Path
from typing import Iterator

import pandas as pd

from analytics.config import SWIPE_REQUIRES_SALARY
from analytics.skills import extract_job_skills, extract_tags

ANALYTICS_DIR = Path(__file__).resolve().parent
ROOT_DIR = ANALYTICS_DIR.parent
DEFAULT_CSV_PATH = ROOT_DIR / "data" / "dou_active_vacancies.csv"
CACHE_DIR = ROOT_DIR / "cache"
DEFAULT_CACHE_PATH = CACHE_DIR / "jobs.parquet"

MIN_MONTHLY_SALARY_USD = 100
MAX_MONTHLY_SALARY_USD = 30000

JOB_COLUMNS = [
    "id",
    "title",
    "company",
    "locations",
    "is_remote",
    "salary_text",
    "salary_min",
    "salary_max",
    "salary_mid",
    "categories",
    "skills",
    "tags",
    "snippet",
    "url",
    "posted_at",
]

_VACANCY_ID_RE = re.compile(r"/vacancies/(\d+)/?")
_SALARY_RANGE_RE = re.compile(r"^\$(\d+)\s*[–-]\s*(\d+)$")
_SALARY_MIN_RE = re.compile(r"^від\s*\$(\d+)$", re.IGNORECASE)
_SALARY_MAX_RE = re.compile(r"^до\s*\$(\d+)$", re.IGNORECASE)
_SALARY_EXACT_RE = re.compile(r"^\$(\d+)$")
_REMOTE_SUFFIX_RE = re.compile(r"\s*\(remote\)$", re.IGNORECASE)
_REMOTE_PREFIX_RE = re.compile(r"^remote\s+", re.IGNORECASE)

_MEM_DF: pd.DataFrame | None = None
_MEM_RECORDS: list[dict] | None = None


def clear_cache() -> None:
    """Clear in-memory cached vacancy tables (disk cache is preserved)."""
    global _MEM_DF, _MEM_RECORDS
    _MEM_DF = None
    _MEM_RECORDS = None


def extract_job_id(link: str) -> str:
    """Extract unique numeric vacancy ID from a DOU job URL."""
    text = (link or "").strip()
    match = _VACANCY_ID_RE.search(text)
    if match:
        return match.group(1)
    return text.rstrip("/").rsplit("/", 1)[-1]


def _is_valid_monthly_salary(amount: int) -> bool:
    return MIN_MONTHLY_SALARY_USD <= amount <= MAX_MONTHLY_SALARY_USD


def parse_salary(salary_text: str | None) -> tuple[int | None, int | None, int | None]:
    """Parse DOU salary string into (salary_min, salary_max, salary_mid) in USD/month.

    Outliers below $100 (hourly rates) or above $30,000 return (None, None, None).
    """
    if salary_text is None:
        return None, None, None
    text = str(salary_text).strip()
    if not text or text.lower() == "nan":
        return None, None, None

    if m := _SALARY_RANGE_RE.match(text):
        low, high = int(m.group(1)), int(m.group(2))
        if low > high:
            low, high = high, low
        if not (_is_valid_monthly_salary(low) and _is_valid_monthly_salary(high)):
            return None, None, None
        return low, high, (low + high) // 2

    if m := _SALARY_MIN_RE.match(text):
        low = int(m.group(1))
        if not _is_valid_monthly_salary(low):
            return None, None, None
        return low, None, low

    if m := _SALARY_MAX_RE.match(text):
        high = int(m.group(1))
        if not _is_valid_monthly_salary(high):
            return None, None, None
        return None, high, high

    if m := _SALARY_EXACT_RE.match(text):
        exact = int(m.group(1))
        if not _is_valid_monthly_salary(exact):
            return None, None, None
        return exact, exact, exact

    return None, None, None


def parse_locations(location_text: str | None) -> tuple[list[str], bool]:
    """Parse location string into (cleaned_locations, is_remote)."""
    if location_text is None:
        return [], False
    raw = str(location_text).strip()
    if not raw or raw.lower() == "nan":
        return [], False

    is_remote = "віддалено" in raw.lower() or "remote" in raw.lower()
    locations: list[str] = []
    seen: set[str] = set()

    for part in raw.split(","):
        token = part.strip()
        if not token:
            continue
        low = token.lower()
        if low in {"віддалено", "remote"} or low.startswith("we're a fully remote"):
            is_remote = True
            continue
        if _REMOTE_SUFFIX_RE.search(token):
            is_remote = True
            token = _REMOTE_SUFFIX_RE.sub("", token).strip()
        elif _REMOTE_PREFIX_RE.match(token):
            is_remote = True
            token = _REMOTE_PREFIX_RE.sub("", token).strip()
        if token and token not in seen:
            seen.add(token)
            locations.append(token)

    return locations, is_remote


def parse_categories(categories_text: str | None) -> list[str]:
    """Parse DOU categories string (semicolon-delimited, comma fallback) into a list."""
    if categories_text is None:
        return []
    raw = str(categories_text).strip()
    if not raw or raw.lower() == "nan":
        return []
    sep = ";" if ";" in raw else ","
    result: list[str] = []
    seen: set[str] = set()
    for part in raw.split(sep):
        cleaned = part.strip()
        if cleaned and cleaned not in seen:
            seen.add(cleaned)
            result.append(cleaned)
    return result


def _parse_date(value: object) -> date:
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    return date.fromisoformat(str(value).strip()[:10])


def _clean_text(value: object) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    text = str(value).strip()
    return "" if text.lower() == "nan" else text


def _build_dataframe_from_csv(csv_path: Path) -> pd.DataFrame:
    raw_df = pd.read_csv(csv_path, encoding="utf-8-sig", dtype=str, keep_default_na=False)
    records: list[dict] = []

    for row in raw_df.to_dict(orient="records"):
        title = _clean_text(row.get("title"))
        company = _clean_text(row.get("company"))
        snippet = _clean_text(row.get("snippet"))
        url = _clean_text(row.get("link"))
        raw_location = _clean_text(row.get("location"))
        raw_salary = _clean_text(row.get("salary"))
        raw_categories = _clean_text(row.get("categories"))
        raw_date = _clean_text(row.get("date"))

        locations, is_remote = parse_locations(raw_location)
        categories = parse_categories(raw_categories)
        salary_min, salary_max, salary_mid = parse_salary(raw_salary)
        skills = extract_job_skills(title, snippet, categories)
        tags = extract_tags(title, snippet, raw_location)

        records.append(
            {
                "id": extract_job_id(url),
                "title": title,
                "company": company,
                "locations": locations,
                "is_remote": is_remote,
                "salary_text": raw_salary or None,
                "salary_min": salary_min,
                "salary_max": salary_max,
                "salary_mid": salary_mid,
                "categories": categories,
                "skills": skills,
                "tags": tags,
                "snippet": snippet,
                "url": url,
                "posted_at": _parse_date(raw_date),
            }
        )

    df = pd.DataFrame.from_records(records, columns=JOB_COLUMNS)
    for col in ("salary_min", "salary_max", "salary_mid"):
        df[col] = df[col].astype("Int64")
    return df


def _to_plain_list(val: object) -> list[str]:
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return []
    if isinstance(val, list):
        return [str(x) for x in val]
    return [str(x) for x in list(val)]


def _to_opt_int(val: object) -> int | None:
    if val is None or pd.isna(val):
        return None
    return int(val)


def _df_to_plain_records(df: pd.DataFrame) -> list[dict]:
    records: list[dict] = []
    for row in df.to_dict(orient="records"):
        salary_text = row.get("salary_text")
        if salary_text is not None and pd.isna(salary_text):
            salary_text = None
        records.append(
            {
                "id": str(row["id"]),
                "title": str(row["title"]),
                "company": str(row["company"]),
                "locations": _to_plain_list(row.get("locations")),
                "is_remote": bool(row["is_remote"]),
                "salary_text": str(salary_text) if salary_text else None,
                "salary_min": _to_opt_int(row.get("salary_min")),
                "salary_max": _to_opt_int(row.get("salary_max")),
                "salary_mid": _to_opt_int(row.get("salary_mid")),
                "categories": _to_plain_list(row.get("categories")),
                "skills": _to_plain_list(row.get("skills")),
                "tags": _to_plain_list(row.get("tags")),
                "snippet": str(row["snippet"]),
                "url": str(row["url"]),
                "posted_at": _parse_date(row["posted_at"]),
            }
        )
    return records


def _is_default_paths(csv_path: Path, cache_path: Path) -> bool:
    return csv_path.resolve() == DEFAULT_CSV_PATH.resolve() and cache_path.resolve() == DEFAULT_CACHE_PATH.resolve()


def build_jobs(
    csv_path: Path = DEFAULT_CSV_PATH,
    cache_path: Path = DEFAULT_CACHE_PATH,
    force: bool = False,
) -> pd.DataFrame:
    """Build cache/jobs.parquet from the raw CSV unless the cache already exists.

    When ``force=False`` and ``cache_path`` exists, loads directly from Parquet
    without reprocessing the CSV.
    """
    global _MEM_DF, _MEM_RECORDS

    if not force and cache_path.exists():
        return load_jobs(refresh=False, require_salary=False, csv_path=csv_path, cache_path=cache_path)

    df = _build_dataframe_from_csv(csv_path)
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = cache_path.with_suffix(".parquet.tmp")
    df.to_parquet(tmp_path, index=False)
    os.replace(tmp_path, cache_path)

    if _is_default_paths(csv_path, cache_path):
        _MEM_DF = df
        _MEM_RECORDS = _df_to_plain_records(df)

    return df.copy()


def load_jobs(
    refresh: bool = False,
    require_salary: bool | None = None,
    csv_path: Path = DEFAULT_CSV_PATH,
    cache_path: Path = DEFAULT_CACHE_PATH,
) -> pd.DataFrame:
    """Return normalized vacancies DataFrame (lazy process-once on first access).

    When ``require_salary`` is None, falls back to ``SWIPE_REQUIRES_SALARY``.
    """
    global _MEM_DF, _MEM_RECORDS
    use_mem = _is_default_paths(csv_path, cache_path)
    salaried_only = SWIPE_REQUIRES_SALARY if require_salary is None else require_salary

    if not refresh and use_mem and _MEM_DF is not None:
        df = _MEM_DF
    elif not refresh and cache_path.exists():
        df = pd.read_parquet(cache_path)
        if use_mem:
            _MEM_DF = df
            _MEM_RECORDS = _df_to_plain_records(df)
    else:
        df = build_jobs(csv_path=csv_path, cache_path=cache_path, force=True)

    if salaried_only:
        return df[df["salary_mid"].notna()].reset_index(drop=True)
    return df.copy()


def _get_job_records(
    csv_path: Path = DEFAULT_CSV_PATH,
    cache_path: Path = DEFAULT_CACHE_PATH,
) -> list[dict]:
    global _MEM_RECORDS
    if _is_default_paths(csv_path, cache_path) and _MEM_RECORDS is not None:
        return _MEM_RECORDS
    df = load_jobs(refresh=False, require_salary=False, csv_path=csv_path, cache_path=cache_path)
    records = _df_to_plain_records(df)
    if _is_default_paths(csv_path, cache_path):
        _MEM_RECORDS = records
    return records


def _matches_location_filter(job: dict, location_filters: list[str]) -> bool:
    job_locs_low = [loc.lower() for loc in job["locations"]]
    for wanted in location_filters:
        if wanted in {"remote", "віддалено"} and job["is_remote"]:
            return True
        if any(wanted in loc for loc in job_locs_low):
            return True
    return False


def iter_jobs(
    categories: list[str] | None = None,
    locations: list[str] | None = None,
    remote_only: bool = False,
    exclude_ids: set[str] | None = None,
    min_salary: int | None = None,
    skills: list[str] | None = None,
    tags: list[str] | None = None,
    require_salary: bool = False,
    *,
    csv_path: Path = DEFAULT_CSV_PATH,
    cache_path: Path = DEFAULT_CACHE_PATH,
) -> Iterator[dict]:
    """Yield normalized Job dicts matching the given filters."""
    wanted_cats = {c.strip().lower() for c in categories if c and c.strip()} if categories else None
    wanted_locs = [loc.strip().lower() for loc in locations if loc and loc.strip()] if locations else None
    wanted_skills = {s.strip().lower() for s in skills if s and s.strip()} if skills else None
    wanted_tags = {t.strip().lower() for t in tags if t and t.strip()} if tags else None
    excluded = set(exclude_ids) if exclude_ids else None

    for job in _get_job_records(csv_path=csv_path, cache_path=cache_path):
        if excluded and job["id"] in excluded:
            continue
        if require_salary and job["salary_mid"] is None:
            continue
        if remote_only and not job["is_remote"]:
            continue
        if wanted_cats:
            job_cats = {c.lower() for c in job["categories"]}
            if not (job_cats & wanted_cats):
                continue
        if wanted_locs and not _matches_location_filter(job, wanted_locs):
            continue
        if min_salary is not None:
            salary_mid = job["salary_mid"]
            if salary_mid is None or salary_mid < min_salary:
                continue
        if wanted_skills:
            job_skills = {s.lower() for s in job["skills"]}
            if not (job_skills & wanted_skills):
                continue
        if wanted_tags:
            job_tags = {t.lower() for t in job["tags"]}
            if not (job_tags & wanted_tags):
                continue
        yield {
            **job,
            "locations": list(job["locations"]),
            "categories": list(job["categories"]),
            "skills": list(job["skills"]),
            "tags": list(job["tags"]),
        }
