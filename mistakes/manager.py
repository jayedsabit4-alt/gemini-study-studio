"""SuperMemo SM-2 Spaced Repetition Calculation Engine."""

from datetime import datetime, timedelta
import logging
import math
from typing import Tuple, TypedDict

from database.database import get_db_connection

logger = logging.getLogger(__name__)


class MistakeUpdateResult(TypedDict):
    schedule_id: int
    question_id: int
    new_interval_days: int
    new_ease_factor: float
    new_repetitions: int
    next_review_date: str


def calculate_sm2(
    quality: int,
    previous_interval: int = 1,
    previous_ef: float = 2.5,
    repetitions: int = 0,
) -> Tuple[int, float, int, datetime]:
    """Calculates next review interval, ease factor, and repetition count via SM-2."""
    if not isinstance(quality, int) or not (0 <= quality <= 5):
        raise ValueError(f"Quality rating must be an integer between 0 and 5, received {quality}.")
    if previous_interval < 0:
        raise ValueError(f"previous_interval must be >= 0, received {previous_interval}.")
    if previous_ef < 1.3:
        raise ValueError(f"previous_ef must be >= 1.3, received {previous_ef}.")
    if repetitions < 0:
        raise ValueError(f"repetitions must be >= 0, received {repetitions}.")

    q = quality
    new_ef = max(1.3, previous_ef + (0.1 - (5 - q) * (0.08 + (5 - q) * 0.02)))

    if q < 3:
        new_repetitions = 0
        new_interval = 1
    else:
        if repetitions == 0:
            new_interval = 1
        elif repetitions == 1:
            new_interval = 6
        else:
            new_interval = math.ceil(previous_interval * new_ef)
        new_repetitions = repetitions + 1

    next_review_date = datetime.now() + timedelta(days=new_interval)
    return new_interval, round(new_ef, 3), new_repetitions, next_review_date


def update_mistake_review(question_id: int, review_quality: int) -> MistakeUpdateResult:
    """Updates revision_schedules record with new SM-2 parameters after a review session."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, interval, easiness_factor, repetitions FROM revision_schedules WHERE question_id = ?",
            (question_id,),
        )
        row = cursor.fetchone()

        if not row:
            # Initialize schedule row if missing
            cursor.execute(
                "INSERT INTO revision_schedules (question_id, easiness_factor, interval, repetitions) VALUES (?, 2.5, 1, 0)",
                (question_id,),
            )
            conn.commit()
            cursor.execute(
                "SELECT id, interval, easiness_factor, repetitions FROM revision_schedules WHERE question_id = ?",
                (question_id,),
            )
            row = cursor.fetchone()

        sched_id, prev_interval, prev_ef, prev_reps = row
        new_interval, new_ef, new_reps, next_review_dt = calculate_sm2(
            quality=review_quality,
            previous_interval=prev_interval or 1,
            previous_ef=prev_ef or 2.5,
            repetitions=prev_reps or 0,
        )

        next_rev_str = next_review_dt.strftime("%Y-%m-%d")

        cursor.execute(
            """
            UPDATE revision_schedules
            SET interval = ?, easiness_factor = ?, repetitions = ?, next_review_date = ?
            WHERE id = ?
            """,
            (new_interval, new_ef, new_reps, next_rev_str, sched_id),
        )
        conn.commit()

        return {
            "schedule_id": sched_id,
            "question_id": question_id,
            "new_interval_days": new_interval,
            "new_ease_factor": new_ef,
            "new_repetitions": new_reps,
            "next_review_date": next_rev_str,
        }
    finally:
        conn.close()
