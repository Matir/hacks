import os
from collections import Counter

# Mapping of file extensions to programming languages
EXTENSION_MAP = {
    ".py": "python",
    ".js": "javascript",
    ".jsx": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".go": "go",
    ".cs": "csharp",
    ".java": "java",
    ".c": "c",
    ".cpp": "cpp",
    ".cc": "cpp",
    ".h": "c/cpp",
    ".rb": "ruby",
    ".php": "php",
    ".rs": "rust",
    ".sh": "shell",
    ".bash": "shell",
    ".ps1": "powershell",
    ".sql": "sql",
    ".html": "html",
    ".css": "css",
    ".json": "json",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".xml": "xml",
    ".md": "markdown",
}

def detect_language(path: str) -> str:
    """Detects the programming language for a single file or a set of files in a directory.

    Args:
        path: The path to a file or directory.

    Returns:
        A string describing the detected language(s).
    """
    if os.path.isfile(path):
        ext = os.path.splitext(path)[1].lower()
        return EXTENSION_MAP.get(ext, "unknown")

    if os.path.isdir(path):
        counts: Counter[str] = Counter()
        total_files = 0
        for root, _, files in os.walk(path):
            # Skip hidden directories and common noisy ones
            if any(part.startswith('.') for part in root.split(os.sep)):
                continue
            if 'node_modules' in root or 'venv' in root or '__pycache__' in root:
                continue

            for filename in files:
                ext = os.path.splitext(filename)[1].lower()
                lang = EXTENSION_MAP.get(ext)
                if lang:
                    counts[lang] += 1
                    total_files += 1

        if total_files == 0:
            return "No recognized source files found."

        # Format the results as a proportion
        results = []
        for lang, count in counts.most_common():
            proportion = (count / total_files) * 100
            results.append(f"{lang}: {proportion:.1f}% ({count} files)")

        return "\n".join(results)

    return f"Path {path} not found."
