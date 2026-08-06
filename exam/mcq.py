"""Multiple Choice Question (MCQ) Engine with Grounded RAG Document Support & Automatic Batching."""

import logging
import re
from typing import Any, Dict, List, Optional, Tuple

from llm.llm_client import generate_json
from llm.prompts import build_mcq_prompt

logger = logging.getLogger(__name__)


def _normalize_mcq_choice(choice_text: Any) -> str:
    """Normalizes option choices (e.g., 'A) Paris', 'Option A', 'a.', 'A') into standard 'A'."""
    if not choice_text or not isinstance(choice_text, str):
        return ""

    cleaned = choice_text.strip().upper()
    match = re.search(r"^(?:OPTION\s*)?([A-D])[\s\)\.\:]*", cleaned)
    if match:
        return match.group(1)

    return cleaned


def generate_mcq_paper(
    api_key: str,
    subject: str,
    chapter: str = "General",
    count: int = 5,
    context_document_text: Optional[str] = None,
    preferred_model: str = "openrouter/free",
) -> Tuple[bool, List[Dict[str, Any]], str]:
    """Generates structured MCQ paper payload via LLM with automatic batching for large counts."""
    all_valid_questions = []
    model_used_final = preferred_model

    # Batching logic: fetch at most 10 questions per API call to prevent LLM JSON truncation
    batch_size = 10
    remaining = count

    while remaining > 0:
        current_batch_count = min(remaining, batch_size)

        if context_document_text and context_document_text.strip():
            prompt_str = (
                f"You are a senior exam paper setter. Generate {current_batch_count} multiple-choice questions (MCQs) "
                f"based EXCLUSIVELY on the provided study context for subject '{subject}', chapter '{chapter}'.\n\n"
                f"Study Context:\n{context_document_text[:10000]}\n\n"
                "Output ONLY a raw JSON array of objects matching this schema:\n"
                "[\n"
                "  {\n"
                '    "question_text": "Question string?",\n'
                '    "options": ["A) Option 1", "B) Option 2", "C) Option 3", "D) Option 4"],\n'
                '    "correct_answer": "A) Option 1",\n'
                '    "explanation": "Detailed explanation based on context.",\n'
                '    "difficulty": "Medium"\n'
                "  }\n"
                "]"
            )
        else:
            prompt_str = build_mcq_prompt(subject=subject, chapter=chapter, count=current_batch_count)

        messages = [{"role": "user", "content": prompt_str}]

        success, result_json, model_used = generate_json(
            api_key=api_key,
            messages=messages,
            preferred_model=preferred_model,
            temperature=0.3,
        )
        model_used_final = model_used

        if success and isinstance(result_json, list):
            for item in result_json:
                if isinstance(item, dict) and "question_text" in item and "options" in item and "correct_answer" in item:
                    all_valid_questions.append({
                        "question_text": item["question_text"],
                        "options": item["options"],
                        "correct_answer": item["correct_answer"],
                        "explanation": item.get("explanation", "No explanation provided."),
                        "difficulty": item.get("difficulty", "Medium"),
                    })

        remaining -= current_batch_count

    if not all_valid_questions:
        logger.error("MCQ paper generation failed: %s", model_used_final)
        return False, [], model_used_final

    return True, all_valid_questions[:count], model_used_final


def score_mcq_submission(
    user_answers: Dict[int, Any],
    questions: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Scores student responses safely handling None values for unanswered questions."""
    total = len(questions)
    correct_count = 0
    breakdown = []

    for idx, q in enumerate(questions):
        raw_val = user_answers.get(idx)
        user_ans_raw = raw_val.strip() if isinstance(raw_val, str) else ""
        correct_ans_raw = str(q.get("correct_answer", "")).strip()

        user_code = _normalize_mcq_choice(user_ans_raw)
        correct_code = _normalize_mcq_choice(correct_ans_raw)

        is_correct = (user_code != "" and user_code == correct_code) or (
            user_ans_raw.lower() == correct_ans_raw.lower() and user_ans_raw != ""
        )

        if is_correct:
            correct_count += 1

        breakdown.append({
            "question_index": idx,
            "question_text": q["question_text"],
            "user_answer": user_ans_raw if user_ans_raw else "Unanswered",
            "correct_answer": correct_ans_raw,
            "is_correct": is_correct,
            "explanation": q.get("explanation", ""),
        })

    score_pct = round((correct_count / total * 100), 2) if total > 0 else 0.0

    return {
        "total_questions": total,
        "correct_count": correct_count,
        "wrong_count": total - correct_count,
        "score_percentage": score_pct,
        "breakdown": breakdown,
    }
