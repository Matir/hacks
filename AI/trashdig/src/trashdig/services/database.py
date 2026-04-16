"""SQLite-backed persistent knowledge store for a TrashDig project.

Provides session persistence across scans: project profiles, findings,
hypotheses (including failed ones), a symbol map, and a tool output cache.
All tables are keyed by ``project_path`` so a single database file can
track multiple target projects.
"""

import hashlib
import json
import os
import sqlite3
import uuid as _uuid
from collections.abc import Generator
from contextlib import contextmanager
from datetime import UTC, datetime
from typing import Any

from trashdig.config import get_config

_DDL = """
CREATE TABLE IF NOT EXISTS scan_sessions (
    session_id TEXT PRIMARY KEY,
    project_path TEXT NOT NULL,
    started_at TEXT NOT NULL,
    ended_at TEXT
);

CREATE TABLE IF NOT EXISTS project_profiles (
    project_path TEXT PRIMARY KEY,
    tech_stack TEXT,
    profile_json TEXT,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS findings (
    finding_id TEXT PRIMARY KEY,
    project_path TEXT NOT NULL,
    title TEXT NOT NULL,
    file_path TEXT NOT NULL,
    severity TEXT,
    description TEXT,
    vulnerable_code TEXT,
    impact TEXT,
    exploitation_path TEXT,
    remediation TEXT,
    cwe_id TEXT,
    verification_status TEXT DEFAULT 'Unverified',
    poc TEXT,
    timestamp TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS hypotheses (
    task_id TEXT PRIMARY KEY,
    project_path TEXT NOT NULL,
    type TEXT NOT NULL,
    target TEXT NOT NULL,
    description TEXT,
    confidence REAL,
    status TEXT DEFAULT 'PENDING',
    context_json TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS conversations (
    log_id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_path TEXT NOT NULL,
    agent_name TEXT NOT NULL,
    prompt TEXT,
    response TEXT,
    tool_calls_json TEXT,
    input_tokens INTEGER,
    output_tokens INTEGER,
    timestamp TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS tool_cache (
    cache_key TEXT PRIMARY KEY,
    func_name TEXT NOT NULL,
    args_json TEXT NOT NULL,
    result_text TEXT,
    timestamp TEXT NOT NULL
);
"""


