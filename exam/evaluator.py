"""Written Exam Rubric Evaluator Module."""

import logging
from typing import Any, Dict, Tuple
from llm.llm_client import generate_json
from llm.prompts import build_written_evaluation_prompt

logger = logging.getLogger(__name__)


def evaluate_written_submission(
    api_key: str,
    question: str,
    key_points: str,
    student_answer: str,
    preferred_model: str = "openrouter/free",
) -> Tuple[bool, Dict[str, Any], str]:
    """Evaluates student written exam answer against key points using a clamped 10-point rubric."""
    prompt_content = build_written_evaluation_prompt(
        question=question,
        key_points=key_points,
        student_answer=student_answer,
    )
    messages = [{"role": "user", "content": prompt_content}]

    success, result_json, model_used = generate_json(
        api_key=api_key,
        messages=messages,
        preferred_model=preferred_model,
        temperature=0.2,
    )

    if not success or not isinstance(result_json, dict):
        fallback_evaluation = {
            "content_score": 0,
            "logic_score": 0,
            "terminology_score": 0,
            "grammar_score": 0,
            "total_score": 0,
            "key_missing_points": ["Evaluation failed to parse."],
            "detailed_feedback": f"Evaluation error: {model_used}",
        }
        return False, fallback_evaluation, model_used

    # Enforce strict score bounds via mathematical clamping
    content_score = max(0, min(4, int(result_json.get("content_score", 0))))
    logic_score = max(0, min(2, int(result_json.get("logic_score", 0))))
    terminology_score = max(0, min(2, int(result_json.get("terminology_score", 0))))
    grammar_score = max(0, min(2, int(result_json.get("grammar_score", 0))))

    clamped_total = content_score + logic_score + terminology_score + grammar_score

    sanitized_eval = {
        "content_score": content_score,
        "logic_score": logic_score,
        "terminology_score": terminology_score,
        "grammar_score": grammar_score,
        "total_score": clamped_total,
        "key_missing_points": result_json.get("key_missing_points", []),
        "detailed_feedback": result_json.get("detailed_feedback", "No feedback provided."),
    }

    return True, sanitized_eval, model_used
