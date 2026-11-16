"""Flask application factory. Run from the repository root: python -m app.main."""

import os
import secrets
from pathlib import Path
from uuid import UUID, uuid4

from flask import Flask, g, request, session

from app.services.profile_service import get_or_create_profile
from app.web import register_swipe_blueprint
from app.web.insights import insights_bp
from app.web.profile import profile_bp

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


def create_app(config: dict | None = None) -> Flask:
    app = Flask(__name__)
    app.config.from_mapping(
        SECRET_KEY=os.environ.get("SWIPEJOB_SECRET_KEY") or secrets.token_hex(32),
        USER_STORAGE_DIR=REPOSITORY_ROOT / "cache" / "users",
        MAX_CONTENT_LENGTH=5 * 1024 * 1024,
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
    )
    if config is not None:
        app.config.update(config)

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

    app.register_blueprint(profile_bp)
    app.register_blueprint(insights_bp)
    register_swipe_blueprint(app)
    return app


if __name__ == "__main__":
    create_app().run(host="127.0.0.1", port=int(os.environ.get("PORT", "5000")))
