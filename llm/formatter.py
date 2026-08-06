import re

def fix_latex_formatting(text: str) -> str:
    if not text:
        return ""
    text = re.sub(r"(?<!\n)(###?\s+)", r"\n\n\1", text)
    text = re.sub(r"\\\[\s*(.*?)\s*\\\]", r"\n$$\1$$\n", text, flags=re.DOTALL)
    text = re.sub(r"\\\(\s*(.*?)\s*\\\)", r"$\1$", text, flags=re.DOTALL)
    text = re.sub(r"\$\$\s*(\\begin\{(aligned|equation|gather|cases)\})", r"\n$$\n\1", text)
    text = re.sub(r"(\\end\{(aligned|equation|gather|cases)\})\s*\$\$", r"\1\n$$\n", text)
    if "\\end{cases}" in text and "\\begin{cases}" not in text:
        text = text.replace("\\end{cases}", "")
    return text

def clean_json(content: str) -> str:
    cleaned = re.sub(r"^```(?:json)?", "", content.strip(), flags=re.MULTILINE)
    cleaned = re.sub(r"```$", "", cleaned.strip(), flags=re.MULTILINE)
    match = re.search(r"([\[\{].*[\]\}])", cleaned, re.DOTALL)
    return match.group(1) if match else cleaned.strip()
