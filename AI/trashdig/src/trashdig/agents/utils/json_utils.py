import json
import logging
import re
from typing import Any

logger = logging.getLogger(__name__)

# Phrases models commonly use when declining a request in-character rather
# than via a hard API-level block (finish_reason=SAFETY/PROHIBITED_CONTENT).
_REFUSAL_PATTERN = re.compile(
    r"^\s*(i'?m sorry|sorry,?|i cannot|i can'?t|i'?m unable to|i am unable to|"
    r"i'?m not able to|i won'?t|i will not)\b",
    re.IGNORECASE,
)

# google.genai.types.FinishReason / BlockedReason values that indicate the
# model or API refused/blocked the request for safety/policy reasons, as
# opposed to reasons like MAX_TOKENS, LANGUAGE, or MALFORMED_FUNCTION_CALL
# which also populate these fields but aren't refusals. Shared with
# `trashdig.agents.utils.callbacks._refusal_reason`, which checks the same
# values on the live LlmResponse as each model call completes — this is the
# single source of truth for both.
BLOCKED_REASONS = frozenset(
    {
        "SAFETY",
        "PROHIBITED_CONTENT",
        "BLOCKLIST",
        "SPII",
        "RECITATION",
        "IMAGE_SAFETY",
        "IMAGE_PROHIBITED_CONTENT",
        "IMAGE_RECITATION",
        "JAILBREAK",
        "MODEL_ARMOR",
    }
)


def classify_llm_failure(text: str, diagnostics: dict[str, Any] | None = None) -> str:
    """Classifies why an LLM response could not be parsed as JSON.

    Args:
        text: The raw LLM response text.
        diagnostics: Optional dict populated by `run_agent` with keys
            `finish_reason`, `error_code`, `error_message` from the final
            response event.

    Returns:
        A short machine-readable label describing the failure, for logging.
    """
    diagnostics = diagnostics or {}

    # ADK's LlmResponse.create() only ever populates `error_code` in one
    # situation: the API returned zero candidates at all, in which case it
    # sets `error_code = generate_content_response.prompt_feedback.block_reason`
    # — i.e. the *prompt itself* (not a generated candidate) was blocked
    # before generation started. Any other error_code is a genuine API/
    # transport error (auth, quota, etc.), not a content block.
    error_code = diagnostics.get("error_code")
    error_code_name = getattr(error_code, "name", error_code)
    if error_code_name and str(error_code_name) in BLOCKED_REASONS:
        return f"prompt_blocked:{error_code_name}"
    if error_code:
        return f"api_error:{error_code}"

    # A candidate was generated but got cut short for a safety/policy reason
    # (finish_reason set on the candidate itself, mid- or post-generation).
    finish_reason = diagnostics.get("finish_reason")
    finish_reason_name = getattr(finish_reason, "name", finish_reason)
    if finish_reason_name and str(finish_reason_name) in BLOCKED_REASONS:
        return f"safety_block:{finish_reason_name}"

    if not text.strip():
        return "empty_response"

    if _REFUSAL_PATTERN.match(text.strip()):
        return "model_refusal"

    return "malformed_json"


def parse_json_response(text: str) -> dict[str, Any]:
    """Cleans and parses a JSON response from an LLM.

    Handles common issues like markdown blocks and leading/trailing whitespace.

    Args:
        text: The raw LLM response text.

    Returns:
        A dictionary parsed from the JSON, or an empty dict on failure.
    """
    if not text:
        return {}

    # 1. Try direct parsing
    try:
        return json.loads(text.strip())
    except json.JSONDecodeError:
        pass

    # 2. Try stripping markdown block markers
    cleaned = text.strip()
    if cleaned.startswith("```"):
        # Strip ```json ... ``` or just ``` ... ```
        cleaned = re.sub(r"^```(?:json)?\n?", "", cleaned)
        cleaned = re.sub(r"\n?```$", "", cleaned)
        try:
            return json.loads(cleaned.strip())
        except json.JSONDecodeError:
            pass

    # 3. Try decoding the first complete JSON value starting at the first
    # '{', ignoring any trailing garbage the LLM may have appended after it
    # (e.g. stray closing brackets). rfind("}") is unreliable here since the
    # *last* '}' in the text isn't necessarily the one that closes the first
    # object.
    try:
        start = cleaned.find("{")
        if start != -1:
            data, _ = json.JSONDecoder().raw_decode(cleaned, start)
            if isinstance(data, list):
                return {"items": data}
            return data
    except (json.JSONDecodeError, ValueError):
        logger.debug("Failed to parse JSON using regex markers: %s", text)

    return {}


def extract_json_list(text: str, key: str) -> list[Any]:
    """Parses JSON from text and returns a list associated with a key.

    Args:
        text: The raw LLM response.
        key: The key in the JSON object (e.g., 'findings').

    Returns:
        The list of items, or an empty list if not found/invalid.
    """
    data = parse_json_response(text)
    items = data.get(key, [])
    if isinstance(items, list):
        return items
    return [items] if items else []
