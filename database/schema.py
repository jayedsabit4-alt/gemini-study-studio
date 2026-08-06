"""SQLite Database Table DDL Statements for Notebook-Centric Architecture."""

CREATE_NOTEBOOKS_TABLE = """
CREATE TABLE IF NOT EXISTS notebooks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL UNIQUE,
    description TEXT DEFAULT '',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

CREATE_NOTES_TABLE = """
CREATE TABLE IF NOT EXISTS notes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    notebook_id INTEGER NOT NULL,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    note_type TEXT DEFAULT 'General' CHECK (note_type IN ('General', 'Generated Questions', 'Mistake Reminder')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (notebook_id) REFERENCES notebooks(id) ON DELETE CASCADE
);
"""

CREATE_SUBJECTS_TABLE = """
CREATE TABLE IF NOT EXISTS subjects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

CREATE_CHAPTERS_TABLE = """
CREATE TABLE IF NOT EXISTS chapters (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    subject_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (subject_id) REFERENCES subjects(id) ON DELETE CASCADE
);
"""

CREATE_DOCUMENTS_TABLE = """
CREATE TABLE IF NOT EXISTS documents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    notebook_id INTEGER,
    subject_id INTEGER,
    chapter_id INTEGER,
    name TEXT NOT NULL,
    file_type TEXT NOT NULL,
    file_path TEXT,
    text_content TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (notebook_id) REFERENCES notebooks(id) ON DELETE CASCADE,
    FOREIGN KEY (subject_id) REFERENCES subjects(id) ON DELETE SET NULL,
    FOREIGN KEY (chapter_id) REFERENCES chapters(id) ON DELETE SET NULL
);
"""

CREATE_QUESTIONS_TABLE = """
CREATE TABLE IF NOT EXISTS questions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    notebook_id INTEGER,
    subject_id INTEGER,
    chapter_id INTEGER,
    question_text TEXT NOT NULL,
    options_json TEXT,
    correct_answer TEXT NOT NULL,
    explanation TEXT,
    question_type TEXT DEFAULT 'MCQ' CHECK (question_type IN ('MCQ', 'Written', 'TrueFalse', 'FillBlank')),
    difficulty TEXT DEFAULT 'Medium' CHECK (difficulty IN ('Easy', 'Medium', 'Hard')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (notebook_id) REFERENCES notebooks(id) ON DELETE CASCADE,
    FOREIGN KEY (subject_id) REFERENCES subjects(id) ON DELETE SET NULL
);
"""

CREATE_MCQ_EXAMS_TABLE = """
CREATE TABLE IF NOT EXISTS mcq_exams (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    notebook_id INTEGER,
    subject_id INTEGER,
    title TEXT NOT NULL,
    total_questions INTEGER NOT NULL,
    score REAL NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (notebook_id) REFERENCES notebooks(id) ON DELETE CASCADE
);
"""

CREATE_WRITTEN_EXAMS_TABLE = """
CREATE TABLE IF NOT EXISTS written_exams (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    notebook_id INTEGER,
    subject_id INTEGER,
    title TEXT NOT NULL,
    total_score REAL NOT NULL,
    feedback_json TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (notebook_id) REFERENCES notebooks(id) ON DELETE CASCADE
);
"""

CREATE_MISTAKES_TABLE = """
CREATE TABLE IF NOT EXISTS mistakes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    notebook_id INTEGER,
    question_id INTEGER NOT NULL,
    exam_id INTEGER,
    wrong_count INTEGER DEFAULT 0,
    correct_count INTEGER DEFAULT 0,
    last_attempted TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (notebook_id) REFERENCES notebooks(id) ON DELETE CASCADE,
    FOREIGN KEY (question_id) REFERENCES questions(id) ON DELETE CASCADE
);
"""

CREATE_REVISION_SCHEDULES_TABLE = """
CREATE TABLE IF NOT EXISTS revision_schedules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    question_id INTEGER NOT NULL,
    easiness_factor REAL DEFAULT 2.5,
    interval INTEGER DEFAULT 1,
    repetitions INTEGER DEFAULT 0,
    next_review_date TEXT DEFAULT '',
    FOREIGN KEY (question_id) REFERENCES questions(id) ON DELETE CASCADE
);
"""

ALL_SCHEMA_STATEMENTS = (
    CREATE_NOTEBOOKS_TABLE,
    CREATE_NOTES_TABLE,
    CREATE_SUBJECTS_TABLE,
    CREATE_CHAPTERS_TABLE,
    CREATE_DOCUMENTS_TABLE,
    CREATE_QUESTIONS_TABLE,
    CREATE_MCQ_EXAMS_TABLE,
    CREATE_WRITTEN_EXAMS_TABLE,
    CREATE_MISTAKES_TABLE,
    CREATE_REVISION_SCHEDULES_TABLE,
)
