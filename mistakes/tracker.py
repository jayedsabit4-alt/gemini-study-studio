from database.database import get_connection

def record_question_attempt(subject: str, chapter: str, question_text: str, is_correct: bool, correct_ans: str = "", explanation: str = ""):
    """UPSERT: Updates counts if question exists, inserts if new."""
    with get_connection() as conn:
        cursor = conn.cursor()
        if is_correct:
            cursor.execute("""
                INSERT INTO question_mistakes (subject, chapter, question_text, correct_answer, explanation, wrong_count, correct_count, last_attempted)
                VALUES (?, ?, ?, ?, ?, 0, 1, CURRENT_TIMESTAMP)
                ON CONFLICT(question_text) DO UPDATE SET
                    correct_count = correct_count + 1,
                    last_attempted = CURRENT_TIMESTAMP
            """, (subject, chapter, question_text, correct_ans, explanation))
        else:
            cursor.execute("""
                INSERT INTO question_mistakes (subject, chapter, question_text, correct_answer, explanation, wrong_count, correct_count, last_attempted)
                VALUES (?, ?, ?, ?, ?, 1, 0, CURRENT_TIMESTAMP)
                ON CONFLICT(question_text) DO UPDATE SET
                    wrong_count = wrong_count + 1,
                    last_attempted = CURRENT_TIMESTAMP
            """, (subject, chapter, question_text, correct_ans, explanation))
        conn.commit()
