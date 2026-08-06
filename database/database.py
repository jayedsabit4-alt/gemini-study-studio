import sqlite3

DB_NAME = "study.db"


def get_connection():
    """Returns a SQLite connection with row factory and foreign keys enabled."""
    conn = sqlite3.connect(DB_NAME, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def init_db():
    """Initializes all 15 relational schema tables automatically when app starts."""
    with get_connection() as conn:
        cursor = conn.cursor()

        # 1. Subjects Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS subjects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 2. Chapters Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS chapters (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                subject_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (subject_id) REFERENCES subjects(id) ON DELETE CASCADE,
                UNIQUE(subject_id, name)
            )
        """)

        # 3. Documents Table (Added file_path)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                subject_id INTEGER,
                chapter_id INTEGER,
                name TEXT NOT NULL,
                file_type TEXT NOT NULL,
                file_path TEXT,
                text_content TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (subject_id) REFERENCES subjects(id) ON DELETE SET NULL,
                FOREIGN KEY (chapter_id) REFERENCES chapters(id) ON DELETE SET NULL
            )
        """)

        # 4. Chat Threads Table (Uses ID primary key)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS chat_threads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT UNIQUE NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 5. Chat History Table (Referenced by thread_id)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS chat_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                thread_id INTEGER NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (thread_id) REFERENCES chat_threads(id) ON DELETE CASCADE
            )
        """)

        # 6. Questions Master Bank (Added type, difficulty, source, page_number)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS questions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                subject_id INTEGER,
                chapter_id INTEGER,
                question_text TEXT UNIQUE NOT NULL,
                options_json TEXT,
                correct_answer TEXT NOT NULL,
                explanation TEXT,
                question_type TEXT DEFAULT 'MCQ',
                difficulty TEXT DEFAULT 'Medium',
                source TEXT,
                page_number INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (subject_id) REFERENCES subjects(id) ON DELETE SET NULL,
                FOREIGN KEY (chapter_id) REFERENCES chapters(id) ON DELETE SET NULL
            )
        """)

        # 7. MCQ Exams Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS mcq_exams (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                subject_id INTEGER,
                title TEXT NOT NULL,
                total_questions INTEGER NOT NULL,
                score REAL DEFAULT 0.0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (subject_id) REFERENCES subjects(id) ON DELETE SET NULL
            )
        """)

        # 8. Exam Questions Breakdown Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS exam_questions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                exam_id INTEGER NOT NULL,
                question_id INTEGER NOT NULL,
                user_answer TEXT,
                is_correct BOOLEAN,
                time_taken_seconds INTEGER,
                FOREIGN KEY (exam_id) REFERENCES mcq_exams(id) ON DELETE CASCADE,
                FOREIGN KEY (question_id) REFERENCES questions(id) ON DELETE CASCADE
            )
        """)

        # 9. Written Exams Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS written_exams (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                subject_id INTEGER,
                title TEXT NOT NULL,
                total_score REAL DEFAULT 0.0,
                feedback_json TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (subject_id) REFERENCES subjects(id) ON DELETE SET NULL
            )
        """)

        # 10. Question Attempts Log (Detailed Granular Performance Engine)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS question_attempts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                question_id INTEGER NOT NULL,
                exam_id INTEGER,
                is_correct BOOLEAN NOT NULL,
                response_time_seconds INTEGER DEFAULT 0,
                attempted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (question_id) REFERENCES questions(id) ON DELETE CASCADE,
                FOREIGN KEY (exam_id) REFERENCES mcq_exams(id) ON DELETE SET NULL
            )
        """)

        # 11. Mistakes Engine Table (Linked with Optional Exam context)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS mistakes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                question_id INTEGER NOT NULL,
                exam_id INTEGER,
                wrong_count INTEGER DEFAULT 0,
                correct_count INTEGER DEFAULT 0,
                last_attempted TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (question_id) REFERENCES questions(id) ON DELETE CASCADE,
                FOREIGN KEY (exam_id) REFERENCES mcq_exams(id) ON DELETE SET NULL,
                UNIQUE(question_id, exam_id)
            )
        """)

        # 12. Chapter Mastery Cache Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS mastery (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                subject_id INTEGER NOT NULL,
                chapter_id INTEGER NOT NULL,
                mastery_percentage REAL DEFAULT 0.0,
                status TEXT DEFAULT 'Unreviewed',
                last_reviewed TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (subject_id) REFERENCES subjects(id) ON DELETE CASCADE,
                FOREIGN KEY (chapter_id) REFERENCES chapters(id) ON DELETE CASCADE,
                UNIQUE(subject_id, chapter_id)
            )
        """)

        # 13. Flashcards Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS flashcards (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                question_id INTEGER,
                front_text TEXT NOT NULL,
                back_text TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (question_id) REFERENCES questions(id) ON DELETE SET NULL
            )
        """)

        # 14. Revision Schedule Table (SuperMemo SM-2 Spaced Repetition)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS revision_schedule (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                question_id INTEGER UNIQUE NOT NULL,
                easiness_factor REAL DEFAULT 2.5,
                interval INTEGER DEFAULT 1,
                repetitions INTEGER DEFAULT 0,
                next_review_date TEXT NOT NULL,
                FOREIGN KEY (question_id) REFERENCES questions(id) ON DELETE CASCADE
            )
        """)

        # 15. Settings Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
        """)

        # 16. Analytics Summary Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS analytics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                subject_id INTEGER,
                metric_name TEXT NOT NULL,
                metric_value REAL NOT NULL,
                recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (subject_id) REFERENCES subjects(id) ON DELETE CASCADE
            )
        """)

        # Default fallback thread and default app settings
        cursor.execute("INSERT OR IGNORE INTO chat_threads (id, title) VALUES (1, 'Default Chat')")
        cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('theme', 'dark')")
        cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('preferred_model', 'openrouter/free')")
        
        conn.commit()


if __name__ == "__main__":
    init_db()
    print("Database schema successfully upgraded and initialized as 'study.db'.")
