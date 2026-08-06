from openai import OpenAI
from llm.formatter import fix_latex_formatting

FALLBACK_MODELS = [
    "openrouter/free",
    "google/gemma-2-9b-it:free",
    "meta-llama/llama-3.1-8b-instruct:free",
    "qwen/qwen-2.5-72b-instruct:free",
    "mistralai/mistral-7b-instruct:free",
]

def execute_completion(api_key: str, messages: list, preferred_model: str = "openrouter/free"):
    client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=api_key, timeout=45.0)
    candidates = [preferred_model] + [m for m in FALLBACK_MODELS if m != preferred_model]
    last_err = None

    for model in candidates:
        try:
            res = client.chat.completions.create(model=model, messages=messages)
            content = res.choices[0].message.content
            if content and content.strip():
                return fix_latex_formatting(content), model
        except Exception as ex:
            last_err = str(ex)
            continue

    raise Exception(f"All models overloaded. Last error: {last_err}")
