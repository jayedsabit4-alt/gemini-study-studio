import time
from typing import Any, Dict, Generator, List, Optional, Tuple, Union
from openai import APIConnectionError, APIError, APITimeoutError, OpenAI, RateLimitError

from llm.formatter import fix_latex_formatting, validate_and_parse_json

# Ordered fallback chain for OpenRouter free models
FALLBACK_MODELS: List[str] = [
    "openrouter/free",
    "google/gemma-2-9b-it:free",
    "meta-llama/llama-3.1-8b-instruct:free",
    "qwen/qwen-2.5-72b-instruct:free",
    "deepseek/deepseek-r1:free",
]


def _get_client(api_key: str, timeout: float = 45.0) -> OpenAI:
    """Instantiates OpenAI SDK configured for OpenRouter endpoints."""
    return OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=api_key,
        timeout=timeout,
    )


def generate_response(
    api_key: str,
    messages: List[Dict[str, str]],
    preferred_model: str = "openrouter/free",
    temperature: float = 0.7,
    max_retries: int = 2,
    timeout: float = 45.0,
) -> Tuple[bool, Optional[str], str]:
    """Executes chat completion with automatic model fallback and exponential retry backoff.
    
    Returns:
        (success_boolean, formatted_response_content, model_used_or_error_message)
    """
    if not api_key:
        return False, None, "API key missing."

    client = _get_client(api_key, timeout=timeout)
    candidate_models = [preferred_model] + [
        m for m in FALLBACK_MODELS if m != preferred_model
    ]
    last_error = ""

    for model in candidate_models:
        for attempt in range(max_retries):
            try:
                response = client.chat.completions.create(
                    model=model,
                    messages=messages,
                    temperature=temperature,
                )
                content = response.choices[0].message.content
                if content and content.strip():
                    return True, fix_latex_formatting(content), model
            except (RateLimitError, APITimeoutError, APIConnectionError) as err:
                last_error = f"{model} (Attempt {attempt+1}): {type(err).__name__} - {str(err)}"
                time.sleep(1.5 * (attempt + 1))  # Exponential backoff
            except APIError as err:
                last_error = f"{model}: APIError {err.status_code} - {err.message}"
                break  # Try next model in fallback list on fatal API error
            except Exception as err:
                last_error = f"{model}: Unexpected - {str(err)}"
                break

    return False, None, f"All models failed. Last error: {last_error}"


def generate_json(
    api_key: str,
    messages: List[Dict[str, str]],
    preferred_model: str = "openrouter/free",
    temperature: float = 0.2,
    timeout: float = 45.0,
) -> Tuple[bool, Union[dict, list, None], str]:
    """Requests structured output from LLM, validates JSON schema, and retries once on parse failure.
    
    Returns:
        (success_boolean, parsed_json_dict_or_list, model_used_or_error_message)
    """
    success, raw_content, model_or_err = generate_response(
        api_key=api_key,
        messages=messages,
        preferred_model=preferred_model,
        temperature=temperature,
        timeout=timeout,
    )

    if not success or not raw_content:
        return False, None, model_or_err

    # Attempt 1: Standard JSON parsing
    parsed_ok, json_data, parse_err = validate_and_parse_json(raw_content)
    if parsed_ok:
        return True, json_data, model_or_err

    # Attempt 2: Auto-repair prompt fallback on JSON decode failure
    repair_messages = messages + [
        {"role": "assistant", "content": raw_content},
        {
            "role": "user",
            "content": (
                f"Your previous response failed JSON validation with error: {parse_err}. "
                "Output ONLY a valid, raw JSON object/array without markdown explanations or code blocks."
            ),
        },
    ]

    fix_success, fix_content, fix_model = generate_response(
        api_key=api_key,
        messages=repair_messages,
        preferred_model=preferred_model,
        temperature=0.0,
        timeout=timeout,
    )

    if fix_success and fix_content:
        re_parsed_ok, re_json_data, re_parse_err = validate_and_parse_json(
            fix_content
        )
        if re_parsed_ok:
            return True, re_json_data, fix_model
        return False, None, f"JSON validation failed after repair attempt: {re_parse_err}"

    return False, None, f"JSON extraction failed: {parse_err}"


def stream_response(
    api_key: str,
    messages: List[Dict[str, str]],
    preferred_model: str = "openrouter/free",
    temperature: float = 0.7,
    timeout: float = 45.0,
) -> Generator[Tuple[bool, str, str], None, None]:
    """Streams response chunks progressively for real-time UI typing animation.
    
    Yields:
        (success_boolean, text_chunk_or_error, model_name)
    """
    if not api_key:
        yield False, "API key missing.", ""
        return

    client = _get_client(api_key, timeout=timeout)
    candidate_models = [preferred_model] + [
        m for m in FALLBACK_MODELS if m != preferred_model
    ]
    stream_started = False

    for model in candidate_models:
        try:
            response_stream = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                stream=True,
            )

            for chunk in response_stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    delta_text = chunk.choices[0].delta.content
                    stream_started = True
                    yield True, delta_text, model

            if stream_started:
                return  # Stream completed successfully

        except Exception as err:
            if stream_started:
                # Interrupted mid-stream
                yield False, f"\n[Stream interrupted: {str(err)}]", model
                return
            continue  # Try next candidate model if connection failed before yielding

    yield False, "All models failed to stream response.", ""


def health_check(api_key: str) -> Tuple[bool, str]:
    """Pings OpenRouter endpoints with a minimal prompt to verify credentials and API reachability."""
    test_messages = [{"role": "user", "content": "Respond with 'OK'."}]
    success, response, details = generate_response(
        api_key=api_key,
        messages=test_messages,
        preferred_model="openrouter/free",
        timeout=10.0,
    )
    if success and response:
        return True, f"LLM client online (Model: {details})"
    return False, f"LLM client offline: {details}"
