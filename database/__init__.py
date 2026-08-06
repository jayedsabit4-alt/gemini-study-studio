"""Database Package API."""

from .database import get_connection, get_db_connection, init_db
from .models import (
    Analytics,
    Chapter,
    ChapterMastery,
    ChatHistory,
    ChatThread,
    Document,
    ExamQuestion,
    Flashcard,
    MCQExam,
    Mistake,
    Question,
    QuestionAttempt,
    RevisionSchedule,
    Setting,
    Subject,
    WrittenExam,
)

__all__ = [
    "get_db_connection",
    "get_connection",
    "init_db",
    "Subject",
    "Chapter",
    "Document",
    "ChatThread",
    "ChatHistory",
    "Question",
    "MCQExam",
    "ExamQuestion",
    "WrittenExam",
    "QuestionAttempt",
    "Mistake",
    "ChapterMastery",
    "Flashcard",
    "RevisionSchedule",
    "Setting",
    "Analytics",
]