class ProjectDatabase:
    """Handles persistence of all project-level state and session data.

    NOTE: Use `get_database(db_path)` instead of instantiating directly to
    benefit from connection pooling.
    """

    def __init__(self, db_path: str | None = None) -> None:
        """Initializes the database connection.

        Args:
            db_path: Path to the SQLite database file. If None, uses config.
        """
        if db_path is None:
            db_path = get_config().db_path
        self.db_path = db_path
        self._memory_conn: sqlite3.Connection | None = None
        if db_path != ":memory:":
            os.makedirs(os.path.dirname(db_path) if os.path.dirname(db_path) else ".", exist_ok=True)
        self._init_db()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _init_db(self) -> None:
        """Initializes the database schema."""
        with self._connect() as conn:
            conn.executescript(_DDL)

    @contextmanager
    def _connect(self) -> Generator[sqlite3.Connection, None, None]:
        """Provides a database connection with automatic commit/rollback."""
        if self.db_path == ":memory:":
            if self._memory_conn is None:
                self._memory_conn = sqlite3.connect(":memory:")
                self._memory_conn.row_factory = sqlite3.Row
                self._memory_conn.execute("PRAGMA journal_mode=WAL")
                self._memory_conn.execute("PRAGMA foreign_keys=ON")
            conn = self._memory_conn
            try:
                yield conn
                conn.commit()
            except Exception:
                conn.rollback()
                raise
            # Do NOT close for :memory: until object destruction
            return

        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def close(self) -> None:
        """Closes the memory connection if it exists."""
        if self._memory_conn:
            self._memory_conn.close()
            self._memory_conn = None

    def __del__(self) -> None:
        """Destructor to ensure connections are closed."""
        if hasattr(self, "_memory_conn") and self._memory_conn:
            self._memory_conn.close()

    # ------------------------------------------------------------------
    # Project profiles
    # ------------------------------------------------------------------

    def save_project_profile(
        self, project_path: str, tech_stack: str, profile: dict[str, Any]
    ) -> None:
        """Saves or updates the project profile."""
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO project_profiles
                (project_path, tech_stack, profile_json, updated_at)
                VALUES (?, ?, ?, ?)
                """,
                (project_path, tech_stack, json.dumps(profile), _now()),
            )

    def get_project_profile(self, project_path: str) -> dict[str, Any] | None:
        """Retrieves the project profile."""
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM project_profiles WHERE project_path = ?", (project_path,)
            ).fetchone()
            if row:
                data = dict(row)
                data["profile"] = json.loads(row["profile_json"])
                return data
        return None

    # ------------------------------------------------------------------
    # Findings
    # ------------------------------------------------------------------

    def save_finding(self, project_path: str, finding: Any) -> str:
        """Saves a security finding to the database."""
        finding_id = str(_uuid.uuid4())
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO findings
                (finding_id, project_path, title, file_path, severity, description,
                 vulnerable_code, impact, exploitation_path, remediation, cwe_id, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    finding_id,
                    project_path,
                    finding.title,
                    finding.file_path,
                    finding.severity,
                    finding.description,
                    finding.vulnerable_code,
                    finding.impact,
                    finding.exploitation_path,
                    finding.remediation,
                    finding.cwe_id,
                    finding.timestamp,
                ),
            )
        return finding_id

    def update_finding_status(
        self,
        project_path: str,
        title: str,
        file_path: str,
        status: str,
        poc: str,
    ) -> None:
        """Updates the verification status and PoC of a finding."""
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE findings
                SET verification_status = ?, poc = ?
                WHERE project_path = ? AND title = ? AND file_path = ?
                """,
                (status, poc, project_path, title, file_path),
            )

    def get_findings(self, project_path: str) -> list[dict[str, Any]]:
        """Returns all findings for a project."""
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM findings WHERE project_path = ?", (project_path,)
            ).fetchall()
            return [dict(r) for r in rows]

    # ------------------------------------------------------------------
    # Hypotheses
    # ------------------------------------------------------------------

    def save_hypothesis(self, project_path: str, hypothesis: Any) -> None:
        """Saves a security hypothesis."""
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO hypotheses
                (task_id, project_path, type, target, description, confidence, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    hypothesis.task_id,
                    project_path,
                    hypothesis.type.name,
                    hypothesis.target,
                    hypothesis.description,
                    hypothesis.confidence,
                    _now(),
                    _now(),
                ),
            )

    def update_hypothesis_status(self, task_id: str, status: str) -> None:
        """Updates the status of a hypothesis."""
        with self._connect() as conn:
            conn.execute(
                "UPDATE hypotheses SET status = ?, updated_at = ? WHERE task_id = ?",
                (status, _now(), task_id),
            )

    def get_pending_hypotheses(self, project_path: str) -> list[dict[str, Any]]:
        """Returns all pending hypotheses for a project, sorted by confidence."""
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT * FROM hypotheses
                WHERE project_path = ? AND status = 'PENDING'
                ORDER BY confidence DESC
                """,
                (project_path,),
            ).fetchall()
            return [dict(r) for r in rows]

    # ------------------------------------------------------------------
    # Logging & Stats
    # ------------------------------------------------------------------

    def log_conversation(  # noqa: PLR0913
        self,
        project_path: str,
        agent_name: str,
        prompt: str,
        response: str,
        tool_calls: list[dict[str, Any]],
        input_tokens: int,
        output_tokens: int,
    ) -> None:
        """Logs an LLM interaction."""
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO conversations
                (project_path, agent_name, prompt, response, tool_calls_json,
                 input_tokens, output_tokens, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    project_path,
                    agent_name,
                    prompt,
                    response,
                    json.dumps(tool_calls),
                    input_tokens,
                    output_tokens,
                    _now(),
                ),
            )

    # ------------------------------------------------------------------
    # Session Management
    # ------------------------------------------------------------------

    def get_or_create_scan_session(self, project_path: str) -> str:
        """Starts a new scan session or returns the current active one."""
        with self._connect() as conn:
            # Check for active session (started but not ended)
            row = conn.execute(
                "SELECT session_id FROM scan_sessions WHERE project_path = ? AND ended_at IS NULL",
                (project_path,),
            ).fetchone()
            if row:
                return row["session_id"]

            session_id = str(_uuid.uuid4())
            conn.execute(
                "INSERT INTO scan_sessions (session_id, project_path, started_at) VALUES (?, ?, ?)",
                (session_id, project_path, _now()),
            )
            return session_id

    def close_scan_session(self, session_id: str) -> None:
        """Marks a scan session as completed.

        Args:
            session_id: The ID of the scan session to close.
        """
        with self._connect() as conn:
            conn.execute(
                "UPDATE scan_sessions SET ended_at = ? WHERE session_id = ?",
                (_now(), session_id),
            )


# ----------------------------------------------------------------------
# Module-level singletons
# ----------------------------------------------------------------------

_db_instances: dict[str, ProjectDatabase] = {}


def get_database(db_path: str | None = None) -> ProjectDatabase:
    """Returns a pooled database instance for the given path."""
    if db_path is None:
        db_path = get_config().db_path
    abs_path = os.path.abspath(db_path) if db_path != ":memory:" else ":memory:"
    if abs_path not in _db_instances:
        _db_instances[abs_path] = ProjectDatabase(db_path=db_path)
    return _db_instances[abs_path]


def _now() -> str:
    return datetime.now(UTC).isoformat()



def _args_hash(args: dict[str, Any]) -> str:
    """Deterministic SHA-256 digest of a JSON-serialised argument dict."""
    payload = json.dumps(args, sort_keys=True, default=str)
    return hashlib.sha256(payload.encode()).hexdigest()
