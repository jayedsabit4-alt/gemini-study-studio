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
    file_path: Optional[str]
    text_content: str
    created_at: Optional[datetime] = None


@dataclass
class ChatThread:
    id: Optional[int]
    title: str
    updated_at: Optional[datetime] = None


@dataclass
class ChatHistory:
    id: Optional[int]
    thread_id: int
    role: str
    content: str
    timestamp: Optional[datetime] = None


@dataclass
class Question:
    id: Optional[int]
    subject_id: Optional[int]
    chapter_id: Optional[int]
    question_text: str
    options_json: Optional[str]  # JSON array string: ["A", "B", "C", "D"]
    correct_answer: str
    explanation: Optional[str]
    question_type: str = "MCQ"  # MCQ, Written, TrueFalse, FillBlank
    difficulty: str = "Medium"  # Easy, Medium, Hard
    source: Optional[str] = None
    page_number: Optional[int] = None
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
class ExamQuestion:
    id: Optional[int]
    exam_id: int
    question_id: int
    user_answer: Optional[str]
    is_correct: Optional[bool]
    time_taken_seconds: Optional[int] = None


@dataclass
class WrittenExam:
    id: Optional[int]
    subject_id: Optional[int]
    title: str
    total_score: float
    feedback_json: Optional[str] = None
    created_at: Optional[datetime] = None


@dataclass
class QuestionAttempt:
    id: Optional[int]
    question_id: int
    exam_id: Optional[int]
    is_correct: bool
    response_time_seconds: int
    attempted_at: Optional[datetime] = None


@dataclass
class Mistake:
    id: Optional[int]
    question_id: int
    exam_id: Optional[int]
    wrong_count: int
    correct_count: int
    last_attempted: Optional[datetime] = None


@dataclass
class ChapterMastery:
    id: Optional[int]
    subject_id: int
    chapter_id: int
    mastery_percentage: float = 0.0
    status: str = "Unreviewed"  # Weak, Moderate, Strong, Mastered
    last_reviewed: Optional[datetime] = None


@dataclass
class Flashcard:
    id: Optional[int]
    question_id: Optional[int]
    front_text: str
    back_text: str
    created_at: Optional[datetime] = None


@dataclass
class RevisionSchedule:
    id: Optional[int]
    question_id: int
    easiness_factor: float = 2.5
    interval: int = 1
    repetitions: int = 0
    next_review_date: str = ""  # YYYY-MM-DD


@dataclass
class Setting:
    key: str
    value: str


@dataclass
class Analytics:
    id: Optional[int]
    subject_id: Optional[int]
    metric_name: str
    metric_value: float
    recorded_at: Optional[datetime] = None
