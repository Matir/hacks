"""Tool for querying the Vulnerability Database."""

from trashdig.services.vulndb import get_vulndb_service

from .base import artifact_tool


@artifact_tool(max_chars=10000)
def query_vulndb(query: str) -> str:
    """Queries the Vulnerability Database for information, patterns, and remediation.

    Args:
        query: The search query (CWE ID, title, or keyword).

    Returns:
        A formatted string containing matching vulnerability information.
    """
    try:
        service = get_vulndb_service()
        entries = service.query(query)

        if not entries:
            return f"No results found for query: {query}"

        results = []
        for entry in entries:
            header = f"## {entry.id}: {entry.title}\n"
            header += (
                f"**Category:** {entry.category} | **Severity:** {entry.severity}\n"
            )
            header += f"**Tags:** {', '.join(entry.tags)}\n\n"

            # Add active patterns if available
            if entry.active_patterns:
                header += "### Active Patterns (Semgrep)\n"
                for p in entry.active_patterns:
                    header += (
                        f"- **{p['name']}** ({', '.join(p.get('languages', []))})\n"
                    )
                    header += f"  ```yaml\n  {p['pattern']}\n  ```\n"
                header += "\n"

            content = entry.get_content()
            results.append(header + content)

        return "\n---\n".join(results)
    except Exception as e:  # noqa: BLE001
        return f"Error querying VulnDB: {str(e)}"
