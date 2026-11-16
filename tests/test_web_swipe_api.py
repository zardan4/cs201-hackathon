"""Input validation of the swipe API (WE-B): bad input is rejected with HTTP 400."""

import pytest

from app import storage
from app.main import create_app


@pytest.fixture
def client(tmp_path):
    """A test client whose profile has finished onboarding (no Gemini call needed)."""
    app = create_app({"USER_STORAGE_DIR": tmp_path, "TESTING": True})
    client = app.test_client()
    client.get("/")
    with client.session_transaction() as session:
        user_id = session["user_id"]
    with app.app_context():
        profile = storage.load_profile(user_id)
        profile.position, profile.skills = "Python", ["python"]
        profile.cv_text, profile.onboarding_completed = "cv", True
        storage.save_profile(profile)
    return client


@pytest.mark.parametrize("body", [
    {"job_id": "x" * 100_000, "action": "skip"},   # huge value
    {"job_id": {"nested": 1}, "action": "skip"},   # not a string
    {"job_id": "380099; drop", "action": "like"},  # not numeric
    {"job_id": "380099", "action": "superlike"},   # unknown action
    [1, 2, 3],                                      # JSON list instead of an object
])
def test_swipe_rejects_bad_input(client, body):
    response = client.post("/api/swipe", json=body)
    assert response.status_code == 400
    assert response.get_json()["ok"] is False


def test_swipe_accepts_numeric_job_id(client):
    response = client.post("/api/swipe", json={"job_id": "380099", "action": "skip"})
    assert response.get_json() == {"ok": True}


@pytest.mark.parametrize("limit", ["-5", "0", "abc"])
def test_next_jobs_ignores_invalid_limit(client, limit):
    cards = client.get(f"/api/next-jobs?limit={limit}").get_json()
    assert len(cards) <= 10
