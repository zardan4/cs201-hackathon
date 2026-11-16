"""JSON persistence for the single-process demo server (CONTRACTS section 5.1)."""

import json
import os
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from tempfile import NamedTemporaryFile
from threading import RLock
from uuid import UUID

from flask import current_app

from app.models import CvParseResult, SwipeAction, UserProfile

_lock = RLock()


def _user_path(user_id: str) -> Path:
    # Validate before using a session value as a filename.
    canonical_id = str(UUID(user_id))
    return Path(current_app.config["USER_STORAGE_DIR"]) / f"{canonical_id}.json"


def _read(user_id: str) -> dict:
    path = _user_path(user_id)
    if not path.exists():
        return {"profile": None, "swipes": [], "cv_draft": None}
    return json.loads(path.read_text(encoding="utf-8"))


def _write(user_id: str, document: dict) -> None:
    path = _user_path(user_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = None
    try:
        with NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent,
                                suffix=".tmp", delete=False) as temporary:
            temporary_path = Path(temporary.name)
            json.dump(document, temporary, ensure_ascii=False, indent=2)
        os.replace(temporary_path, path)
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)


def load_profile(user_id: str) -> UserProfile | None:
    with _lock:
        raw = _read(user_id)["profile"]
    if raw is None:
        return None
    for key in ("created_at", "updated_at"):
        raw[key] = datetime.fromisoformat(raw[key])
    return UserProfile(**raw)


def save_profile(profile: UserProfile) -> None:
    raw = asdict(profile)
    for key in ("created_at", "updated_at"):
        raw[key] = raw[key].isoformat()
    with _lock:
        document = _read(profile.user_id)
        document["profile"] = raw
        _write(profile.user_id, document)


def list_swipes(user_id: str) -> list[SwipeAction]:
    with _lock:
        rows = _read(user_id)["swipes"]
    return [SwipeAction(**{**row, "created_at": datetime.fromisoformat(row["created_at"])})
            for row in rows]


def append_swipe(swipe: SwipeAction) -> None:
    """Store the first action per job, preserving the user's current profile."""
    if swipe.action not in {"like", "skip"}:
        raise ValueError("Swipe action must be 'like' or 'skip'.")
    with _lock:
        document = _read(swipe.user_id)
        if document["profile"] is None:
            raise ValueError("Create a profile before recording swipes.")
        if any(row["job_id"] == swipe.job_id for row in document["swipes"]):
            return
        raw = asdict(swipe)
        raw["created_at"] = swipe.created_at.isoformat()
        document["swipes"].append(raw)
        _write(swipe.user_id, document)


def remove_swipes(user_id: str, *, action: str | None = None, job_id: str | None = None) -> int:
    """Undo swipes (the jobs return to the feed). Filters by action and/or job; returns how many were removed."""
    if action is None and job_id is None:
        raise ValueError("Say which swipes to remove: an action, a job, or both.")
    with _lock:
        document = _read(user_id)
        kept = [row for row in document["swipes"]
                if not ((action is None or row["action"] == action) and (job_id is None or row["job_id"] == job_id))]
        removed = len(document["swipes"]) - len(kept)
        if removed:
            document["swipes"] = kept
            _write(user_id, document)
    return removed


def load_cv_draft(user_id: str) -> CvParseResult | None:
    with _lock:
        raw = _read(user_id).get("cv_draft")
    return CvParseResult(**raw) if raw is not None else None


def save_cv_draft(user_id: str, result: CvParseResult | None) -> None:
    """Keep unconfirmed CV data on the server, separate from the active profile."""
    with _lock:
        document = _read(user_id)
        if document["profile"] is None:
            raise ValueError("Create a profile before importing a CV.")
        document["cv_draft"] = asdict(result) if result is not None else None
        _write(user_id, document)
