"""Swipe feed service (WE-B): adapts analytics output to shared dataclasses.

Analytics modules are imported inside the functions so the web app still starts
while the DA's `analytics` package is being built.
"""

import random
from datetime import date, datetime

from app import storage
from app.models import Job, JobMatch, SwipeAction, UserProfile

VALID_ACTIONS = ("like", "skip")
MIN_FEED_SCORE = 0.2  # weaker matches (usually 0%) are not worth a card
FEED_POOL_SIZE = 200  # candidates drawn from the ranking before the random pick
SCORE_BIAS = 0.25  # added to a score to get its pick weight: 100% ~1.25x, 40% ~0.65x, 20% ~0.45x


def _as_list(value) -> list[str]:
    """Parquet list columns come back as numpy arrays; JSON fixtures as lists."""
    if value is None:
        return []
    return [str(item) for item in value]


def _as_date(value) -> date:
    """Accept a date, datetime, pandas Timestamp or ISO string."""
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if hasattr(value, "date"):  # pandas.Timestamp
        return value.date()
    return date.fromisoformat(str(value)[:10])


def _as_int(value) -> int | None:
    """Missing salaries may arrive as None or NaN."""
    if value is None or value != value:  # NaN != NaN
        return None
    return int(value)


def _job_from_dict(raw: dict) -> Job:
    return Job(
        id=str(raw["id"]),
        title=raw["title"],
        company=raw["company"],
        locations=_as_list(raw.get("locations")),
        is_remote=bool(raw.get("is_remote")),
        salary_text=raw.get("salary_text") or None,
        salary_min=_as_int(raw.get("salary_min")),
        salary_max=_as_int(raw.get("salary_max")),
        salary_mid=_as_int(raw.get("salary_mid")),
        categories=_as_list(raw.get("categories")),
        skills=_as_list(raw.get("skills")),
        snippet=raw.get("snippet") or "",
        url=raw["url"],
        posted_at=_as_date(raw["posted_at"]),
    )


def _match_from_dict(raw: dict) -> JobMatch:
    return JobMatch(
        job=_job_from_dict(raw["job"]),
        score=float(raw["score"]),
        matched_skills=_as_list(raw.get("matched_skills")),
        missing_skills=_as_list(raw.get("missing_skills")),
        reason=raw.get("reason", ""),
    )


def swiped_job_ids(user_id: str) -> set[str]:
    """Jobs the user already liked or skipped are never shown again."""
    return {swipe.job_id for swipe in storage.list_swipes(user_id)}


def weighted_shuffle(rows: list[dict], limit: int, rng: random.Random | None = None) -> list[dict]:
    """Random order where better matches come up more often but do not always come first.

    Weighted sampling without replacement (Efraimidis-Spirakis): each row gets the key
    u ** (1 / weight) with u uniform in (0, 1); the largest keys win.
    """
    rng = rng or random
    keyed = [(rng.random() ** (1.0 / (SCORE_BIAS + row["score"])), index) for index, row in enumerate(rows)]
    keyed.sort(reverse=True)
    return [rows[index] for _, index in keyed[:limit]]


def next_matches(profile: UserProfile, limit: int = 10) -> list[JobMatch]:
    """A varied mix of decent salaried matches (e.g. 100%, 60%, 40%) the user has not swiped yet."""
    from analytics.matching import rank_jobs

    rows = rank_jobs(
        position=profile.position,
        skills=profile.skills,
        exclude_ids=swiped_job_ids(profile.user_id),
        remote_only=profile.remote_only,
        limit=FEED_POOL_SIZE,
        min_score=MIN_FEED_SCORE,
    )
    return [_match_from_dict(row) for row in weighted_shuffle(rows, limit)]


def record_swipe(user_id: str, job_id: str, action: str) -> None:
    """Persist a like/skip; a repeated swipe on the same job is ignored by storage."""
    if action not in VALID_ACTIONS:
        raise ValueError(f"Unknown swipe action: {action!r}")
    storage.append_swipe(SwipeAction(user_id=user_id, job_id=job_id, action=action))


def skipped_count(user_id: str) -> int:
    return sum(1 for swipe in storage.list_swipes(user_id) if swipe.action == "skip")


def reset_skipped(user_id: str) -> int:
    """Bring every skipped job back into the feed; saved (liked) jobs stay saved."""
    return storage.remove_swipes(user_id, action="skip")


def unsave_job(user_id: str, job_id: str) -> bool:
    """Remove one job from Saved jobs; it returns to the feed."""
    return storage.remove_swipes(user_id, action="like", job_id=job_id) > 0


def clear_saved(user_id: str) -> int:
    """Remove all saved jobs; they return to the feed."""
    return storage.remove_swipes(user_id, action="like")


def saved_jobs(user_id: str) -> list[Job]:
    """Liked jobs, newest like first (shown in the profile's Saved jobs block)."""
    from analytics.jobs import load_jobs

    likes = [swipe for swipe in storage.list_swipes(user_id) if swipe.action == "like"]
    if not likes:
        return []
    jobs_table = load_jobs()
    liked_ids = {swipe.job_id for swipe in likes}
    rows = jobs_table[jobs_table["id"].astype(str).isin(liked_ids)].to_dict("records")
    jobs_by_id = {str(row["id"]): _job_from_dict(row) for row in rows}
    newest_first = sorted(likes, key=lambda swipe: swipe.created_at, reverse=True)
    # A vacancy may disappear after a data refresh, so skip unknown ids.
    return [jobs_by_id[swipe.job_id] for swipe in newest_first if swipe.job_id in jobs_by_id]
