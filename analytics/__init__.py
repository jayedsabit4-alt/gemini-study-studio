"""Analytics and Dashboard Metrics Package API."""

from .dashboard import calculate_study_streak, get_dashboard_summary

__all__ = [
    "calculate_study_streak",
    "get_dashboard_summary",
]
