import json
import re
from typing import Any, Tuple, Union


def fix_latex_formatting(text: str) -> str:
    """Cleans raw LLM outputs, fixes squished markdown headers, KaTeX equations, and tables."""
    if not text:
        return ""

    # Fix squished markdown headers and section dividers
    text = re.sub(r"(?<!\n)(###?\s+)", r"\n\n\1", text)
    text = re.sub(r"(\\end\{[a-zA-Z]+\})\s*(###?|---)", r"\1\n\n\2", text)
    text = re.sub(
        r"(?<![|\w\n])\n?^\s*---\s*$(?![|\w])", r"\n\n---\n\n", text, flags=re.MULTILINE
    )

    # Standardize LaTeX delimiters: \[...\] -> $$...$$, \(...\) -> $...$
    text = re.sub(r"\\\[\s*(.*?)\s*\\\]", r"\n$$\1$$\n", text, flags=re.DOTALL)
    text = re.sub(r"(?<!\w)\[\s*(\\.*?)\s*\]", r"\n$$\1$$\n", text, flags=re.DOTALL)
    text = re.sub(r"\\\(\s*(.*?)\s*\\\)", r"$\1$", text, flags=re.DOTALL)
    text = re.sub(r"(?<!\w)\(\s*(\\.*?)\s*\)", r"$\1$", text, flags=re.DOTALL)

    # Ensure display environments are wrapped cleanly inside $$ block tags
    text = re.sub(
        r"\$\$\s*(\\begin\{(aligned|equation|gather|alignat|matrix|bmatrix|cases|array)\})",
        r"\n$$\n\1",
        text,
    )
    text = re.sub(
        r"(\\end\{(aligned|equation|gather|alignat|matrix|bmatrix|cases|array)\})\s*\$\$",
        r"\1\n$$\n",
        text,
    )

    # Clean orphaned KaTeX tags
    if "\\end{cases}" in text and "\\begin{cases}" not in text:
        text = text.replace("\\end{cases}", "")

    return text


def clean_json_response(content: str) -> str:
    """Extracts raw JSON text by stripping markdown backticks or surrounding text wrappers."""
    if not content:
        return ""
    cleaned = re.sub(r"^```(?:json)?", "", content.strip(), flags=re.MULTILINE)
    cleaned = re.sub(r"```$", "", cleaned.strip(), flags=re.MULTILINE)
    match = re.search(r"([\[\{].*[\]\}])", cleaned, re.DOTALL)
    return match.group(1) if match else cleaned.strip()


def validate_and_parse_json(
    content: str,
) -> Tuple[bool, Union[dict, list, None], str]:
    """Extracts and parses JSON string safely into a Python dictionary or list."""
    cleaned_text = clean_json_response(content)
    if not cleaned_text:
        return False, None, "Empty payload string."

    try:
        data = json.loads(cleaned_text)
        return True, data, ""
    except json.JSONDecodeError as err:
        return False, None, f"JSON Parsing Error: {str(err)}"
