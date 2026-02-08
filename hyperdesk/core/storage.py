from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, List

from hyperdesk.core.models import Device, FileRequest, Session, TransferJob


def default_db_path() -> Path:
    root = Path.cwd()
    data_dir = root / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir / "hyperdesk.db"


class Storage:
    def __init__(self, db_path: Path | None = None) -> None:
        self.db_path = db_path or default_db_path()
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self._initialize()

    def close(self) -> None:
        self.conn.close()

    def record_device(self, device: Device) -> None:
        self._execute(
            """
            INSERT OR REPLACE INTO devices (id, name, ip, status, capabilities, last_seen)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                device.id,
                device.name,
                device.ip,
                device.status,
                ",".join(device.capabilities),
                _utc_now(),
            ),
        )

    def record_session(self, session: Session) -> None:
        self._execute(
            """
            INSERT OR REPLACE INTO sessions
            (id, host_device_id, peer_device_id, status, mode, approval_required, conflict_rule, token, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                session.id,
                session.host_device.id,
                session.peer_device.id,
                session.status,
                session.policy.mode,
                int(session.policy.approval_required),
                session.policy.conflict_rule,
                session.token,
                session.created_at.isoformat(),
            ),
        )

    def update_session_status(self, session_id: str, status: str) -> None:
        self._execute(
            "UPDATE sessions SET status = ? WHERE id = ?",
            (status, session_id),
        )

    def record_audit_event(self, session_id: str, event_type: str, details: str) -> None:
        self._execute(
            """
            INSERT INTO audit_events (session_id, event_type, details, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (session_id, event_type, details, _utc_now()),
        )

    def record_transfer(self, session_id: str, job: TransferJob) -> None:
        self._execute(
            """
            INSERT OR REPLACE INTO transfers
            (id, session_id, path, direction, status, progress, checksum, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                job.id,
                session_id,
                job.path,
                job.direction,
                job.status,
                job.progress,
                job.checksum,
                _utc_now(),
            ),
        )

    def record_request(self, request: FileRequest) -> None:
        self._execute(
            """
            INSERT OR REPLACE INTO file_requests
            (id, session_id, path, requester, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                request.id,
                request.session_id,
                request.path,
                request.requester,
                request.status,
                request.created_at.isoformat(),
            ),
        )

    def list_requests(self, session_id: str) -> List[FileRequest]:
        cursor = self.conn.execute(
            """
            SELECT id, session_id, path, requester, status, created_at
            FROM file_requests
            WHERE session_id = ?
            ORDER BY created_at DESC
            """,
            (session_id,),
        )
        return [
            FileRequest(
                id=row["id"],
                session_id=row["session_id"],
                path=row["path"],
                requester=row["requester"],
                status=row["status"],
                created_at=datetime.fromisoformat(row["created_at"]),
            )
            for row in cursor.fetchall()
        ]

    def list_requests_history(self, session_id: str | None = None) -> List[FileRequest]:
        if session_id:
            cursor = self.conn.execute(
                """
                SELECT id, session_id, path, requester, status, created_at
                FROM file_requests
                WHERE session_id = ?
                ORDER BY created_at DESC
                """,
                (session_id,),
            )
        else:
            cursor = self.conn.execute(
                """
                SELECT id, session_id, path, requester, status, created_at
                FROM file_requests
                ORDER BY created_at DESC
                """
            )
        return [
            FileRequest(
                id=row["id"],
                session_id=row["session_id"],
                path=row["path"],
                requester=row["requester"],
                status=row["status"],
                created_at=datetime.fromisoformat(row["created_at"]),
            )
            for row in cursor.fetchall()
        ]

    def list_sessions_with_peers(self) -> list[dict]:
        cursor = self.conn.execute(
            """
            SELECT sessions.id AS session_id,
                   sessions.peer_device_id AS peer_device_id,
                   devices.name AS peer_name
            FROM sessions
            LEFT JOIN devices ON sessions.peer_device_id = devices.id
            ORDER BY sessions.created_at DESC
            """
        )
        return [
            {
                "session_id": row["session_id"],
                "peer_device_id": row["peer_device_id"],
                "peer_name": row["peer_name"] or "Unknown",
            }
            for row in cursor.fetchall()
        ]

    def set_preference(self, key: str, value: str) -> None:
        self._execute(
            """
            INSERT OR REPLACE INTO preferences (key, value)
            VALUES (?, ?)
            """,
            (key, value),
        )

    def get_preference(self, key: str, default: str = "") -> str:
        cursor = self.conn.execute(
            "SELECT value FROM preferences WHERE key = ?",
            (key,),
        )
        row = cursor.fetchone()
        return row["value"] if row else default

    def list_preferences(self) -> dict[str, str]:
        cursor = self.conn.execute("SELECT key, value FROM preferences")
        return {row["key"]: row["value"] for row in cursor.fetchall()}

    def _initialize(self) -> None:
        self._execute(
            """
            CREATE TABLE IF NOT EXISTS devices (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                ip TEXT NOT NULL,
                status TEXT NOT NULL,
                capabilities TEXT NOT NULL,
                last_seen TEXT NOT NULL
            )
            """
        )
        self._execute(
            """
            CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY,
                host_device_id TEXT NOT NULL,
                peer_device_id TEXT NOT NULL,
                status TEXT NOT NULL,
                mode TEXT NOT NULL,
                approval_required INTEGER NOT NULL,
                conflict_rule TEXT,
                token TEXT,
                created_at TEXT NOT NULL
            )
            """
        )
        self._execute(
            """
            CREATE TABLE IF NOT EXISTS audit_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                event_type TEXT NOT NULL,
                details TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        self._execute(
            """
            CREATE TABLE IF NOT EXISTS transfers (
                id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                path TEXT NOT NULL,
                direction TEXT NOT NULL,
                status TEXT NOT NULL,
                progress REAL NOT NULL,
                checksum TEXT,
                updated_at TEXT NOT NULL
            )
            """
        )
        self._execute(
            """
            CREATE TABLE IF NOT EXISTS file_requests (
                id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                path TEXT NOT NULL,
                requester TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        self._execute(
            """
            CREATE TABLE IF NOT EXISTS preferences (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
            """
        )
        self._ensure_columns(
            "sessions",
            {
                "token": "TEXT",
                "conflict_rule": "TEXT",
            },
        )

    def _execute(self, statement: str, params: Iterable = ()) -> None:
        with self.conn:
            self.conn.execute(statement, params)

    def _ensure_columns(self, table: str, columns: dict[str, str]) -> None:
        cursor = self.conn.execute(f"PRAGMA table_info({table})")
        existing = {row["name"] for row in cursor.fetchall()}
        for name, definition in columns.items():
            if name not in existing:
                with self.conn:
                    self.conn.execute(
                        f"ALTER TABLE {table} ADD COLUMN {name} {definition}"
                    )


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()
