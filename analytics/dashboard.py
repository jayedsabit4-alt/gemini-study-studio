"""Analytics Engine for Subject Mastery, Accuracy Metrics, and Study Streaks."""

from datetime import datetime, timedelta
import logging
import sqlite3
from typing import Any, Dict, Optional
from database.database import get_db_connection

logger = logging.getLogger(__name__)


def calculate_study_streak(
    existing_conn: Optional[sqlite3.Connection] = None,
) -> Dict[str, Any]:
    """Calculates active daily study streak and total sessions logged using question attempts."""
    conn = existing_conn or get_db_connection()
    try:
        cursor = conn.cursor()
        # Query activity dates from question_attempts and mcq_exams
        cursor.execute(
            """
            SELECT DISTINCT activity_date FROM (
                SELECT DATE(attempted_at) AS activity_date FROM question_attempts WHERE attempted_at IS NOT NULL
                UNION
                SELECT DATE(created_at) AS activity_date FROM mcq_exams WHERE created_at IS NOT NULL
            ) ORDER BY activity_date DESC
            """
        )
        rows = cursor.fetchall()

        if not rows:
            return {"current_streak_days": 0, "total_active_days": 0, "last_active_date": None}

        active_dates = [datetime.strptime(r[0], "%Y-%m-%d").date() for r in rows if r[0]]
        if not active_dates:
            return {"current_streak_days": 0, "total_active_days": 0, "last_active_date": None}

        today = datetime.now().date()
        yesterday = today - timedelta(days=1)

        if active_dates[0] not in (today, yesterday):
            streak = 0
        else:
            streak = 1
            current_date = active_dates[0]
            for idx in range(1, len(active_dates)):
                if active_dates[idx] == current_date - timedelta(days=1):
                    streak += 1
                    current_date = active_dates[idx]
                elif active_dates[idx] == current_date:
                    continue
                else:
                    break

        return {
            "current_streak_days": streak,
            "total_active_days": len(active_dates),
            "last_active_date": active_dates[0].isoformat(),
        }
    finally:
        if existing_conn is None:
            conn.close()


def get_dashboard_summary() -> Dict[str, Any]:
    """Aggregates high-level analytics for UI dashboard tiles using a single shared database connection."""
    from mistakes.mastery import calculate_subject_mastery

    conn = get_db_connection()
    try:
        cursor = conn.cursor()

        # Query total exams and overall average score across MCQ and Written exams
        cursor.execute(
            """
            SELECT 
                (SELECT COUNT(*) FROM mcq_exams) + (SELECT COUNT(*) FROM written_exams) AS total_exams,
                (SELECT AVG(score) FROM mcq_exams) AS avg_mcq_score
            """
        )
        exam_row = cursor.fetchone()
        total_exams = exam_row[0] if exam_row and exam_row[0] is not None else 0
        overall_avg_score = round(exam_row[1], 2) if (exam_row and exam_row[1] is not None) else 0.0

        # Query due mistakes from revision_schedules
        today_str = datetime.now().strftime("%Y-%m-%d")
        cursor.execute(
            "SELECT COUNT(*) FROM revision_schedules WHERE next_review_date <= ? AND next_review_date != ''",
            (today_str,),
        )
        due_mistakes = cursor.fetchone()[0]

        streak_info = calculate_study_streak(existing_conn=conn)
        subject_mastery = calculate_subject_mastery(existing_conn=conn)

        return {
            "total_exams_taken": total_exams,
            "overall_average_score": overall_avg_score,
            "due_mistakes_count": due_mistakes,
            "current_streak_days": streak_info["current_streak_days"],
            "mastery_by_subject": subject_mastery,
        }
    finally:
        conn.close()
