import json
from llm.llm_client import execute_completion
from llm.prompts import WRITTEN_EVAL_PROMPT
from llm.formatter import clean_json

def evaluate_written_answer(api_key: str, question: str, student_answer: str) -> dict:
    messages = [
        {"role": "system", "content": WRITTEN_EVAL_PROMPT},
        {"role": "user", "content": f"Question: {question}\n\nStudent Answer: {student_answer}"}
    ]
    raw_response, _ = execute_completion(api_key, messages)
    try:
        return json.loads(clean_json(raw_response))
    except Exception:
        return {"total_score": 0, "feedback": raw_response}
