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
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any, Dict, Generator, List, Optional

from trashdig.config import get_config


_DDL = """
CREATE TABLE IF NOT EXISTS project_profiles (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    project_path TEXT    NOT NULL UNIQUE,
    tech_stack   TEXT,
    profile_json TEXT,
    created_at   TEXT    NOT NULL,
    updated_at   TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS findings (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    project_path        TEXT    NOT NULL,
    title               TEXT    NOT NULL,
    description         TEXT,
    severity            TEXT,
    vulnerable_code     TEXT,
    file_path           TEXT,
    impact              TEXT,
    exploitation_path   TEXT,
    remediation         TEXT,
    cwe_id              TEXT,
    verification_status TEXT    DEFAULT 'Unverified',
    poc                 TEXT,
    timestamp           TEXT,
    UNIQUE(project_path, title, file_path)
);

CREATE TABLE IF NOT EXISTS hypotheses (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    project_path TEXT    NOT NULL,
    task_id      TEXT    NOT NULL UNIQUE,
    target       TEXT    NOT NULL,
    description  TEXT,
    confidence   REAL,
    status       TEXT    DEFAULT 'pending',
    result_json  TEXT,
    created_at   TEXT    NOT NULL,
    updated_at   TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS symbol_map (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    project_path TEXT    NOT NULL,
    symbol_name  TEXT    NOT NULL,
    file_path    TEXT    NOT NULL,
    line_number  INTEGER,
    symbol_type  TEXT,
    UNIQUE(project_path, symbol_name, file_path, line_number)
);

CREATE TABLE IF NOT EXISTS tool_cache (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    project_path TEXT    NOT NULL,
    tool_name    TEXT    NOT NULL,
    args_hash    TEXT    NOT NULL,
    output       TEXT,
    created_at   TEXT    NOT NULL,
    UNIQUE(project_path, tool_name, args_hash)
);

CREATE TABLE IF NOT EXISTS conversations (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    project_path TEXT    NOT NULL,
    agent_name   TEXT    NOT NULL,
    prompt       TEXT    NOT NULL,
    response     TEXT,
    tool_calls   TEXT,   -- JSON array of {name: str, args: dict}
    input_tokens INTEGER,
    output_tokens INTEGER,
    timestamp    TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS scan_sessions (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    project_path TEXT    NOT NULL,
    session_id   TEXT    NOT NULL UNIQUE,
    started_at   TEXT    NOT NULL,
    ended_at     TEXT
);
"""


_db_instances: Dict[str, "ProjectDatabase"] = {}


def get_database(db_path: Optional[str] = None) -> "ProjectDatabase":
    """Singleton-like factory to return a ProjectDatabase for the given path.

    This ensures we don't frequently re-initialise the database connection
    and settings for the same file, improving efficiency and reducing the
    risk of SQLite locking issues in concurrent environments.
    """
    if db_path is None:
        db_path = get_config().db_path
    
    if not isinstance(db_path, str):
        # Handle cases where a Mock might have been passed in tests
        db_path = get_config().db_path
        
    abs_path = os.path.abspath(db_path)
    if abs_path not in _db_instances:
        _db_instances[abs_path] = ProjectDatabase(db_path=db_path)
    return _db_instances[abs_path]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _args_hash(args: Dict[str, Any]) -> str:
    """Deterministic SHA-256 digest of a JSON-serialised argument dict."""
    payload = json.dumps(args, sort_keys=True, default=str)
    return hashlib.sha256(payload.encode()).hexdigest()


