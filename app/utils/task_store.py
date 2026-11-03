from __future__ import annotations

import json
import logging
import os
import sqlite3
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

_lock = threading.RLock()
_conn: Optional[sqlite3.Connection] = None
_db_path: Optional[str] = None

_SCHEMA = """
CREATE TABLE IF NOT EXISTS tasks (
    task_id TEXT PRIMARY KEY,
    status TEXT NOT NULL DEFAULT '',
    file_name TEXT NOT NULL DEFAULT '',
    file_size INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT '',
    updated_at TEXT NOT NULL DEFAULT '',
    done_list TEXT NOT NULL DEFAULT '[]',
    running_list TEXT NOT NULL DEFAULT '[]',
    error TEXT NOT NULL DEFAULT ''
);
"""


def get_db_path() -> str:
    env = os.environ.get("TASK_STORE_PATH", "").strip()
    if env:
        return env
    # 仓库根：app/utils/task_store.py → parents[2]
    root = Path(__file__).resolve().parents[2]
    return str(root / "data" / "tasks.db")


def init_db(path: Optional[str] = None) -> None:
    global _conn, _db_path
    db_path = path or get_db_path()
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    with _lock:
        if _conn is not None:
            try:
                _conn.close()
            except Exception:
                logger.exception("task_store.init_db failed to close previous connection")
            _conn = None
        _db_path = db_path
        conn = sqlite3.connect(db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute(_SCHEMA)
        conn.commit()
        _conn = conn


def _ensure_conn() -> sqlite3.Connection:
    global _conn
    if _conn is None:
        init_db()
    assert _conn is not None
    return _conn


def upsert_task(record: Dict[str, Any]) -> None:
    try:
        with _lock:
            conn = _ensure_conn()
            conn.execute(
                """
                INSERT INTO tasks (
                    task_id, status, file_name, file_size, created_at, updated_at,
                    done_list, running_list, error
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(task_id) DO UPDATE SET
                    status=excluded.status,
                    file_name=excluded.file_name,
                    file_size=excluded.file_size,
                    created_at=excluded.created_at,
                    updated_at=excluded.updated_at,
                    done_list=excluded.done_list,
                    running_list=excluded.running_list,
                    error=excluded.error
                """,
                (
                    record.get("task_id", ""),
                    record.get("status", ""),
                    record.get("file_name", ""),
                    int(record.get("file_size") or 0),
                    record.get("created_at", ""),
                    record.get("updated_at", ""),
                    json.dumps(record.get("done_list") or [], ensure_ascii=False),
                    json.dumps(record.get("running_list") or [], ensure_ascii=False),
                    record.get("error", "") or "",
                ),
            )
            conn.commit()
    except Exception:
        logger.exception("task_store.upsert_task failed task_id=%s", record.get("task_id"))


def delete_task(task_id: str) -> None:
    try:
        with _lock:
            conn = _ensure_conn()
            conn.execute("DELETE FROM tasks WHERE task_id = ?", (task_id,))
            conn.commit()
    except Exception:
        logger.exception("task_store.delete_task failed task_id=%s", task_id)


def load_all() -> List[Dict[str, Any]]:
    try:
        with _lock:
            conn = _ensure_conn()
            rows = conn.execute("SELECT * FROM tasks").fetchall()
        out: List[Dict[str, Any]] = []
        for r in rows:
            out.append({
                "task_id": r["task_id"],
                "status": r["status"] or "",
                "file_name": r["file_name"] or "",
                "file_size": int(r["file_size"] or 0),
                "created_at": r["created_at"] or "",
                "updated_at": r["updated_at"] or "",
                "done_list": json.loads(r["done_list"] or "[]"),
                "running_list": json.loads(r["running_list"] or "[]"),
                "error": r["error"] or "",
            })
        return out
    except Exception:
        logger.exception("task_store.load_all failed")
        return []
