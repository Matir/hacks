import os
from dataclasses import dataclass, field
from datetime import UTC, datetime

from trashdig.config import get_config


@dataclass
class Finding:
    """Represents a discovered security vulnerability."""
    title: str
    description: str
    severity: str
    vulnerable_code: str
    file_path: str
    impact: str
    exploitation_path: str
    remediation: str
    cwe_id: str | None = None
    verification_status: str = "Unverified" # Unverified, Verified, False Positive
    poc: str | None = None
    timestamp: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    def to_markdown(self) -> str:
        """Converts the finding to a formatted Markdown string.

        Returns:
            Markdown representation of the finding.
        """
        md = f"# {self.title}\n\n"
        md += f"**Severity:** {self.severity}\n"
        md += f"**CWE:** {self.cwe_id or 'N/A'}\n"
        md += f"**Status:** {self.verification_status}\n\n"
        md += f"## Description\n{self.description}\n\n"
        md += f"## Vulnerable Code\n```\n{self.vulnerable_code}\n```\n\n"
        md += f"## Impact\n{self.impact}\n\n"
        md += f"## Exploitation Path\n{self.exploitation_path}\n\n"
        md += f"## Remediation\n{self.remediation}\n"
        if self.poc:
            md += f"\n## Proof of Concept\n```python\n{self.poc}\n```\n"
        return md

    def save(self, output_dir: str | None = None) -> None:
        """Saves the finding to a Markdown file.

        Args:
            output_dir: Directory to save to. Defaults to config settings.
        """
        if output_dir is None:
            config = get_config()
            output_dir = os.path.join(config.data_dir, "findings")

        if not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)

        # Create a safe filename from the title
        safe_title = "".join(c for c in self.title if c.isalnum() or c in (" ", "-", "_")).strip().replace(" ", "_")
        filename = f"{safe_title}_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}.md"
        file_path = os.path.join(output_dir, filename)

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(self.to_markdown())