class ProjectDatabase:
    """Persistent SQLite knowledge store for a TrashDig session.

    NOTE: Use `get_database(db_path)` instead of instantiating this class
    directly to benefit from instance caching.
    """

    def __init__(self, db_path: Optional[str] = None) -> None:
        if db_path is None:
            db_path = get_config().db_path
        self.db_path = db_path
        self._memory_conn: Optional[sqlite3.Connection] = None
        if db_path != ":memory:":
            os.makedirs(os.path.dirname(db_path) if os.path.dirname(db_path) else ".", exist_ok=True)
        self._init_db()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.executescript(_DDL)

    @contextmanager
    def _connect(self) -> Generator[sqlite3.Connection, None, None]:
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

    def __del__(self) -> None:
        if self._memory_conn:
            self._memory_conn.close()

    # ------------------------------------------------------------------
    # Project profiles
    # ------------------------------------------------------------------

    def save_project_profile(
        self,
        project_path: str,
        tech_stack: str,
        profile: Dict[str, Any],
    ) -> None:
        """Upsert the Archaeologist's project profile for *project_path*.

        Args:
            project_path: The root directory of the scanned project.
            tech_stack: Short human-readable description of the tech stack.
            profile: The full scan mapping dict to persist as JSON.
        """
        now = _now()
        profile_json = json.dumps(profile, default=str)
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO project_profiles
                    (project_path, tech_stack, profile_json, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(project_path) DO UPDATE SET
                    tech_stack   = excluded.tech_stack,
                    profile_json = excluded.profile_json,
                    updated_at   = excluded.updated_at
                """,
                (project_path, tech_stack, profile_json, now, now),
            )

    def get_project_profile(self, project_path: str) -> Optional[Dict[str, Any]]:
        """Return the stored profile for *project_path*, or ``None``.

        Args:
            project_path: The root directory of the scanned project.

        Returns:
            A dict with keys ``tech_stack``, ``profile``, ``created_at``,
            ``updated_at``, or ``None`` if no profile exists yet.
        """
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM project_profiles WHERE project_path = ?",
                (project_path,),
            ).fetchone()
        if row is None:
            return None
        return {
            "tech_stack": row["tech_stack"],
            "profile": json.loads(row["profile_json"]) if row["profile_json"] else {},
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }

    # ------------------------------------------------------------------
    # Findings
    # ------------------------------------------------------------------

    def save_finding(self, project_path: str, finding: Any) -> int:
        """Persist a ``Finding`` instance, returning its database row ID.

        Duplicate findings (same project_path + title + file_path) are
        updated in place rather than duplicated.

        Args:
            project_path: The root directory of the scanned project.
            finding: A ``trashdig.findings.Finding`` instance.

        Returns:
            The integer row ID of the inserted or updated row.
        """
        now = _now()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO findings (
                    project_path, title, description, severity, vulnerable_code,
                    file_path, impact, exploitation_path, remediation, cwe_id,
                    verification_status, poc, timestamp
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(project_path, title, file_path) DO UPDATE SET
                    description         = excluded.description,
                    severity            = excluded.severity,
                    vulnerable_code     = excluded.vulnerable_code,
                    impact              = excluded.impact,
                    exploitation_path   = excluded.exploitation_path,
                    remediation         = excluded.remediation,
                    cwe_id              = excluded.cwe_id,
                    verification_status = excluded.verification_status,
                    poc                 = excluded.poc,
                    timestamp           = excluded.timestamp
                """,
                (
                    project_path,
                    finding.title,
                    finding.description,
                    finding.severity,
                    finding.vulnerable_code,
                    finding.file_path,
                    finding.impact,
                    finding.exploitation_path,
                    finding.remediation,
                    finding.cwe_id,
                    finding.verification_status,
                    finding.poc,
                    finding.timestamp if hasattr(finding, "timestamp") else now,
                ),
            )
            row = conn.execute(
                "SELECT id FROM findings WHERE project_path = ? AND title = ? AND file_path = ?",
                (project_path, finding.title, finding.file_path),
            ).fetchone()
        return row["id"] if row else -1

    def update_finding_status(
        self,
        project_path: str,
        title: str,
        file_path: str,
        status: str,
        poc: Optional[str] = None,
    ) -> None:
        """Update the verification status (and optionally PoC) for a finding.

        Args:
            project_path: The root directory of the scanned project.
            title: The finding title.
            file_path: The file the finding was found in.
            status: New verification status string.
            poc: Optional PoC code to attach.
        """
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE findings
                SET verification_status = ?,
                    poc = COALESCE(?, poc)
                WHERE project_path = ? AND title = ? AND file_path = ?
                """,
                (status, poc, project_path, title, file_path),
            )

    def get_findings(self, project_path: str) -> List[Dict[str, Any]]:
        """Return all findings stored for *project_path*.

        Args:
            project_path: The root directory of the scanned project.

        Returns:
            A list of dicts, each representing one finding row.
        """
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM findings WHERE project_path = ? ORDER BY id",
                (project_path,),
            ).fetchall()
        return [dict(r) for r in rows]

    # ------------------------------------------------------------------
    # Hypotheses
    # ------------------------------------------------------------------

    def save_hypothesis(self, project_path: str, hypothesis: Any) -> int:
        """Persist a ``Hypothesis`` task, returning its database row ID.

        Args:
            project_path: The root directory of the scanned project.
            hypothesis: A ``trashdig.agents.types.Hypothesis`` instance.

        Returns:
            The integer row ID of the inserted row (or existing row if the
            task_id already exists).
        """
        now = _now()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR IGNORE INTO hypotheses
                    (project_path, task_id, target, description, confidence,
                     status, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, 'pending', ?, ?)
                """,
                (
                    project_path,
                    hypothesis.task_id,
                    hypothesis.target,
                    getattr(hypothesis, "description", ""),
                    getattr(hypothesis, "confidence", 0.0),
                    now,
                    now,
                ),
            )
            row = conn.execute(
                "SELECT id FROM hypotheses WHERE task_id = ?",
                (hypothesis.task_id,),
            ).fetchone()
        return row["id"] if row else -1

    def update_hypothesis_status(
        self,
        task_id: str,
        status: str,
        result: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Update the status and optional result of a stored hypothesis.

        Args:
            task_id: The UUID of the hypothesis task.
            status: New status string (e.g. 'completed', 'failed').
            result: Optional result payload to serialise as JSON.
        """
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE hypotheses
                SET status      = ?,
                    result_json = ?,
                    updated_at  = ?
                WHERE task_id = ?
                """,
                (status, json.dumps(result, default=str) if result else None, _now(), task_id),
            )

    def get_hypotheses(self, project_path: str) -> List[Dict[str, Any]]:
        """Return all hypotheses for *project_path*, including failed ones.

        Args:
            project_path: The root directory of the scanned project.

        Returns:
            A list of dicts, each representing one hypothesis row.
        """
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM hypotheses WHERE project_path = ? ORDER BY id",
                (project_path,),
            ).fetchall()
        results = []
        for r in rows:
            d = dict(r)
            if d.get("result_json"):
                d["result"] = json.loads(d["result_json"])
            else:
                d["result"] = None
            del d["result_json"]
            results.append(d)
        return results

    # ------------------------------------------------------------------
    # Symbol map
    # ------------------------------------------------------------------

    def save_symbol(
        self,
        project_path: str,
        symbol_name: str,
        file_path: str,
        line_number: int,
        symbol_type: str = "unknown",
    ) -> None:
        """Insert or silently ignore a symbol location into the symbol map.

        Args:
            project_path: The root directory of the scanned project.
            symbol_name: The name of the symbol (function, class, etc.).
            file_path: The file where the symbol is defined.
            line_number: The line number of the symbol definition.
            symbol_type: Category string (e.g. 'function', 'class').
        """
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR IGNORE INTO symbol_map
                    (project_path, symbol_name, file_path, line_number, symbol_type)
                VALUES (?, ?, ?, ?, ?)
                """,
                (project_path, symbol_name, file_path, line_number, symbol_type),
            )

    def get_symbol(self, project_path: str, symbol_name: str) -> List[Dict[str, Any]]:
        """Look up all known locations for a symbol.

        Args:
            project_path: The root directory of the scanned project.
            symbol_name: The name of the symbol to look up.

        Returns:
            A list of dicts with keys ``file_path``, ``line_number``,
            ``symbol_type``.
        """
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT file_path, line_number, symbol_type
                FROM symbol_map
                WHERE project_path = ? AND symbol_name = ?
                ORDER BY file_path, line_number
                """,
                (project_path, symbol_name),
            ).fetchall()
        return [dict(r) for r in rows]

    # ------------------------------------------------------------------
    # Tool output cache
    # ------------------------------------------------------------------

    def cache_tool_output(
        self,
        project_path: str,
        tool_name: str,
        args: Dict[str, Any],
        output: str,
    ) -> None:
        """Store the output of an expensive tool call for later reuse.

        Args:
            project_path: The root directory of the scanned project.
            tool_name: The name of the tool function.
            args: The keyword arguments the tool was called with.
            output: The string output returned by the tool.
        """
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO tool_cache
                    (project_path, tool_name, args_hash, output, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (project_path, tool_name, _args_hash(args), output, _now()),
            )

    def get_cached_tool_output(
        self,
        project_path: str,
        tool_name: str,
        args: Dict[str, Any],
    ) -> Optional[str]:
        """Return a previously cached tool output, or ``None`` if not found.

        Args:
            project_path: The root directory of the scanned project.
            tool_name: The name of the tool function.
            args: The keyword arguments the tool was called with.

        Returns:
            The cached output string, or ``None``.
        """
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT output FROM tool_cache
                WHERE project_path = ? AND tool_name = ? AND args_hash = ?
                """,
                (project_path, tool_name, _args_hash(args)),
            ).fetchone()
        return row["output"] if row else None

    # ------------------------------------------------------------------
    # Conversations
    # ------------------------------------------------------------------

    def log_conversation(
        self,
        project_path: str,
        agent_name: str,
        prompt: str,
        response: Optional[str],
        tool_calls: List[Dict[str, Any]],
        input_tokens: int,
        output_tokens: int,
    ) -> None:
        """Persist a structured conversation turn to the database.

        Args:
            project_path: The root directory of the scanned project.
            agent_name: The name of the agent that performed the interaction.
            prompt: The text prompt sent to the LLM.
            response: The final text response from the LLM.
            tool_calls: A list of dicts {name: str, args: dict} for each tool call.
            input_tokens: Number of prompt tokens used.
            output_tokens: Number of response/tool-call tokens used.
        """
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO conversations (
                    project_path, agent_name, prompt, response, tool_calls,
                    input_tokens, output_tokens, timestamp
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    project_path,
                    agent_name,
                    prompt,
                    response,
                    json.dumps(tool_calls, default=str),
                    input_tokens,
                    output_tokens,
                    _now(),
                ),
            )

    # ------------------------------------------------------------------
    # Scan sessions
    # ------------------------------------------------------------------

    def get_or_create_scan_session(self, project_path: str) -> str:
        """Return the most recent open scan session ID for *project_path*.

        If no open session exists, create and return a new UUID. This gives
        the Coordinator a stable ID to pass to Engine.run() so all agent
        calls within one scan invocation share the same ADK session row.
        On an unclean exit the open session is reused, enabling resumption.

        Args:
            project_path: The root directory of the scanned project.

        Returns:
            A UUID string suitable for use as an ADK ``session_id``.
        """
        if not isinstance(project_path, str):
            # Handle cases where a Mock might have been passed in tests
            project_path = str(project_path)
            
        import uuid as _uuid
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT session_id FROM scan_sessions
                WHERE project_path = ? AND ended_at IS NULL
                ORDER BY id DESC LIMIT 1
                """,
                (project_path,),
            ).fetchone()
            if row:
                return row["session_id"]
            new_id = str(_uuid.uuid4())
            conn.execute(
                """
                INSERT INTO scan_sessions (project_path, session_id, started_at)
                VALUES (?, ?, ?)
                """,
                (project_path, new_id, _now()),
            )
        return new_id

    def close_scan_session(self, session_id: str) -> None:
        """Mark a scan session as ended.

        Called on clean exit so the next invocation starts a fresh session
        rather than resuming the completed one.

        Args:
            session_id: The UUID of the scan session to close.
        """
        with self._connect() as conn:
            conn.execute(
                "UPDATE scan_sessions SET ended_at = ? WHERE session_id = ?",
                (_now(), session_id),
            )
