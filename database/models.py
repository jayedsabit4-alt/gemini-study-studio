from dataclasses import dataclass
from datetime import datetime
from typing import Optional

@dataclass
class ChatThread:
    id: Optional[int]
    title: str
    updated_at: datetime

@dataclass
class QuestionMistake:
    id: Optional[int]
    subject: str
    chapter: str
    question_text: str
    correct_answer: str
    explanation: str
    wrong_count: int
    correct_count: int
    last_attempted: datetime
