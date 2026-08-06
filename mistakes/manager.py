"""SuperMemo SM-2 Spaced Repetition Calculation Engine."""

from datetime import datetime, timedelta
import logging
import math
from typing import Tuple, TypedDict

from database.database import get_db_connection

logger = logging.getLogger(__name__)


class MistakeUpdateResult(TypedDict):
    mistake_id: int
    new_interval_days: int
    new_ease_factor: float
    new_repetitions: int
    next_review_at: str


def calculate_sm2(
    quality: int,
    previous_interval: int = 0,
    previous_ef: float = 2.5,
    repetitions: int = 0,
) -> Tuple[int, float, int, datetime]:
    """Calculates next review interval, ease factor, and repetition count via SM-2.

    Args:
        quality: Performance rating from 0 (complete blackout) to 5 (perfect recall).
        previous_interval: Previous inter-repetition interval in days (>= 0).
        previous_ef: Previous Ease Factor (>= 1.3).
        repetitions: Number of successful consecutive reviews (>= 0).

    Returns:
        Tuple containing (next_interval_days, new_ease_factor, new_repetitions, next_review_date).
    """
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


def update_mistake_review(mistake_id: int, review_quality: int) -> MistakeUpdateResult:
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

        prev_interval, prev_ef, prev_reps = row
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
