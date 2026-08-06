from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class Subject:
    id: Optional[int]
    name: str
    created_at: Optional[datetime] = None


@dataclass
class Chapter:
    id: Optional[int]
    subject_id: int
    name: str
    created_at: Optional[datetime] = None


@dataclass
class Document:
    id: Optional[int]
    subject_id: Optional[int]
    chapter_id: Optional[int]
    name: str
    file_type: str
    text_content: str
    created_at: Optional[datetime] = None


@dataclass
class ChatHistory:
    id: Optional[int]
    thread_title: str
    role: str
    content: str
    timestamp: Optional[datetime] = None


@dataclass
class Question:
    id: Optional[int]
    subject_id: Optional[int]
    chapter_id: Optional[int]
    question_text: str
    options_json: str  # Store options as JSON array string: ["A", "B", "C", "D"]
    correct_answer: str
    explanation: str
    created_at: Optional[datetime] = None


@dataclass
class MCQExam:
    id: Optional[int]
    subject_id: Optional[int]
    title: str
    total_questions: int
    score: float
    created_at: Optional[datetime] = None


@dataclass
class WrittenExam:
    id: Optional[int]
    subject_id: Optional[int]
    title: str
    total_score: float
    feedback_json: str  # Structured rubric score breakdown
    created_at: Optional[datetime] = None


@dataclass
class Mistake:
    id: Optional[int]
    question_id: int
    wrong_count: int
    correct_count: int
    last_attempted: Optional[datetime] = None


@dataclass
class RevisionSchedule:
    id: Optional[int]
    question_id: int
    easiness_factor: float
    interval: int
    repetitions: int
    next_review_date: str  # YYYY-MM-DD format


@dataclass
class Analytics:
    id: Optional[int]
    subject_id: Optional[int]
    metric_name: str
    metric_value: float
    recorded_at: Optional[datetime] = None
