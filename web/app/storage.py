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

from app.models import SwipeAction, UserProfile

_lock = RLock()


def _user_path(user_id: str) -> Path:
    # Validate before using a session value as a filename.
    canonical_id = str(UUID(user_id))
    return Path(current_app.config["USER_STORAGE_DIR"]) / f"{canonical_id}.json"


def _read(user_id: str) -> dict:
    path = _user_path(user_id)
    if not path.exists():
        return {"profile": None, "swipes": []}
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
