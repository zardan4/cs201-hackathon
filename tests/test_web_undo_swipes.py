"""Undoing swipes: reset skipped jobs and remove saved jobs (storage + jobs_service)."""

from uuid import uuid4

import pytest
from flask import Flask

from app import storage
from app.models import UserProfile
from app.services import jobs_service


@pytest.fixture()
def user_id(tmp_path):
    app = Flask(__name__)
    app.config["USER_STORAGE_DIR"] = tmp_path
    uid = str(uuid4())
    with app.app_context():
        storage.save_profile(UserProfile(user_id=uid, position="Python", skills=["python"], onboarding_completed=True))
        for job_id, action in [("1", "like"), ("2", "skip"), ("3", "skip"), ("4", "like")]:
            jobs_service.record_swipe(uid, job_id, action)
        yield uid


def test_reset_skipped_keeps_saved_jobs(user_id):
    assert jobs_service.skipped_count(user_id) == 2
    assert jobs_service.reset_skipped(user_id) == 2
    assert jobs_service.skipped_count(user_id) == 0
    assert jobs_service.swiped_job_ids(user_id) == {"1", "4"}


def test_unsave_one_job_returns_it_to_the_feed(user_id):
    assert jobs_service.unsave_job(user_id, "1") is True
    assert jobs_service.unsave_job(user_id, "1") is False
    assert jobs_service.swiped_job_ids(user_id) == {"2", "3", "4"}


def test_clear_saved_leaves_skips_alone(user_id):
    assert jobs_service.clear_saved(user_id) == 2
    assert jobs_service.swiped_job_ids(user_id) == {"2", "3"}


def test_remove_swipes_requires_a_filter(user_id):
    with pytest.raises(ValueError):
        storage.remove_swipes(user_id)
