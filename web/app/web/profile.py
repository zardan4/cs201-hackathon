"""CV-first onboarding and profile review/editing (WE-A)."""

import hashlib
import hmac

from flask import Blueprint, abort, current_app, flash, g, redirect, render_template, request, url_for

from app.services import catalog_service, profile_service

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
    except catalog_service.CatalogUnavailable:
        skills = []
        error = error or "The skills list is temporarily unavailable. Please try again later."
    return dict(profile=profile, draft=draft, values=values, error=error,
                positions=catalog_service.all_positions(), skills=skills,
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
