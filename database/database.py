import sqlite3

DB_NAME = "study.db"


def get_connection():
    """Returns a SQLite connection with row factory and foreign keys enabled."""
    conn = sqlite3.connect(DB_NAME, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def init_db():
    """Initializes all relational schema tables automatically when app starts."""
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

        # 3. Documents Table (RAG Context Sources)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                subject_id INTEGER,
                chapter_id INTEGER,
                name TEXT NOT NULL,
                file_type TEXT NOT NULL,
                text_content TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (subject_id) REFERENCES subjects(id) ON DELETE SET NULL,
                FOREIGN KEY (chapter_id) REFERENCES chapters(id) ON DELETE SET NULL
            )
        """)

        # 4. Chat Threads Table (Tracks last active update for sorting latest first)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS chat_threads (
                title TEXT PRIMARY KEY,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 5. Chat History Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS chat_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                thread_title TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (thread_title) REFERENCES chat_threads(title) ON DELETE CASCADE
            )
        """)

        # 6. Questions Master Bank (Deduplicated via UNIQUE constraint on question_text)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS questions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                subject_id INTEGER,
                chapter_id INTEGER,
                question_text TEXT UNIQUE NOT NULL,
                options_json TEXT,
                correct_answer TEXT NOT NULL,
                explanation TEXT,
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

        # 8. Written Exams Table
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

        # 9. Mistakes Engine Table (Deduplicated mistake counter per question)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS mistakes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                question_id INTEGER UNIQUE NOT NULL,
                wrong_count INTEGER DEFAULT 0,
                correct_count INTEGER DEFAULT 0,
                last_attempted TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (question_id) REFERENCES questions(id) ON DELETE CASCADE
            )
        """)

        # 10. Revision Schedule Table (SuperMemo SM-2 Spaced Repetition)
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

        # 11. Analytics Table
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

        # Insert default fallback chat thread
        cursor.execute(
            "INSERT OR IGNORE INTO chat_threads (title) VALUES ('Default Chat')"
        )
        conn.commit()


if __name__ == "__main__":
    init_db()
    print("Database schema successfully initialized as 'study.db'.")
