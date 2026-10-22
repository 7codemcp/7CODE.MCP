"""7CODE opt-in durable project memory. Standard library only.

The database belongs to the local operator, not a remote chat. Memory never
stores full file contents, command output, screenshots, or credentials implicitly.
"""
from __future__ import annotations

from contextlib import closing
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import sqlite3
import threading
from uuid import uuid4

MAX_TEXT = 8000
_ALLOWED_STATUS = {"planned", "active", "blocked", "completed", "paused"}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _text(value: str, label: str, limit: int = MAX_TEXT) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > limit:
        raise ValueError(f"{label} must be nonempty text of at most {limit} characters")
    return value.strip()


def _clean_metadata(record: dict) -> dict:
    """Allow-list operational fields only; never persist arbitrary tool arguments."""
    safe = {}
    for key in ("id", "tool", "result", "error_type", "job_id", "exit_code",
                "path", "root", "cwd", "source", "destination", "executable",
                "overwrite", "encoding", "timeout_seconds", "offset", "length",
                "line", "utc"):
        val = record.get(key)
        if isinstance(val, (str, int, float, bool)) or val is None:
            if key == "executable" and isinstance(val, str):
                val = Path(val).name
            if isinstance(val, str):
                val = val[:2048]
            safe[key] = val
    return safe


