"""Written Exam Question Generator and Session Manager with Automatic Batching."""

import logging
from typing import Any, Dict, List, Optional, Tuple

from exam.evaluator import evaluate_written_submission
from llm.llm_client import generate_json

logger = logging.getLogger(__name__)


def generate_written_question_paper(
    api_key: str,
    subject: str,
    chapter: str = "General",
    count: int = 1,
    context_document_text: Optional[str] = None,
    preferred_model: str = "openrouter/free",
) -> Tuple[bool, List[Dict[str, Any]], str]:
    """Generates written essay/short-answer question papers with automatic batching for large counts."""
    all_questions = []
    model_used_final = preferred_model

    batch_size = 5
    remaining = count

    while remaining > 0:
        current_batch_count = min(remaining, batch_size)

        if context_document_text and context_document_text.strip():
            prompt_str = (
                f"You are a senior examiner. Generate {current_batch_count} written/essay exam questions "
                f"based EXCLUSIVELY on the provided study context for subject '{subject}', chapter '{chapter}'.\n\n"
                f"Study Context:\n{context_document_text[:10000]}\n\n"
                "Output ONLY a raw JSON array of objects matching this schema:\n"
                "[\n"
                "  {\n"
                '    "question_text": "Detailed exam question?",\n'
                '    "key_points": "Bullet list of expected key concepts and facts from the context."\n'
                "  }\n"
                "]"
            )
        else:
            prompt_str = (
                f"You are a senior examiner. Generate {current_batch_count} written/essay exam questions "
                f"for subject '{subject}', chapter '{chapter}'.\n"
                "Output ONLY a raw JSON array of objects matching this schema:\n"
                "[\n"
                "  {\n"
                '    "question_text": "Detailed exam question?",\n'
                '    "key_points": "Bullet list of expected key concepts and facts for evaluation."\n'
                "  }\n"
                "]"
            )

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
                if isinstance(item, dict) and "question_text" in item and "key_points" in item:
                    all_questions.append({
                        "question_text": item["question_text"],
                        "key_points": item["key_points"],
                    })

        remaining -= current_batch_count

    if not all_questions:
        return False, [], model_used_final

    return True, all_questions[:count], model_used_final


def grade_written_exam(
    api_key: str,
    question: str,
    key_points: str,
    student_answer: str,
    preferred_model: str = "openrouter/free",
) -> Dict[str, Any]:
    """Grades written student response and returns rubric feedback."""
    if not student_answer or not student_answer.strip():
        return {
            "success": False,
            "total_score": 0,
            "detailed_feedback": "Answer was left blank.",
            "rubric": {
                "content_score": 0,
                "logic_score": 0,
                "terminology_score": 0,
                "grammar_score": 0,
            },
        }

    success, eval_data, model_used = evaluate_written_submission(
        api_key=api_key,
        question=question,
        key_points=key_points,
        student_answer=student_answer,
        preferred_model=preferred_model,
    )

    return {
        "success": success,
        "total_score": eval_data.get("total_score", 0),
        "detailed_feedback": eval_data.get("detailed_feedback", ""),
        "key_missing_points": eval_data.get("key_missing_points", []),
        "rubric": {
            "content_score": eval_data.get("content_score", 0),
            "logic_score": eval_data.get("logic_score", 0),
            "terminology_score": eval_data.get("terminology_score", 0),
            "grammar_score": eval_data.get("grammar_score", 0),
        },
        "model_used": model_used,
    }
