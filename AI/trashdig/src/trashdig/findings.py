import os
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

@dataclass
class Finding:
    """Represents a vulnerability finding discovered by the Hunter agent.

    Attributes:
        title: A short, descriptive title for the finding.
        description: A detailed explanation of the vulnerability.
        severity: The risk level (Critical, High, Medium, Low, Info).
        vulnerable_code: A snippet of the problematic code.
        file_path: Path to the file containing the vulnerability.
        impact: Description of the potential consequences if exploited.
        exploitation_path: Step-by-step description of how to exploit.
        remediation: Instructions on how to fix the vulnerability.
        cwe_id: Optional CWE identifier.
        verification_status: Current status (Unverified, Verified, False Positive).
        poc: Optional Proof of Concept code.
        timestamp: ISO formatted string of when the finding was created.
    """
    title: str
    description: str
    severity: str  # e.g., Critical, High, Medium, Low, Info
    vulnerable_code: str
    file_path: str
    impact: str
    exploitation_path: str
    remediation: str
    cwe_id: str | None = None
    verification_status: str = "Unverified" # Unverified, Verified, False Positive
    poc: str | None = None
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_markdown(self) -> str:
        """Converts the finding to a formatted Markdown string.

        Returns:
            A string containing the Markdown representation of the finding.
        """
        md = f"# {self.title}\n\n"
        md += f"**Severity:** {self.severity}\n"
        md += f"**Status:** {self.verification_status}\n"
        md += f"**File Path:** `{self.file_path}`\n"
        if self.cwe_id:
            md += f"**CWE:** {self.cwe_id}\n"
        md += f"**Timestamp:** {self.timestamp}\n\n"
        
        md += "## Description\n"
        md += f"{self.description}\n\n"
        
        if self.poc:
            md += "## Proof of Concept\n"
            md += f"```python\n{self.poc}\n```\n\n"

        md += "## Vulnerable Code\n"
        # Determine language from file path for syntax highlighting
        lang = os.path.splitext(self.file_path)[1][1:] or "text"
        md += f"```{lang}\n{self.vulnerable_code}\n```\n\n"
        
        md += "## Impact\n"
        md += f"{self.impact}\n\n"
        
        md += "## Exploitation Path\n"
        md += f"{self.exploitation_path}\n\n"
        
        md += "## Remediation\n"
        md += f"{self.remediation}\n"
        
        return md

    def save(self, output_dir: Optional[str] = None) -> str:
        """Saves the finding as a Markdown file in the specified directory.

        Args:
            output_dir: The directory where the finding should be saved.
                       Defaults to Config.data_dir/findings.

        Returns:
            The absolute path to the saved file.
        """
        from trashdig.config import get_config
        if output_dir is None:
            output_dir = get_config().resolve_data_path("findings")
            
        if not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)
            
        # Create a safe filename from the title
        safe_title = "".join(c for c in self.title if c.isalnum() or c in (" ", "-", "_")).strip().replace(" ", "_")
        filename = f"{safe_title}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        file_path = os.path.join(output_dir, filename)
        
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(self.to_markdown())
            
        return file_path

