"""Onboarding and profile routes (WE-A). Forms and CV import follow in A1–A3."""

from flask import Blueprint, abort, g, redirect, render_template, request, url_for

profile_bp = Blueprint("profile", __name__)


@profile_bp.get("/")
def home():
    endpoint = "swipe.index" if g.profile.position else "profile.onboarding"
    return redirect(url_for(endpoint))


@profile_bp.route("/onboarding", methods=["GET", "POST"])
def onboarding():
    if request.method == "POST":
        abort(501, description="Onboarding submission is not implemented yet.")
    return render_template("onboarding/index.html")


@profile_bp.route("/profile", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        abort(501, description="Profile editing is not implemented yet.")
    return render_template("profile/index.html", profile=g.profile)


@profile_bp.post("/profile/cv")
def upload_cv():
    abort(501, description="CV upload is not implemented yet.")
