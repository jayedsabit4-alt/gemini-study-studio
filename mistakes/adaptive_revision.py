from database.database import get_connection

def fetch_adaptive_mistakes(subject: str, limit: int = 10):
    """Fetches high-priority weak spots ordered by highest error frequency."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT question_text, correct_answer, explanation, wrong_count, correct_count, chapter
            FROM question_mistakes
            WHERE subject = ? AND wrong_count > correct_count
            ORDER BY (wrong_count - correct_count) DESC, last_attempted ASC
            LIMIT ?
        """, (subject, limit))
        return [dict(row) for row in cursor.fetchall()]
