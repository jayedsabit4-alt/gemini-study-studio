"""Mistake Logging and Spaced Repetition Tracking Utilities."""

from datetime import datetime
import logging
from typing import Any, Dict, List, Optional
from database.database import get_db_connection

logger = logging.getLogger(__name__)


def log_mistake(question_id: int, exam_id: Optional[int] = None, is_correct: bool = False):
    """Upserts a question attempt into mistakes and revision_schedules tables."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id, wrong_count, correct_count FROM mistakes WHERE question_id = ?", (question_id,))
        row = cursor.fetchone()

        if row:
            mistake_id, wrong, correct = row
            if is_correct:
                cursor.execute(
                    "UPDATE mistakes SET correct_count = correct_count + 1, last_attempted = CURRENT_TIMESTAMP WHERE id = ?",
                    (mistake_id,),
                )
            else:
                cursor.execute(
                    "UPDATE mistakes SET wrong_count = wrong_count + 1, last_attempted = CURRENT_TIMESTAMP WHERE id = ?",
                    (mistake_id,),
                )
        else:
            wrong_val = 0 if is_correct else 1
            correct_val = 1 if is_correct else 0
            cursor.execute(
                "INSERT INTO mistakes (question_id, exam_id, wrong_count, correct_count) VALUES (?, ?, ?, ?)",
                (question_id, exam_id, wrong_val, correct_val),
            )

        # Initialize schedule entry if missing
        cursor.execute("SELECT id FROM revision_schedules WHERE question_id = ?", (question_id,))
        if not cursor.fetchone():
            today_str = datetime.now().strftime("%Y-%m-%d")
            cursor.execute(
                "INSERT INTO revision_schedules (question_id, easiness_factor, interval, repetitions, next_review_date) VALUES (?, 2.5, 1, 0, ?)",
                (question_id, today_str),
            )

        conn.commit()
    finally:
        conn.close()


def record_question_attempt(question_id: int, is_correct: bool, response_time_seconds: int = 0, exam_id: Optional[int] = None):
    """Records attempt in question_attempts and updates mistake trackers."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO question_attempts (question_id, exam_id, is_correct, response_time_seconds) VALUES (?, ?, ?, ?)",
            (question_id, exam_id, is_correct, response_time_seconds),
        )
        conn.commit()
    finally:
        conn.close()

    log_mistake(question_id=question_id, exam_id=exam_id, is_correct=is_correct)


def get_due_mistakes(limit: int = 20) -> List[Dict[str, Any]]:
    """Fetches questions that are due for revision based on revision_schedules."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        today_str = datetime.now().strftime("%Y-%m-%d")
        cursor.execute(
            """
            SELECT q.id, q.question_text, q.options_json, q.correct_answer, q.explanation,
                   r.easiness_factor, r.interval, r.repetitions, r.next_review_date
            FROM revision_schedules r
            JOIN questions q ON r.question_id = q.id
            WHERE r.next_review_date <= ? AND r.next_review_date != ''
            ORDER BY r.next_review_date ASC
            LIMIT ?
            """,
            (today_str, limit),
        )
        rows = cursor.fetchall()

        due_list = []
        for r in rows:
            due_list.append({
                "question_id": r[0],
                "question_text": r[1],
                "options_json": r[2],
                "correct_answer": r[3],
                "explanation": r[4],
                "easiness_factor": r[5],
                "interval": r[6],
                "repetitions": r[7],
                "next_review_date": r[8],
            })
        return due_list
    finally:
        conn.close()
