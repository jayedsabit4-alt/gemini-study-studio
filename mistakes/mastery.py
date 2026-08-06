from database.database import get_connection

def get_chapter_mastery(subject: str):
    """Calculates accuracy percentage and star ratings per chapter."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT chapter, SUM(correct_count) as total_correct, SUM(wrong_count) as total_wrong
            FROM question_mistakes
            WHERE subject = ?
            GROUP BY chapter
        """, (subject,))
        
        results = []
        for row in cursor.fetchall():
            tot = row["total_correct"] + row["total_wrong"]
            acc = (row["total_correct"] / tot) * 100 if tot > 0 else 0
            stars = "★" * int(acc // 20) + "☆" * (5 - int(acc // 20))
            results.append({"chapter": row["chapter"], "accuracy": round(acc, 1), "stars": stars})
        return results
