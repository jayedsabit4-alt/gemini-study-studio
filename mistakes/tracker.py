"""Mistake Logging and Spaced Repetition Tracking Utilities."""

from datetime import datetime
import logging
from typing import Any, Dict, List, Optional
from database.database import get_db_connection

logger = logging.getLogger(__name__)


def log_mistake(
    question_id: Optional[int] = None,
    exam_id: Optional[int] = None,
    is_correct: bool = False,
    subject: Optional[str] = None,
    chapter: Optional[str] = None,
    question_text: str = "",
    user_answer: str = "",
    correct_answer: str = "",
    explanation: str = "",
    exam_type: str = "MCQ",
) -> int:
    """Logs or upserts a question mistake into the database and returns the question/mistake ID."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()

        # Resolve or insert question entry if question_id is not directly passed
        if question_id is None:
            subj_id = None
            if subject:
                cursor.execute("SELECT id FROM subjects WHERE name = ?", (subject,))
                s_row = cursor.fetchone()
                if s_row:
                    subj_id = s_row[0]
                else:
                    cursor.execute("INSERT INTO subjects (name) VALUES (?)", (subject,))
                    subj_id = cursor.lastrowid

            cursor.execute(
                "INSERT INTO questions (subject_id, question_text, correct_answer, explanation, question_type) VALUES (?, ?, ?, ?, ?)",
                (subj_id, question_text or "Sample Question", correct_answer, explanation, exam_type),
            )
            question_id = cursor.lastrowid

        cursor.execute("SELECT id, wrong_count, correct_count FROM mistakes WHERE question_id = ?", (question_id,))
        row = cursor.fetchone()

        if row:
            m_id, wrong, correct = row
            if is_correct:
                cursor.execute(
                    "UPDATE mistakes SET correct_count = correct_count + 1, last_attempted = CURRENT_TIMESTAMP WHERE id = ?",
                    (m_id,),
                )
            else:
                cursor.execute(
                    "UPDATE mistakes SET wrong_count = wrong_count + 1, last_attempted = CURRENT_TIMESTAMP WHERE id = ?",
                    (m_id,),
                )
        else:
            wrong_val = 0 if is_correct else 1
            correct_val = 1 if is_correct else 0
            cursor.execute(
                "INSERT INTO mistakes (question_id, exam_id, wrong_count, correct_count) VALUES (?, ?, ?, ?)",
                (question_id, exam_id, wrong_val, correct_val),
            )

        # Initialize revision schedule entry if missing
        cursor.execute("SELECT id FROM revision_schedules WHERE question_id = ?", (question_id,))
        if not cursor.fetchone():
            today_str = datetime.now().strftime("%Y-%m-%d")
            cursor.execute(
                "INSERT INTO revision_schedules (question_id, easiness_factor, interval, repetitions, next_review_date) VALUES (?, 2.5, 1, 0, ?)",
                (question_id, today_str),
            )

        conn.commit()
        return question_id
    finally:
        conn.close()


def record_question_attempt(
    question_id: int, is_correct: bool, response_time_seconds: int = 0, exam_id: Optional[int] = None
):
    """Records attempt in question_attempts table and updates mistake tracking."""
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


def get_due_mistakes(subject: Optional[str] = None, limit: int = 20) -> List[Dict[str, Any]]:
    """Fetches questions due for spaced repetition revision."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        today_str = datetime.now().strftime("%Y-%m-%d")

        query = """
            SELECT q.id, q.question_text, q.options_json, q.correct_answer, q.explanation,
                   r.easiness_factor, r.interval, r.repetitions, r.next_review_date
            FROM revision_schedules r
            JOIN questions q ON r.question_id = q.id
            LEFT JOIN subjects s ON q.subject_id = s.id
            WHERE r.next_review_date <= ? AND r.next_review_date != ''
        """
        params = [today_str]

        if subject:
            query += " AND s.name = ?"
            params.append(subject)

        query += " ORDER BY r.next_review_date ASC LIMIT ?"
        params.append(limit)

        cursor.execute(query, params)
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
