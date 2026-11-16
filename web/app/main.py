"""Flask application factory. Run from the repository root: python -m app.main."""

import os
import secrets
from pathlib import Path
from uuid import UUID, uuid4

from dotenv import load_dotenv
from flask import Flask, g, jsonify, redirect, render_template, request, session, url_for

from app.mascot import mascot_url
from app.services.profile_service import get_or_create_profile, is_profile_ready
from app.web import register_swipe_blueprint
from app.web.insights import insights_bp
from app.web.profile import profile_bp

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


def _session_key(path: Path) -> str:
    """Reuse a private signing key so a restart doesn't orphan saved profiles."""
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        return path.read_text(encoding="utf-8").strip()
    key = secrets.token_hex(32)
    with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
        stream.write(key)
    return key


def create_app(config: dict | None = None) -> Flask:
    load_dotenv(REPOSITORY_ROOT / ".env")
    app = Flask(__name__)
    app.config.from_mapping(
        SECRET_KEY=os.environ.get("BLOWMYJOB_SECRET_KEY"),
        USER_STORAGE_DIR=REPOSITORY_ROOT / "cache" / "users",
        MAX_CONTENT_LENGTH=5 * 1024 * 1024,
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        GEMINI_API_KEY=os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY"),
        GEMINI_MODEL=os.environ.get("GEMINI_MODEL", "gemini-3.5-flash-lite"),
        GEMINI_TIMEOUT_SECONDS=30,
        SKILLS_CATALOG_PATH=REPOSITORY_ROOT / "analytics" / "skills_catalog.json",
    )
    if config is not None:
        app.config.update(config)
    if not app.config["SECRET_KEY"]:
        key_path = Path(app.config["USER_STORAGE_DIR"]).parent / ".session-key"
        app.config["SECRET_KEY"] = _session_key(key_path)

    @app.before_request
    def load_current_profile():
        if request.endpoint == "static":
            return
        user_id = session.get("user_id")
        try:
            user_id = str(UUID(user_id)) if isinstance(user_id, str) else str(uuid4())
        except ValueError:
            user_id = str(uuid4())
        session["user_id"] = user_id
        g.profile = get_or_create_profile(user_id)
        g.onboarding_complete = is_profile_ready(g.profile)
        public_endpoints = {"profile.home", "profile.onboarding", "profile.upload_cv"}
        if not g.onboarding_complete and request.endpoint not in public_endpoints:
            if request.path.startswith("/api/"):
                return jsonify(error="onboarding_required", redirect=url_for("profile.onboarding")), 403
            return redirect(url_for("profile.onboarding"), code=303)

    @app.after_request
    def prevent_profile_caching(response):
        if request.endpoint != "static":
            response.headers["Cache-Control"] = "no-store"
        return response

    @app.errorhandler(404)
    def page_not_found(error):
        if request.path.startswith("/api/"):
            return jsonify(error="not_found"), 404
        return render_template("error404.html"), 404

    @app.errorhandler(413)
    def upload_too_large(error):
        return render_template("profile/error.html", title="File too large",
                               message="Please upload a CV smaller than 5 MiB."), 413

    app.jinja_env.globals["mascot_url"] = mascot_url
    app.register_blueprint(profile_bp)
    app.register_blueprint(insights_bp)
    register_swipe_blueprint(app)
    return app


if __name__ == "__main__":
    create_app().run(host="127.0.0.1", port=int(os.environ.get("PORT", "5000")))
