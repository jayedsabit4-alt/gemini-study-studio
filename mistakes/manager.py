"""Mistakes Manager & SuperMemo SM-2 Spaced Repetition Engine."""

from datetime import datetime, timedelta
import logging
import math
from typing import Any, Dict, List, Optional, Tuple

from database.database import get_db_connection

logger = logging.getLogger(__name__)


def calculate_sm2(
    quality: int,
    previous_interval: int = 0,
    previous_ef: float = 2.5,
    repetitions: int = 0,
) -> Tuple[int, float, int, datetime]:
    """Calculates the next review interval, ease factor, and review count using SuperMemo SM-2.

    Args:
        quality: Performance rating from 0 (complete blackout) to 5 (perfect recall).
        previous_interval: Previous inter-repetition interval in days.
        previous_ef: Previous Ease Factor (default 2.5).
        repetitions: Number of successful consecutive reviews.

    Returns:
        Tuple containing (next_interval_days, new_ease_factor, new_repetitions, next_review_date).
    """
    if not isinstance(quality, int) or not (0 <= quality <= 5):
        raise ValueError(f"Quality rating must be an integer between 0 and 5, received {quality}.")

    q = quality

    # Calculate new Ease Factor (EF)
    new_ef = previous_ef + (0.1 - (5 - q) * (0.08 + (5 - q) * 0.02))
    new_ef = max(1.3, new_ef)

    if q < 3:
        # Failed recall resets repetition count and forces immediate 1-day retry
        new_repetitions = 0
        new_interval = 1
    else:
        # Successful recall advances review interval schedule
        if repetitions == 0:
            new_interval = 1
        elif repetitions == 1:
            new_interval = 6
        else:
            new_interval = math.ceil(previous_interval * new_ef)
        
        new_repetitions = repetitions + 1

    next_review_date = datetime.now() + timedelta(days=new_interval)

    return new_interval, round(new_ef, 3), new_repetitions, next_review_date


def log_mistake(
    subject: str,
    chapter: str,
    question_text: str,
    user_answer: str,
    correct_answer: str,
    explanation: str = "",
    exam_type: str = "MCQ",
) -> int:
    """Logs a new wrong answer entry to the SQLite database with initial SM-2 defaults."""
    now = datetime.now()
    next_review = now + timedelta(days=1)
    conn = get_db_connection()

    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO mistake_logs (
                subject, chapter, question_text, user_answer, correct_answer,
                explanation, exam_type, ease_factor, interval_days, repetitions,
                next_review_at, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, 2.5, 1, 0, ?, ?)
            """,
            (
                subject,
                chapter,
                question_text,
                user_answer,
                correct_answer,
                explanation,
                exam_type,
                next_review.isoformat(),
                now.isoformat(),
            ),
        )

        log_id = cursor.lastrowid
        conn.commit()
        logger.info(f"Logged mistake #{log_id} for subject '{subject}' - {exam_type}")
        return log_id
    finally:
        conn.close()


def get_due_mistakes(subject: Optional[str] = None, limit: int = 20) -> List[Dict[str, Any]]:
    """Retrieves all mistakes scheduled for revision on or before current time."""
    now_str = datetime.now().isoformat()
    conn = get_db_connection()

    try:
        cursor = conn.cursor()
        if subject:
            cursor.execute(
                """
                SELECT id, subject, chapter, question_text, user_answer, correct_answer,
                       explanation, exam_type, ease_factor, interval_days, repetitions, next_review_at
                FROM mistake_logs
                WHERE next_review_at <= ? AND subject = ?
                ORDER BY next_review_at ASC
                LIMIT ?
                """,
                (now_str, subject, limit),
            )
        else:
            cursor.execute(
                """
                SELECT id, subject, chapter, question_text, user_answer, correct_answer,
                       explanation, exam_type, ease_factor, interval_days, repetitions, next_review_at
                FROM mistake_logs
                WHERE next_review_at <= ?
                ORDER BY next_review_at ASC
                LIMIT ?
                """,
                (now_str, limit),
            )

        rows = cursor.fetchall()
        return [
            {
                "id": r[0],
                "subject": r[1],
                "chapter": r[2],
                "question_text": r[3],
                "user_answer": r[4],
                "correct_answer": r[5],
                "explanation": r[6],
                "exam_type": r[7],
                "ease_factor": r[8],
                "interval_days": r[9],
                "repetitions": r[10],
                "next_review_at": r[11],
            }
            for r in rows
        ]
    finally:
        conn.close()


def update_mistake_review(mistake_id: int, review_quality: int) -> Dict[str, Any]:
    """Updates mistake record with new SM-2 parameters after a revision session."""
    conn = get_db_connection()

    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT interval_days, ease_factor, repetitions FROM mistake_logs WHERE id = ?",
            (mistake_id,),
        )
        row = cursor.fetchone()

        if not row:
            raise ValueError(f"Mistake record #{mistake_id} not found.")

        prev_interval, prev_ef, prev_reps = row[0], row[1], row[2]

        new_interval, new_ef, new_reps, next_review_date = calculate_sm2(
            quality=review_quality,
            previous_interval=prev_interval,
            previous_ef=prev_ef,
            repetitions=prev_reps,
        )

        cursor.execute(
            """
            UPDATE mistake_logs
            SET interval_days = ?, ease_factor = ?, repetitions = ?, next_review_at = ?
            WHERE id = ?
            """,
            (new_interval, new_ef, new_reps, next_review_date.isoformat(), mistake_id),
        )

        conn.commit()

        return {
            "mistake_id": mistake_id,
            "new_interval_days": new_interval,
            "new_ease_factor": new_ef,
            "new_repetitions": new_reps,
            "next_review_at": next_review_date.isoformat(),
        }
    finally:
        conn.close()
