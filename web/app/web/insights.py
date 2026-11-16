"""DOU insights pages and salary distribution image (WE-A)."""

from flask import Blueprint, Response, current_app, g, render_template

from app.services import insights_service

insights_bp = Blueprint("insights", __name__)


@insights_bp.get("/insights")
def index():
    try:
        report = insights_service.build_report(g.profile)
    except (OSError, ValueError, KeyError):
        current_app.logger.exception("DOU insights could not be loaded")
        return render_template("insights/index.html", report=None, profile=g.profile), 503
    return render_template("insights/index.html", report=report, profile=g.profile)


@insights_bp.get("/insights/salary-distribution.svg")
def distribution():
    try:
        svg = insights_service.salary_chart(g.profile)
    except (OSError, ValueError, KeyError):
        return Response("Salary chart is temporarily unavailable", status=503, mimetype="text/plain")
    return Response(svg, mimetype="image/svg+xml")
