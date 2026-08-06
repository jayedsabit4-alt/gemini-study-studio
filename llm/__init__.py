"""LLM Integration, Prompt Engineering, and Response Formatting Package API."""

from .formatter import clean_json_response, fix_latex_formatting, format_chat_messages, validate_and_parse_json
from .llm_client import generate_json, generate_response, health_check, stream_response
from .prompts import (
    build_mcq_generation_prompt,
    build_mcq_prompt,
    build_rag_prompt,
    build_rag_qa_prompt,
    build_revision_note_prompt,
    build_summary_prompt,
    build_written_eval_prompt,
    build_written_evaluation_prompt,
    build_written_generation_prompt,
    get_prompt,
)

__all__ = [
    "generate_response",
    "generate_json",
    "stream_response",
    "health_check",
    "format_chat_messages",
    "fix_latex_formatting",
    "clean_json_response",
    "validate_and_parse_json",
    "get_prompt",
    "build_mcq_prompt",
    "build_mcq_generation_prompt",
    "build_written_eval_prompt",
    "build_written_evaluation_prompt",
    "build_written_generation_prompt",
    "build_rag_prompt",
    "build_rag_qa_prompt",
    "build_revision_note_prompt",
    "build_summary_prompt",
]