class MemoryStore:
    def __init__(self, state: Path):
        self.state = Path(state)
        self.settings = self.state / "memory-settings.json"
        self.database = self.state / "memory.sqlite3"
        self.lock = threading.RLock()
        self._session = uuid4().hex

    def enabled(self) -> bool:
        if not self.settings.is_file():
            return False
        try:
            data = json.loads(self.settings.read_text(encoding="utf-8"))
            return data.get("enabled") is True
        except (ValueError, OSError):
            return False

    def configure_local(self, enabled: bool) -> dict:
        """Only exposed by the local on-machine CLI; never via MCP."""
        if type(enabled) is not bool:
            raise TypeError("enabled must be boolean")
        with self.lock:
            self.state.mkdir(parents=True, exist_ok=True)
            temp = self.settings.with_name("memory-settings-" + uuid4().hex + ".tmp")
            try:
                with temp.open("x", encoding="utf-8") as f:
                    json.dump({"enabled": enabled, "version": 1}, f)
                    f.flush()
                    os.fsync(f.fileno())
                os.replace(temp, self.settings)
            finally:
                temp.unlink(missing_ok=True)
            if enabled:
                self._initialize()
            return self.status()

    def _connect(self) -> sqlite3.Connection:
        self.state.mkdir(parents=True, exist_ok=True)
        con = sqlite3.connect(self.database, timeout=10)
        con.row_factory = sqlite3.Row
        con.execute("PRAGMA busy_timeout=10000")
        con.execute("PRAGMA journal_mode=WAL")
        con.execute("PRAGMA foreign_keys=ON")
        return con

    def _initialize(self) -> None:
        with closing(self._connect()) as con, con:
            con.executescript("""
                CREATE TABLE IF NOT EXISTS projects (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    root_path TEXT NOT NULL UNIQUE,
                    objective TEXT NOT NULL,
                    summary TEXT NOT NULL DEFAULT '',
                    next_step TEXT NOT NULL DEFAULT '',
                    status TEXT NOT NULL DEFAULT 'active',
                    created_utc TEXT NOT NULL,
                    updated_utc TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS checkpoints (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_id TEXT NOT NULL REFERENCES projects(id),
                    summary TEXT NOT NULL,
                    next_step TEXT NOT NULL,
                    details TEXT NOT NULL DEFAULT '',
                    status TEXT NOT NULL,
                    created_utc TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_checkpoints_project
                    ON checkpoints(project_id, id DESC);
                CREATE TABLE IF NOT EXISTS activity (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_id TEXT REFERENCES projects(id),
                    session_id TEXT NOT NULL,
                    utc TEXT NOT NULL,
                    tool TEXT NOT NULL,
                    result TEXT NOT NULL,
                    metadata TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_activity_project
                    ON activity(project_id, id DESC);
            """)

    def _required(self) -> None:
        if not self.enabled():
            raise PermissionError("Local memory disabled; only the PC operator can enable it.")

    def status(self) -> dict:
        result = {"enabled": self.enabled(), "database": str(self.database),
                  "database_exists": self.database.is_file(),
                  "memory_is_local": True, "remote_toggle_allowed": False}
        if result["enabled"]:
            with self.lock:
                self._initialize()
                with closing(self._connect()) as con, con:
                    result["projects"] = con.execute("SELECT COUNT(*) FROM projects").fetchone()[0]
                    result["activities"] = con.execute("SELECT COUNT(*) FROM activity").fetchone()[0]
                    result["checkpoints"] = con.execute("SELECT COUNT(*) FROM checkpoints").fetchone()[0]
        return result

    def project_create(self, name: str, root_path: str, objective: str) -> dict:
        self._required()
        name = _text(name, "name", 120)
        objective = _text(objective, "objective", 2000)
        try:
            path = Path(_text(root_path, "root_path", 32760)).resolve(strict=True)
        except OSError as exc:
            raise ValueError("Project root must be an existing directory") from exc
        if not path.is_dir():
            raise ValueError("Project root must be an existing directory")
        if path == self.state or self.state in path.parents or path == Path(path.anchor):
            raise ValueError("Unsafe project directory")
        identifier, now = uuid4().hex, _now()
        with self.lock:
            self._initialize()
            with closing(self._connect()) as con, con:
                con.execute("INSERT INTO projects(id,name,root_path,objective,created_utc,updated_utc) VALUES(?,?,?,?,?,?)",
                            (identifier, name, str(path), objective, now, now))
        return {"project_id": identifier, "name": name, "root_path": str(path), "objective": objective}

    def project_list(self, limit: int = 50) -> dict:
        self._required()
        if type(limit) is not int or not 1 <= limit <= 100:
            raise ValueError("limit must be 1..100")
        with self.lock:
            self._initialize()
            with closing(self._connect()) as con, con:
                rows = con.execute("SELECT * FROM projects ORDER BY updated_utc DESC LIMIT ?", (limit,)).fetchall()
                return {"projects": [dict(r) for r in rows]}

    def checkpoint(self, project_id: str, summary: str, next_step: str,
                   details: str = "", status: str = "active") -> dict:
        self._required()
        project_id = _text(project_id, "project_id", 64)
        summary = _text(summary, "summary", 2000)
        next_step = _text(next_step, "next_step", 2000)
        if not isinstance(details, str) or len(details) > MAX_TEXT:
            raise ValueError("details may contain at most 8000 characters")
        if status not in _ALLOWED_STATUS:
            raise ValueError("Invalid project status")
        now = _now()
        with self.lock:
            self._initialize()
            with closing(self._connect()) as con, con:
                cur = con.execute("UPDATE projects SET summary=?,next_step=?,status=?,updated_utc=? WHERE id=?",
                                  (summary, next_step, status, now, project_id))
                if cur.rowcount != 1:
                    raise ValueError("Project not found")
                item = con.execute("INSERT INTO checkpoints(project_id,summary,next_step,details,status,created_utc) VALUES(?,?,?,?,?,?)",
                                   (project_id, summary, next_step, details, status, now))
                return {"checkpoint_id": item.lastrowid, "project_id": project_id, "saved_utc": now}

    def project_context(self, project_id: str, limit: int = 30) -> dict:
        self._required()
        if type(limit) is not int or not 1 <= limit <= 100:
            raise ValueError("limit must be 1..100")
        with self.lock:
            self._initialize()
            with closing(self._connect()) as con, con:
                row = con.execute("SELECT * FROM projects WHERE id=?", (project_id,)).fetchone()
                if row is None:
                    raise ValueError("Project not found")
                checkpoints = con.execute("SELECT * FROM checkpoints WHERE project_id=? ORDER BY id DESC LIMIT ?",
                                          (project_id, limit)).fetchall()
                events = con.execute("SELECT * FROM activity WHERE project_id=? ORDER BY id DESC LIMIT ?",
                                     (project_id, limit)).fetchall()
                return {"project": dict(row), "checkpoints": [dict(r) for r in checkpoints],
                        "recent_activity": [dict(r) for r in events]}

    def search(self, query: str, project_id: str | None = None, limit: int = 30) -> dict:
        self._required()
        query = _text(query, "query", 200)
        if type(limit) is not int or not 1 <= limit <= 100:
            raise ValueError("limit must be 1..100")
        # Escape SQL LIKE metacharacters; search user text literally.
        pattern = "%" + re.sub(r"([\\%_])", r"\\\1", query) + "%"
        clause = "AND project_id=?" if project_id else ""
        params = (pattern, pattern, project_id, limit) if project_id else (pattern, pattern, limit)
        with self.lock:
            self._initialize()
            with closing(self._connect()) as con, con:
                rows = con.execute(
                    "SELECT * FROM checkpoints WHERE (summary LIKE ? ESCAPE '\\' OR details LIKE ? ESCAPE '\\') "
                    + clause + " ORDER BY id DESC LIMIT ?", params).fetchall()
                return {"matches": [dict(r) for r in rows]}

    def record_audit(self, record: dict) -> None:
        if not self.enabled() or record.get("result") == "started":
            return
        clean = _clean_metadata(record)
        tool = clean.get("tool", "unknown")
        with self.lock:
            self._initialize()
            with closing(self._connect()) as con, con:
                projects = con.execute("SELECT id,root_path FROM projects").fetchall()
                project_id = None
                for key in ("path", "root", "cwd", "source", "destination"):
                    candidate = clean.get(key)
                    if not isinstance(candidate, str):
                        continue
                    for project in projects:
                        project_path = os.path.normcase(os.path.normpath(project["root_path"]))
                        candidate_path = os.path.normcase(os.path.normpath(candidate))
                        if candidate_path == project_path or candidate_path.startswith(project_path + os.sep):
                            project_id = project["id"]
                            break
                    if project_id:
                        break
                con.execute("INSERT INTO activity(project_id,session_id,utc,tool,result,metadata) VALUES(?,?,?,?,?,?)",
                            (project_id, self._session, _now(), tool, str(clean.get("result", "unknown")),
                             json.dumps(clean, ensure_ascii=False, sort_keys=True)))
