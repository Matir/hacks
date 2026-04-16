import json
import re
from typing import Any, Dict, List, Optional

def parse_json_response(text: str) -> Dict[str, Any]:
    """Cleans and parses a JSON response from an LLM.

    Handles common issues like markdown blocks and leading/trailing whitespace.

    Args:
        text: The raw response text from the LLM.

    Returns:
        A dictionary containing the parsed JSON data.
        Returns an empty dict if parsing fails.
    """
    if not text:
        return {}
        
    cleaned = text.strip()
    
    # Remove markdown JSON code blocks if present
    # Matches ```json { ... } ``` or just ``` { ... } ```
    pattern = r"```(?:json)?\s*(.*?)\s*```"
    match = re.search(pattern, cleaned, re.DOTALL)
    if match:
        cleaned = match.group(1).strip()
    
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        # Try to find anything that looks like a JSON object or array
        # This is a bit more aggressive fallback
        try:
            # Look for the first '{' and last '}'
            start = cleaned.find('{')
            end = cleaned.rfind('}')
            if start != -1 and end != -1 and end > start:
                return json.loads(cleaned[start:end+1])
            
            # Look for the first '[' and last ']'
            start = cleaned.find('[')
            end = cleaned.rfind(']')
            if start != -1 and end != -1 and end > start:
                # If it's a list, we wrap it in a dict with a 'data' key?
                # Actually, many agents expect a dict, so let's see.
                # If the agent expects a list, this might still fail if it expects a dict.
                data = json.loads(cleaned[start:end+1])
                if isinstance(data, list):
                    return {"items": data}
                return data
        except Exception:
            pass
            
    return {}

def extract_json_list(text: str, key: str) -> List[Any]:
    """Parses JSON from text and returns a list associated with a key.

    Args:
        text: Raw LLM response.
        key: The key in the JSON object that should contain a list.

    Returns:
        A list of items, or an empty list if not found or not a list.
    """
    data = parse_json_response(text)
    items = data.get(key, [])
    if isinstance(items, list):
        return items
    elif isinstance(items, dict):
        # Some LLMs might return a single object instead of a list of one
        return [items]
    return []
