"""Survey statistics and upgrade report boundary (WE-A, tasks A4–A5)."""

from app.models import InsightsReport, UserProfile


def build_report(profile: UserProfile) -> InsightsReport:
    """Combine DOU survey statistics, matching job count and upgrades."""
    raise NotImplementedError("Connect analytics in tasks A4–A5.")
