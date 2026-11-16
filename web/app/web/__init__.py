"""Blueprint integration shared by the web engineers."""

from importlib import import_module
from importlib.util import find_spec

from flask import Blueprint, Flask, render_template


def register_swipe_blueprint(app: Flask) -> None:
    """Use WE-B's blueprint when available; otherwise show a temporary empty tab."""
    if find_spec("app.web.swipe") is not None:
        module = import_module("app.web.swipe")
        app.register_blueprint(module.swipe_bp)
        return

    placeholder = Blueprint("swipe", __name__)

    @placeholder.get("/swipe")
    def index():
        return render_template("placeholder.html", title="Job feed unavailable",
                               message="Please try again later.")

    app.register_blueprint(placeholder)
