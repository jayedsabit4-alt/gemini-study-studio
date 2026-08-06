"""Subject Mastery & Performance Analytics Engine."""

import logging
import sqlite3
from typing import Any, Dict, List, Optional
from database.database import get_db_connection

logger = logging.getLogger(__name__)


def calculate_subject_mastery(
    existing_conn: Optional[sqlite3.Connection] = None,
) -> List[Dict[str, Any]]:
    """Calculates accuracy percentages and mastery tiers per subject by querying mcq_exams."""
    conn = existing_conn or get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT s.name AS subject,
                   COUNT(e.id) AS total_exams,
                   AVG(e.score) AS average_score,
                   MAX(e.score) AS highest_score
            FROM mcq_exams e
            JOIN subjects s ON e.subject_id = s.id
            GROUP BY s.id, s.name
            ORDER BY average_score DESC
            """
        )
        rows = cursor.fetchall()

        mastery_report = []
        for r in rows:
            avg_score = round(r[2], 2) if r[2] is not None else 0.0
            max_score = round(r[3], 2) if r[3] is not None else 0.0

            if avg_score >= 85.0:
                tier = "Mastered"
            elif avg_score >= 65.0:
                tier = "Competent"
            elif avg_score >= 45.0:
                tier = "Developing"
            else:
                tier = "Needs Focus"

            mastery_report.append({
                "subject": r[0],
                "total_exams": r[1],
                "average_score": avg_score,
                "highest_score": max_score,
                "mastery_tier": tier,
            })
        return mastery_report
    finally:
        if existing_conn is None:
            conn.close()
