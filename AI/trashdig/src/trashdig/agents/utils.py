import os
from typing import List, Dict
from pathspec import PathSpec
from pathspec.patterns import GitWildMatchPattern

def get_project_structure(root_path: str = ".") -> List[str]:
    """Walks the project directory and returns a list of files, respecting .gitignore.

    Args:
        root_path: The root directory to walk.

    Returns:
        A list of file paths relative to the root, sorted alphabetically.
    """
    files: List[str] = []
    
    # Load .gitignore patterns
    gitignore_path = os.path.join(root_path, ".gitignore")
    spec: Optional[PathSpec] = None
    if os.path.exists(gitignore_path):
        with open(gitignore_path, "r", encoding="utf-8") as f:
            spec = PathSpec.from_lines(GitWildMatchPattern, f.readlines())

    # Noisy directories to always skip
    noisy_dirs = {".git", "node_modules", "dist", "vendor", "__pycache__", ".venv", "findings", "tests"}

    for root, dirs, filenames in os.walk(root_path):
        # Filter directories in-place to avoid walking them
        dirs[:] = [d for d in dirs if d not in noisy_dirs]
        
        for filename in filenames:
            rel_path = os.path.relpath(os.path.join(root, filename), root_path)
            
            # Skip if it matches .gitignore
            if spec and spec.match_file(rel_path):
                continue
                
            files.append(rel_path)
            
    return sorted(files)

def read_file_content(file_path: str, max_chars: int = 2000) -> str:
    """Reads a portion of a file's content for analysis.

    Args:
        file_path: Path to the file.
        max_chars: Maximum number of characters to read. Defaults to 2000.

    Returns:
        The file content (potentially truncated), or an error message.
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read(max_chars)
            return content
    except (UnicodeDecodeError, PermissionError, FileNotFoundError):
        return "[Error: Could not read file content]"

def detect_frameworks(file_list: List[str], project_root: str = ".") -> Dict[str, List[str]]:
    """Analyzes dependency files to identify known frameworks and libraries.

    Args:
        file_list: List of project files.
        project_root: Project root directory. Defaults to ".".

    Returns:
        A dictionary mapping categories (e.g., 'web_frameworks', 'databases') to lists 
        of detected technology names.
    """
    stack: Dict[str, List[str]] = {
        "web_frameworks": [],
        "databases": [],
        "auth_libraries": [],
        "other": []
    }
    
    # Key files to check
    dep_files = ["package.json", "requirements.txt", "pyproject.toml", "go.mod", "pom.xml", "Gemfile"]
    
    # Framework signatures
    signatures = {
        "web_frameworks": ["fastapi", "flask", "django", "express", "spring-boot", "rails", "gin", "echo", "nextjs", "react"],
        "databases": ["sqlalchemy", "prisma", "mongoose", "typeorm", "gorm", "postgresql", "mysql", "mongodb", "redis", "sqlite"],
        "auth_libraries": ["passport", "auth0", "next-auth", "firebase-auth", "clerk", "jwt", "oauthlib"]
    }

    for dep_file in dep_files:
        if dep_file in file_list:
            content = read_file_content(os.path.join(project_root, dep_file), max_chars=10000).lower()
            
            for category, names in signatures.items():
                for name in names:
                    if name in content:
                        if name not in stack[category]:
                            stack[category].append(name)
                            
    return stack

