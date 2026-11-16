"""DOU-only report adapter and server-rendered chart (WE-A, A4–A5)."""

import math
from io import BytesIO

from analytics.matching import iter_ranked_jobs
from analytics.salary import salary_stats
from analytics.upgrade import UNLOCK_SCORE_THRESHOLD, recommend_upgrades
from app.models import InsightsReport, SalaryStats, UpgradeSuggestion, UserProfile


def _salary(profile: UserProfile) -> SalaryStats:
    raw = salary_stats(profile.position, profile.skills, profile.experience_years)
    if raw["basis"] != "survey":
        raise ValueError("Insights require DOU survey statistics.")
    stats = SalaryStats(**raw)
    if stats.count <= 0 or not all(math.isfinite(value) for value in
                                 (stats.median, stats.mean, stats.p25, stats.p75)):
        stats.count = 0
        stats.median = stats.mean = stats.p25 = stats.p75 = 0
        stats.histogram = []
    return stats


def build_report(profile: UserProfile) -> InsightsReport:
    """Delegate all calculations to the DA library; expose only dataclasses."""
    stats = _salary(profile)
    available = sum(1 for _ in iter_ranked_jobs(
        position=profile.position, skills=profile.skills, exclude_ids=set(),
        remote_only=profile.remote_only, min_score=UNLOCK_SCORE_THRESHOLD, require_salary=True,
    ))
    upgrades = recommend_upgrades(profile.position, profile.skills, top_n=5) if stats.count else []
    return InsightsReport(profile_salary=stats, jobs_available=available,
                          top_upgrades=[UpgradeSuggestion(**item) for item in upgrades
                                        if item["sample_size"] >= 30 and item["skill"] not in profile.skills][:5])


MUTED = "#9aa3bf"  # chart text on the dark app theme


def salary_chart(profile: UserProfile) -> bytes:
    """Plot the DA histogram without interactive JavaScript or shared pyplot state."""
    from matplotlib.figure import Figure

    stats = _salary(profile)
    figure = Figure(figsize=(7, 3.8), layout="constrained", facecolor="none")
    axes = figure.subplots()
    if stats.histogram:
        labels = [f'${bucket["from"]:,}–{bucket["to"]:,}' for bucket in stats.histogram]
        labels[-1] = f'${stats.histogram[-1]["from"]:,}+'
        axes.bar(range(len(labels)), [bucket["count"] for bucket in stats.histogram],
                 color="#ff3d81", edgecolor="none", width=.72, zorder=3)
        axes.set_xticks(range(len(labels)), labels, rotation=30, ha="right", fontsize=11, color=MUTED)
        axes.set_ylabel("Survey responses", color=MUTED, fontsize=11)
        axes.set_xlabel("Monthly take-home salary · USD", color=MUTED, fontsize=11)
        axes.grid(axis="y", color="#ffffff", alpha=.08, zorder=0)
        axes.spines[["top", "right"]].set_visible(False)
        axes.spines[["left", "bottom"]].set_color("#ffffff22")
        axes.tick_params(axis="y", colors=MUTED, labelsize=11)
        axes.patch.set_alpha(0)
        axes.set_ylim(bottom=0)
    else:
        axes.text(.5, .5, "No DOU salary responses available", ha="center", va="center", color=MUTED)
        axes.set_axis_off()
    output = BytesIO()
    figure.savefig(output, format="svg", metadata={"Date": None})
    return output.getvalue()
