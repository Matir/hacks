import json
import os
from typing import Any, Dict, List

from .base import artifact_tool


@artifact_tool(max_chars=5000)
def query_cwe_database(query: str) -> str:
    """Queries the built-in CWE knowledge base for descriptions and examples.

    Args:
        query: The search query (CWE ID, title, or description keyword).

    Returns:
        A formatted string containing matching CWE entries and examples.
    """
    try:
        # data path is relative to the package
        data_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "cwe_db.json")
        with open(data_path, "r", encoding="utf-8") as f:
            cwe_data: List[Dict[str, Any]] = json.load(f)
        results: List[str] = []
        q = query.lower()
        for item in cwe_data:
            if (q in item["cwe_id"].lower() or q in item["title"].lower() or q in item["description"].lower()):
                results.append(f"### {item['cwe_id']}: {item['title']}\n{item['description']}\n")
                if "examples" in item:
                    for ex in item["examples"]:
                        results.append(f"**Vulnerable Example ({ex['language']}):**\n```\n{ex['vulnerable_code']}\n```\n")
        return "\n".join(results) if results else f"No results found for query: {query}"
    except Exception as e:
        return f"Error querying CWE database: {str(e)}"
