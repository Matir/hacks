import json
import os
from dataclasses import dataclass
from typing import Any

from trashdig.config import get_config


@dataclass
class VulnEntry:
    """Represents a single vulnerability entry."""

    id: str
    title: str
    category: str
    severity: str
    tags: list[str]
    active_patterns: list[dict[str, Any]]
    content_path: str
    base_dir: str

    def get_content(self) -> str:
        """Reads the Markdown content for this entry.

        Returns:
            The Markdown content as a string.
        """
        full_path = os.path.join(self.base_dir, self.content_path)
        if not os.path.exists(full_path):
            return f"Content file not found: {self.content_path}"
        with open(full_path, encoding="utf-8") as f:
            return f.read()


class VulnDBService:
    """Service for querying the Vulnerability Database."""

    def __init__(self, extra_dirs: list[str] | None = None):
        """Initializes the VulnDBService.

        Args:
            extra_dirs: Optional list of additional directories to load data from.
        """
        self.entries: dict[str, VulnEntry] = {}

        # 1. Load built-in data
        builtin_dir = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), "data", "vulndb"
        )
        self._load_from_dir(builtin_dir)

        # 2. Load extra dirs (overrides built-in)
        if extra_dirs:
            for d in extra_dirs:
                self._load_from_dir(os.path.expanduser(d))

    def _load_from_dir(self, data_dir: str) -> None:
        """Loads vulnerability data from a specific directory."""
        metadata_path = os.path.join(data_dir, "metadata.json")
        if not os.path.exists(metadata_path):
            return

        try:
            with open(metadata_path, encoding="utf-8") as f:
                data = json.load(f)
                for item in data:
                    entry = VulnEntry(
                        id=item["id"],
                        title=item["title"],
                        category=item["category"],
                        severity=item["severity"],
                        tags=item.get("tags", []),
                        active_patterns=item.get("active_patterns", []),
                        content_path=item["content_path"],
                        base_dir=data_dir,
                    )
                    self.entries[entry.id] = entry
        except Exception:  # noqa: BLE001, S110
            # Silently skip failed loads
            pass

    def query(self, query: str) -> list[VulnEntry]:
        """Searches for vulnerabilities matching the query.

        Args:
            query: The search string.

        Returns:
            A list of matching VulnEntry objects.
        """
        results = []
        q = query.lower()
        for entry in self.entries.values():
            if (
                q in entry.id.lower()
                or q in entry.title.lower()
                or any(q in t.lower() for t in entry.tags)
            ):
                results.append(entry)
        return results

    def get_entry(self, vuln_id: str) -> VulnEntry | None:
        """Retrieves a single entry by ID.

        Args:
            vuln_id: The ID of the vulnerability to retrieve.

        Returns:
            The matching VulnEntry, or None if not found.
        """
        return self.entries.get(vuln_id)


_instance: VulnDBService | None = None


def get_vulndb_service() -> VulnDBService:
    """Returns the global VulnDBService instance.

    Returns:
        The VulnDBService singleton.
    """
    global _instance  # noqa: PLW0603
    if _instance is None:
        config = get_config()
        vulndb_cfg = config.data.get("vulndb", {})
        extra_dirs = vulndb_cfg.get("extra_dirs", [])
        _instance = VulnDBService(extra_dirs=extra_dirs)
    return _instance
