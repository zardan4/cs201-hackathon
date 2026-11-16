"""Swipe tab routes (WE-B): card stack page and the JSON swipe API."""

from dataclasses import asdict

from flask import Blueprint, g, jsonify, render_template, request

from app.services import jobs_service

swipe_bp = Blueprint("swipe", __name__)

CARDS_PER_PAGE = 10
MAX_API_LIMIT = 50


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
        activity=jobs_service.swipe_activity(profile.user_id),
        strong_match_score=jobs_service.STRONG_MATCH_SCORE,
    )


LIKED_FILTERS = {
    "all": ("All", lambda job: True),
    "remote": ("Remote", lambda job: job.is_remote),
    "office": ("Office", lambda job: not job.is_remote),
}


@swipe_bp.get("/liked")
def liked():
    """Liked jobs list with All / Remote / Office filters (server-side)."""
    active_filter = request.args.get("filter", "all")
    if active_filter not in LIKED_FILTERS:
        active_filter = "all"
    saved = jobs_service.liked_jobs(g.profile.user_id)
    keep = LIKED_FILTERS[active_filter][1]
    return render_template(
        "swipe/liked.html",
        profile=g.profile,
        total=len(saved),
        saved=[item for item in saved if keep(item.job)],
        filters={key: label for key, (label, _) in LIKED_FILTERS.items()},
        active_filter=active_filter,
    )


@swipe_bp.get("/api/next-jobs")
def next_jobs():
    """JSON list of JobMatch for the next portion of cards."""
    limit = min(request.args.get("limit", CARDS_PER_PAGE, type=int) or CARDS_PER_PAGE,
                MAX_API_LIMIT)
    matches = jobs_service.next_matches(g.profile, limit)
    # jsonify serialises the posted_at date as an HTTP date string; ISO is clearer.
    payload = [asdict(match) for match in matches]
    for item in payload:
        item["job"]["posted_at"] = item["job"]["posted_at"].isoformat()
    return jsonify(payload)


@swipe_bp.post("/api/swipe")
def swipe():
    """Body {"job_id": "...", "action": "like"|"skip"} -> {"ok": true, "activity": {...}}."""
    body = request.get_json(silent=True) or {}
    job_id = str(body.get("job_id", "")).strip()
    action = body.get("action")
    if not job_id or action not in jobs_service.VALID_ACTIONS:
        return jsonify(ok=False, error="Expected job_id and action 'like' or 'skip'."), 400
    try:
        jobs_service.record_swipe(g.profile.user_id, job_id, action)
    except ValueError as error:
        return jsonify(ok=False, error=str(error)), 400
    activity = jobs_service.swipe_activity(g.profile.user_id)
    return jsonify(ok=True, activity=asdict(activity))
