"""Profile persistence and the future CV import boundary (WE-A)."""

from werkzeug.datastructures import FileStorage

from app import storage
from app.models import CvParseResult, UserProfile, utc_now


def get_or_create_profile(user_id: str) -> UserProfile:
    profile = storage.load_profile(user_id)
    if profile is None:
        profile = UserProfile(user_id=user_id)
        storage.save_profile(profile)
    return profile


def save_profile(profile: UserProfile) -> None:
    profile.updated_at = utc_now()
    storage.save_profile(profile)


def import_cv(user_id: str, file: FileStorage) -> CvParseResult:
    """A3: extract TXT/PDF text, then adapt analytics.cv.parse_cv(text)."""
    raise NotImplementedError("CV import is scheduled for task A3.")
