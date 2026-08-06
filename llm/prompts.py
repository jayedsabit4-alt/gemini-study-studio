SYSTEM_CHAT_PROMPT = {
    "role": "system",
    "content": (
        "You are an expert job preparation AI tutor. "
        "Format math equations with LaTeX ($inline$ and $$display$$). "
        "Keep responses structured, concise, and professional."
    )
}

WRITTEN_EVAL_PROMPT = """
Evaluate the user's written exam response using this 10-point rubric:
1. Content & Depth: /4
2. Analytical Logic & Structure: /2
3. Subject Terminology & Precision: /2
4. Language & Grammar: /2

Return strictly a valid JSON object matching this structure:
{
  "content_score": 3,
  "logic_score": 2,
  "terminology_score": 1,
  "grammar_score": 2,
  "total_score": 8,
  "feedback": "Detailed feedback string..."
}
"""
