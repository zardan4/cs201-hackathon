"""Insights page shell (WE-A)."""

from flask import Blueprint, render_template

insights_bp = Blueprint("insights", __name__)


@insights_bp.get("/insights")
def index():
    return render_template("insights/index.html")
