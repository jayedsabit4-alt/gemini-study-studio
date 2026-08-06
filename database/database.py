import sqlite3

DB_NAME = "study_platform.db"

def get_connection():
    conn = sqlite3.connect(DB_NAME, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_connection() as conn:
        cursor = conn.cursor()
        
        # Threads (ORDER BY updated_at DESC for latest first)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS threads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT UNIQUE NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Chat Messages
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS chat_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                thread_title TEXT,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (thread_title) REFERENCES threads(title) ON DELETE CASCADE
            )
        """)
        
        # Deduplicated Mistakes (UNIQUE constraint on question_text)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS question_mistakes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                subject TEXT NOT NULL,
                chapter TEXT DEFAULT 'General',
                question_text TEXT UNIQUE NOT NULL,
                correct_answer TEXT,
                explanation TEXT,
                wrong_count INTEGER DEFAULT 1,
                correct_count INTEGER DEFAULT 0,
                last_attempted TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Written Evaluations with Rubric Breakdown
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS written_evaluations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                subject TEXT NOT NULL,
                question_title TEXT NOT NULL,
                content_score INTEGER,
                logic_score INTEGER,
                terminology_score INTEGER,
                grammar_score INTEGER,
                total_score INTEGER,
                feedback_json TEXT,
                attempted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cursor.execute("INSERT OR IGNORE INTO threads (title) VALUES ('Default Chat')")
        conn.commit()

# --- THREAD DB QUERIES ---
def fetch_all_threads():
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT title FROM threads ORDER BY updated_at DESC")
        return [row["title"] for row in cursor.fetchall()]

def create_thread(title: str):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("INSERT OR IGNORE INTO threads (title, updated_at) VALUES (?, CURRENT_TIMESTAMP)", (title,))
        conn.commit()

def delete_thread(title: str):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM threads WHERE title = ?", (title,))
        cursor.execute("DELETE FROM chat_messages WHERE thread_title = ?", (title,))
        conn.commit()

def add_chat_message(thread_title: str, role: str, content: str):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO chat_messages (thread_title, role, content) VALUES (?, ?, ?)", (thread_title, role, content))
        cursor.execute("UPDATE threads SET updated_at = CURRENT_TIMESTAMP WHERE title = ?", (thread_title,))
        conn.commit()

def fetch_thread_messages(thread_title: str):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT role, content FROM chat_messages WHERE thread_title = ? ORDER BY timestamp ASC", (thread_title,))
        return [dict(row) for row in cursor.fetchall()]
