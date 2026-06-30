import hashlib
import json
from pathlib import Path
from typing import Any, Dict


class StateManager:
    def __init__(self, output_dir: Path):
        self.output_dir = Path(output_dir)
        self.state_file = self.output_dir / "state.json"
        self.state: Dict[str, Any] = {}
        self.load()

    def load(self):
        self.output_dir.mkdir(parents=True, exist_ok=True)
        if self.state_file.exists():
            try:
                with open(self.state_file, "r") as f:
                    self.state = json.load(f)
            except json.JSONDecodeError:
                # If corrupt, start fresh
                self.state = {}
        else:
            self.state = {}

    def save(self):
        with open(self.state_file, "w") as f:
            json.dump(self.state, f, indent=2)

    def get_file_hash(self, file_path: Path) -> str:
        """Calculate MD5 hash of a file."""
        hasher = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hasher.update(chunk)
        return hasher.hexdigest()

    def get_entry(self, relative_path: str) -> Dict[str, Any]:
        return self.state.get(relative_path, {
            "hash": "",
            "status": "new", # new, preprocessed, transcribed, completed, failed
            "preprocessed_path": "",
            "raw_transcript_path": "",
            "final_transcript_path": "",
            "error": "",
            "audio_duration": 0.0,
            "token_usage": {
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0
            }
        })

    def update_entry(self, relative_path: str, **kwargs):
        entry = self.get_entry(relative_path)
        for k, v in kwargs.items():
            entry[k] = str(v) if isinstance(v, Path) else v
        self.state[relative_path] = entry
        self.save()

    def is_completed(self, relative_path: str, current_hash: str) -> bool:
        entry = self.state.get(relative_path)
        if not entry:
            return False
        return entry.get("status") == "completed" and entry.get("hash") == current_hash
