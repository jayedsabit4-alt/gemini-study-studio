"""AI Adaptive Revision Note Generator from Mistake Logs."""

from typing import Tuple
from config import DEFAULT_MODEL
from llm.llm_client import generate_response
from llm.prompts import build_revision_note_prompt


def generate_adaptive_revision_notes(
    api_key: str,
    mistakes_data: str,
    preferred_model: str = DEFAULT_MODEL,
) -> Tuple[bool, str, str]:
    """Generates structured markdown revision notes using recent mistake history."""
    prompt_content = build_revision_note_prompt(mistakes_data=mistakes_data)
    messages = [{"role": "user", "content": prompt_content}]

    return generate_response(
        api_key=api_key,
        messages=messages,
        preferred_model=preferred_model,
        temperature=0.4,
    )
