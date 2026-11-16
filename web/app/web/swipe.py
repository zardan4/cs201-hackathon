"""Swipe tab routes (WE-B): card stack page and the JSON swipe API."""

import re
from dataclasses import asdict

from flask import Blueprint, g, jsonify, render_template, request

from app.services import jobs_service

swipe_bp = Blueprint("swipe", __name__)

CARDS_PER_PAGE = 10
MAX_API_LIMIT = 50
# DOU vacancy IDs are numbers taken from the vacancy URL; anything else is rejected
# so a client cannot store arbitrary (or huge) values in the user's swipe history.
JOB_ID_PATTERN = re.compile(r"\d{1,12}")


@swipe_bp.get("/swipe")
def index():
    """Render the first cards on the server; JS only animates and posts swipes."""
    profile = g.profile
    needs_onboarding = not profile.position
    matches = [] if needs_onboarding else jobs_service.next_matches(profile, CARDS_PER_PAGE)
    return render_template(
        "swipe/index.html",
        profile=profile,
        matches=matches,
        needs_onboarding=needs_onboarding,
        skipped_count=0 if needs_onboarding else jobs_service.skipped_count(profile.user_id),
    )


@swipe_bp.get("/api/next-jobs")
def next_jobs():
    """JSON list of JobMatch for the next portion of cards."""
    limit = request.args.get("limit", CARDS_PER_PAGE, type=int)
    if limit is None or limit < 1:  # a negative limit would slice from the end of the list
        limit = CARDS_PER_PAGE
    limit = min(limit, MAX_API_LIMIT)
    matches = jobs_service.next_matches(g.profile, limit)
    # jsonify serialises the posted_at date as an HTTP date string; ISO is clearer.
    payload = [asdict(match) for match in matches]
    for item in payload:
        item["job"]["posted_at"] = item["job"]["posted_at"].isoformat()
    return jsonify(payload)


@swipe_bp.post("/api/swipe")
def swipe():
    """Body {"job_id": "...", "action": "like"|"skip"} -> {"ok": true}."""
    body = request.get_json(silent=True)
    if not isinstance(body, dict):  # e.g. a JSON list or a non-JSON body
        body = {}
    job_id = body.get("job_id")
    job_id = str(job_id).strip() if isinstance(job_id, (str, int)) else ""
    action = body.get("action")
    if not JOB_ID_PATTERN.fullmatch(job_id) or action not in jobs_service.VALID_ACTIONS:
        return jsonify(ok=False, error="Expected a numeric job_id and action 'like' or 'skip'."), 400
    try:
        jobs_service.record_swipe(g.profile.user_id, job_id, action)
    except ValueError as error:
        return jsonify(ok=False, error=str(error)), 400
    return jsonify(ok=True)
