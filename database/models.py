"""Domain Model Dataclasses for System Entities."""

from dataclasses import dataclass
from datetime import date, datetime
from typing import Optional


@dataclass
class Subject:
    name: str
    id: Optional[int] = None
    created_at: Optional[datetime] = None


@dataclass
class Chapter:
    subject_id: int
    name: str
    id: Optional[int] = None
    created_at: Optional[datetime] = None


@dataclass
class Document:
    name: str
    file_type: str
    text_content: str
    id: Optional[int] = None
    subject_id: Optional[int] = None
    chapter_id: Optional[int] = None
    file_path: Optional[str] = None
    created_at: Optional[datetime] = None


@dataclass
class ChatThread:
    title: str
    id: Optional[int] = None
    updated_at: Optional[datetime] = None


@dataclass
class ChatHistory:
    thread_id: int
    role: str
    content: str
    id: Optional[int] = None
    timestamp: Optional[datetime] = None


@dataclass
class Question:
    question_text: str
    correct_answer: str
    id: Optional[int] = None
    subject_id: Optional[int] = None
    chapter_id: Optional[int] = None
    options_json: Optional[str] = None  # JSON array string: ["A", "B", "C", "D"]
    explanation: Optional[str] = None
    question_type: str = "MCQ"  # MCQ, Written, TrueFalse, FillBlank
    difficulty: str = "Medium"  # Easy, Medium, Hard
    source: Optional[str] = None
    page_number: Optional[int] = None
    created_at: Optional[datetime] = None


@dataclass
class MCQExam:
    title: str
    total_questions: int
    score: float
    id: Optional[int] = None
    subject_id: Optional[int] = None
    created_at: Optional[datetime] = None


@dataclass
class ExamQuestion:
    exam_id: int
    question_id: int
    id: Optional[int] = None
    user_answer: Optional[str] = None
    is_correct: Optional[bool] = None
    time_taken_seconds: Optional[int] = None


@dataclass
class WrittenExam:
    title: str
    total_score: float
    id: Optional[int] = None
    subject_id: Optional[int] = None
    feedback_json: Optional[str] = None
    created_at: Optional[datetime] = None


@dataclass
class QuestionAttempt:
    question_id: int
    is_correct: bool
    response_time_seconds: int
    id: Optional[int] = None
    exam_id: Optional[int] = None
    attempted_at: Optional[datetime] = None


@dataclass
class Mistake:
    question_id: int
    id: Optional[int] = None
    exam_id: Optional[int] = None
    wrong_count: int = 0
    correct_count: int = 0
    last_attempted: Optional[datetime] = None


@dataclass
class ChapterMastery:
    subject_id: int
    chapter_id: int
    id: Optional[int] = None
    mastery_percentage: float = 0.0
    status: str = "Unreviewed"  # Weak, Moderate, Strong, Mastered
    last_reviewed: Optional[datetime] = None


@dataclass
class Flashcard:
    front_text: str
    back_text: str
    id: Optional[int] = None
    question_id: Optional[int] = None
    created_at: Optional[datetime] = None


@dataclass
class RevisionSchedule:
    question_id: int
    id: Optional[int] = None
    easiness_factor: float = 2.5
    interval: int = 1
    repetitions: int = 0
    next_review_date: Optional[date] = None


@dataclass
class Setting:
    key: str
    value: str


@dataclass
class Analytics:
    metric_name: str
    metric_value: float
    id: Optional[int] = None
    subject_id: Optional[int] = None
    recorded_at: Optional[datetime] = None
