import json
import logging
import re
from typing import Any

logger = logging.getLogger(__name__)


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

    # 3. Try to find anything between { and }
    try:
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start != -1 and end != -1:
            data = json.loads(cleaned[start:end+1])
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
