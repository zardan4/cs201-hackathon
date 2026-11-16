"""CV-first onboarding and profile review/editing (WE-A)."""

import hashlib
import hmac

from flask import Blueprint, abort, current_app, flash, g, redirect, render_template, request, url_for

from app.services import catalog_service, jobs_service, profile_service

profile_bp = Blueprint("profile", __name__)


def _csrf_token() -> str:
    key = current_app.secret_key
    if isinstance(key, str):
        key = key.encode()
    return hmac.new(key, f"profile:{g.profile.user_id}".encode(), hashlib.sha256).hexdigest()


@profile_bp.app_context_processor
def form_context():
    return {"csrf_token": _csrf_token() if hasattr(g, "profile") else ""}


@profile_bp.before_request
def protect_profile_forms():
    if request.method == "POST":
        token = request.form.get("csrf_token", "")
        if not hmac.compare_digest(token.encode("utf-8"), _csrf_token().encode("ascii")):
            abort(400, description="This form has expired. Reload the page and try again.")


def _view_context(form=None, error=None) -> dict:
    draft = profile_service.get_cv_draft(g.profile.user_id)
    profile = g.profile
    values = {
        "position": profile.position,
        "skills": profile.skills,
        "experience_years": profile.experience_years if g.onboarding_complete else "",
        "english_level": profile.english_level if g.onboarding_complete else "",
        "remote_only": profile.remote_only,
    }
    if draft is not None:
        values["position"] = draft.detected_position or values["position"]
        values["skills"] = draft.detected_skills or values["skills"]
        if draft.detected_experience_years is not None:
            values["experience_years"] = draft.detected_experience_years
        values["english_level"] = draft.detected_english_level or values["english_level"]
    if form is not None:
        values.update(position=form.get("position", ""), skills=form.getlist("skills"),
                      experience_years=form.get("experience_years", ""),
                      english_level=form.get("english_level", ""),
                      remote_only=form.get("remote_only") == "on")
    try:
        skills = catalog_service.all_skills()
        skill_groups = catalog_service.skill_groups()
    except catalog_service.CatalogUnavailable:
        skills = []
        skill_groups = []
        error = error or "The skills list is temporarily unavailable. Please try again later."
    saved_jobs = []
    saved_jobs_error = False
    if g.onboarding_complete:
        try:
            saved_jobs = jobs_service.saved_jobs(profile.user_id)
        except (OSError, ValueError, KeyError):
            current_app.logger.exception("Saved jobs could not be loaded")
            saved_jobs_error = True
    skipped_count = jobs_service.skipped_count(profile.user_id) if g.onboarding_complete else 0
    return dict(profile=profile, draft=draft, values=values, error=error, skipped_count=skipped_count,
                positions=catalog_service.all_positions(), skills=skills, skill_groups=skill_groups,
                saved_jobs=saved_jobs, saved_jobs_error=saved_jobs_error,
                english_levels=profile_service.ENGLISH_LEVELS)


def _render_page(*, form=None, error=None, status=200):
    template = "profile/index.html" if g.onboarding_complete else "onboarding/index.html"
    return render_template(template, **_view_context(form, error)), status


def _save_form():
    try:
        profile_service.confirm_profile(g.profile.user_id, request.form)
    except ValueError as error:
        return _render_page(form=request.form, error=str(error), status=400)
    flash("Profile saved.", "success")
    return redirect(url_for("profile.index"), code=303)


@profile_bp.get("/")
def home():
    endpoint = "swipe.index" if g.onboarding_complete else "profile.onboarding"
    return redirect(url_for(endpoint))


@profile_bp.route("/onboarding", methods=["GET", "POST"])
def onboarding():
    if g.onboarding_complete:
        return redirect(url_for("profile.index"), code=303)
    if request.method == "POST":
        return _save_form()
    return _render_page()


@profile_bp.route("/profile", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        return _save_form()
    return _render_page()


def _back_to():
    """Return to the page the form was posted from (only known pages, never a free-form URL)."""
    return redirect(url_for("swipe.index" if request.form.get("next") == "swipe" else "profile.index"), code=303)


@profile_bp.post("/profile/saved/remove")
def remove_saved_job():
    job_id = request.form.get("job_id", "").strip()
    if job_id and jobs_service.unsave_job(g.profile.user_id, job_id):
        flash("Removed from saved jobs.", "success")
    return _back_to()


@profile_bp.post("/profile/saved/clear")
def clear_saved_jobs():
    count = jobs_service.clear_saved(g.profile.user_id)
    flash(f"Removed {count} saved job{'s' if count != 1 else ''}." if count else "No saved jobs to remove.", "success")
    return _back_to()


@profile_bp.post("/profile/feed/reset")
def reset_feed():
    count = jobs_service.reset_skipped(g.profile.user_id)
    flash(f"{count} skipped job{'s are' if count != 1 else ' is'} back in your feed." if count else "No skipped jobs to bring back.", "success")
    return _back_to()


@profile_bp.post("/profile/cv")
def upload_cv():
    try:
        profile_service.import_cv(g.profile.user_id, request.files.get("cv"))
    except profile_service.CvAnalysisError as error:
        return _render_page(error=str(error), status=error.status_code)
    except ValueError as error:
        return _render_page(error=str(error), status=400)
    endpoint = "profile.index" if g.onboarding_complete else "profile.onboarding"
    return redirect(url_for(endpoint), code=303)
