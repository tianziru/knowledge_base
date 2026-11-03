# Task Status SQLite Persistence Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 用 SQLite 持久化导入/查询任务状态与节点进度，使服务重启后概览「已完成」与 `/stats`、`/tasks` 仍正确。

**Architecture:** 新增 `task_store.py` 负责 SQLite；`task_utils.py` 保持现有 API，写操作改内存后写穿；启动时从 DB 加载，并将未结束任务标为 `failed`。

**Tech Stack:** Python 3 标准库 `sqlite3` / `json` / `threading` / `os`；pytest（新建测试目录）

## Global Constraints

- 库默认路径：`data/tasks.db`；可用环境变量 `TASK_STORE_PATH` 覆盖
- 写库失败只打日志，不阻断业务主流程
- 不改 `file_import_service` / 各节点业务逻辑；不改前端
- 不从 localStorage 回填；不做任务续跑
- `done_list` / `running_list` 存原始节点 ID（非中文）
- 仅持久化 `set_task_result` 的 `error` 键
- 本仓库若无 git，所有 Commit 步骤跳过

---

## File Structure

| 文件 | 职责 |
|------|------|
| `app/utils/task_store.py` | SQLite 建表、upsert、delete、load_all、线程锁 |
| `app/utils/task_utils.py` | 写穿调用 store；启动 bootstrap；中断任务标记 |
| `tests/test_task_store.py` | store 单元测试 |
| `tests/test_task_utils_persistence.py` | 写穿 + 模拟重启 |
| `docs/技术架构.md` | 去掉「任务状态非持久化」债务表述，改为 SQLite |
| `.gitignore`（若存在或新建） | 忽略 `data/tasks.db` |

---

### Task 1: `task_store` + 单元测试

**Files:**
- Create: `app/utils/task_store.py`
- Create: `tests/test_task_store.py`
- Create or modify: `.gitignore`（加入 `data/tasks.db`、`data/*.db`）

**Interfaces:**
- Produces:
  - `get_db_path() -> str`
  - `init_db(path: Optional[str] = None) -> None`
  - `upsert_task(record: Dict[str, Any]) -> None`
  - `delete_task(task_id: str) -> None`
  - `load_all() -> List[Dict[str, Any]]`
  - Record keys: `task_id`, `status`, `file_name`, `file_size`, `created_at`, `updated_at`, `done_list` (list[str]), `running_list` (list[str]), `error`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_task_store.py
import os
import tempfile
from pathlib import Path

import pytest

from app.utils import task_store


@pytest.fixture
def db_path(tmp_path):
    path = str(tmp_path / "tasks.db")
    os.environ["TASK_STORE_PATH"] = path
    task_store.init_db(path)
    yield path
    os.environ.pop("TASK_STORE_PATH", None)


def test_upsert_and_load(db_path):
    task_store.upsert_task({
        "task_id": "t1",
        "status": "completed",
        "file_name": "a.pdf",
        "file_size": 12,
        "created_at": "2026-10-28T10:00:00",
        "updated_at": "2026-10-28T10:01:00",
        "done_list": ["upload_file", "node_entry"],
        "running_list": [],
        "error": "",
    })
    rows = task_store.load_all()
    assert len(rows) == 1
    assert rows[0]["task_id"] == "t1"
    assert rows[0]["status"] == "completed"
    assert rows[0]["done_list"] == ["upload_file", "node_entry"]


def test_delete(db_path):
    task_store.upsert_task({
        "task_id": "t2",
        "status": "failed",
        "file_name": "",
        "file_size": 0,
        "created_at": "2026-10-28T10:00:00",
        "updated_at": "2026-10-28T10:00:00",
        "done_list": [],
        "running_list": [],
        "error": "x",
    })
    task_store.delete_task("t2")
    assert task_store.load_all() == []
```

- [ ] **Step 2: Run tests — expect FAIL**

Run: `cd /Users/tianziru/Documents/project/knowledge_base && python -m pytest tests/test_task_store.py -v`  
Expected: FAIL（`task_store` 不存在或缺符号）

- [ ] **Step 3: Implement `task_store.py`**

```python
# app/utils/task_store.py
from __future__ import annotations

import json
import logging
import os
import sqlite3
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

_lock = threading.Lock()
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
                pass
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
```

- [ ] **Step 4: Run tests — expect PASS**

Run: `python -m pytest tests/test_task_store.py -v`  
Expected: PASS

- [ ] **Step 5: Commit（有 git 时）**

```bash
git add app/utils/task_store.py tests/test_task_store.py .gitignore
git commit -m "$(cat <<'EOF'
feat: add SQLite task_store for import task persistence

EOF
)"
```

---

### Task 2: `task_utils` 写穿 + 启动 bootstrap + 模拟重启测试

**Files:**
- Modify: `app/utils/task_utils.py`
- Create: `tests/test_task_utils_persistence.py`

**Interfaces:**
- Consumes: `task_store.init_db`, `upsert_task`, `delete_task`, `load_all`, `get_db_path`
- Produces（新增，供测试）:
  - `reset_persistence_for_tests(db_path: str) -> None` — 清空内存、指向测试 DB、重新 bootstrap
  - 内部 `_persist_task(task_id: str) -> None`
  - 内部 `_bootstrap_from_store() -> None`

- [ ] **Step 1: Write failing persistence tests**

```python
# tests/test_task_utils_persistence.py
import os

import pytest

from app.utils import task_utils


@pytest.fixture
def fresh_store(tmp_path):
    path = str(tmp_path / "tasks.db")
    os.environ["TASK_STORE_PATH"] = path
    task_utils.reset_persistence_for_tests(path)
    yield path
    os.environ.pop("TASK_STORE_PATH", None)


def test_completed_survives_reload(fresh_store):
    task_utils.register_task_meta("t1", file_name="a.pdf", file_size=10)
    task_utils.update_task_status("t1", task_utils.TASK_STATUS_COMPLETED)
    task_utils.add_done_task("t1", "upload_file")

    # 模拟进程重启：清空内存再从 DB 加载
    task_utils.reset_persistence_for_tests(fresh_store)

    assert task_utils.get_task_status("t1") == task_utils.TASK_STATUS_COMPLETED
    stats = task_utils.get_task_stats()
    assert stats["by_status"][task_utils.TASK_STATUS_COMPLETED] == 1
    assert "开始上传文件" in task_utils.get_done_task_list("t1") or "upload_file" in str(
        task_utils.get_done_task_list("t1")
    )


def test_processing_becomes_failed_on_bootstrap(fresh_store):
    task_utils.register_task_meta("t2", file_name="b.pdf", file_size=1)
    task_utils.update_task_status("t2", task_utils.TASK_STATUS_PROCESSING)
    task_utils.add_running_task("t2", "node_entry")

    task_utils.reset_persistence_for_tests(fresh_store)

    assert task_utils.get_task_status("t2") == task_utils.TASK_STATUS_FAILED
    assert task_utils.get_running_task_list("t2") == []
    assert "重启" in task_utils.get_task_result("t2", "error", "")


def test_clear_task_removes_from_db(fresh_store):
    task_utils.register_task_meta("t3", file_name="c.pdf", file_size=1)
    task_utils.update_task_status("t3", task_utils.TASK_STATUS_COMPLETED)
    task_utils.clear_task("t3")
    task_utils.reset_persistence_for_tests(fresh_store)
    assert task_utils.get_task_stats()["total"] == 0
```

- [ ] **Step 2: Run tests — expect FAIL**

Run: `python -m pytest tests/test_task_utils_persistence.py -v`  
Expected: FAIL（缺 `reset_persistence_for_tests` / 未写穿）

- [ ] **Step 3: Wire persistence into `task_utils.py`**

在文件顶部增加：

```python
import logging
from . import task_store

logger = logging.getLogger(__name__)
```

在现有字典与常量之后增加：

```python
def _snapshot_task(task_id: str) -> Dict[str, Any]:
    meta = _tasks_meta.get(task_id, {})
    return {
        "task_id": task_id,
        "status": _tasks_status.get(task_id, ""),
        "file_name": meta.get("file_name", ""),
        "file_size": int(meta.get("file_size") or 0),
        "created_at": meta.get("created_at", ""),
        "updated_at": meta.get("updated_at", ""),
        "done_list": list(_tasks_done_list.get(task_id, [])),
        "running_list": list(_tasks_running_list.get(task_id, [])),
        "error": _tasks_result.get(task_id, {}).get("error", ""),
    }


def _persist_task(task_id: str) -> None:
    if not task_id:
        return
    _ensure_task(task_id)
    task_store.upsert_task(_snapshot_task(task_id))


def _clear_memory() -> None:
    _tasks_running_list.clear()
    _tasks_done_list.clear()
    _tasks_status.clear()
    _tasks_result.clear()
    _tasks_meta.clear()


def _load_record_into_memory(rec: Dict[str, Any]) -> None:
    tid = rec["task_id"]
    _ensure_task(tid)
    _tasks_status[tid] = rec.get("status") or ""
    _tasks_done_list[tid] = list(rec.get("done_list") or [])
    _tasks_running_list[tid] = list(rec.get("running_list") or [])
    _tasks_meta[tid] = {
        "file_name": rec.get("file_name") or "",
        "file_size": int(rec.get("file_size") or 0),
        "created_at": rec.get("created_at") or "",
        "updated_at": rec.get("updated_at") or "",
    }
    err = rec.get("error") or ""
    if err:
        _tasks_result[tid]["error"] = err


def _mark_interrupted_tasks() -> None:
    for tid, status in list(_tasks_status.items()):
        if status in (TASK_STATUS_PENDING, TASK_STATUS_PROCESSING):
            _tasks_status[tid] = TASK_STATUS_FAILED
            _tasks_running_list[tid] = []
            _ensure_task(tid)
            _tasks_result[tid]["error"] = "服务重启，任务中断"
            _persist_task(tid)


def _bootstrap_from_store() -> None:
    try:
        task_store.init_db()
        for rec in task_store.load_all():
            _load_record_into_memory(rec)
        _mark_interrupted_tasks()
    except Exception:
        logger.exception("task_utils bootstrap from store failed")


def reset_persistence_for_tests(db_path: str) -> None:
    """测试专用：清空内存并以指定 DB 重新 bootstrap。"""
    _clear_memory()
    task_store.init_db(db_path)
    for rec in task_store.load_all():
        _load_record_into_memory(rec)
    _mark_interrupted_tasks()
```

在写函数末尾调用 `_persist_task` / `delete_task`：

- `register_task_meta` 末尾：`_persist_task(task_id)`
- `update_task_status`：在赋值后 `_persist_task(task_id)`（push 之前或之后均可）
- `add_running_task` / `add_done_task`：改 list 后 `_persist_task(task_id)`
- `set_task_result`：仅当 `key == "error"` 时 `_persist_task(task_id)`
- `clear_task`：清内存后 `task_store.delete_task(task_id)`

模块末尾（所有函数定义之后）调用一次：

```python
_bootstrap_from_store()
```

注意：`get_done_task_list` / `get_running_task_list` 仍对内存中的原始 ID 做 `_to_cn`；DB 只存原始 ID。

- [ ] **Step 4: Run tests — expect PASS**

Run: `python -m pytest tests/test_task_store.py tests/test_task_utils_persistence.py -v`  
Expected: 全部 PASS

- [ ] **Step 5: Commit（有 git 时）**

```bash
git add app/utils/task_utils.py tests/test_task_utils_persistence.py
git commit -m "$(cat <<'EOF'
feat: persist task_utils state to SQLite across restarts

EOF
)"
```

---

### Task 3: 文档更新 + 手工冒烟

**Files:**
- Modify: `docs/技术架构.md`（约第 207 行「任务状态非持久化」）
- 可选：`docs/项目背景.md` 同类表述

- [ ] **Step 1: Update architecture docs**

将边界项改为类似：

> 任务状态持久化于 `data/tasks.db`（SQLite）；进程内内存为热缓存。多 worker 仍不共享同一内存视图，需共享同一 DB 文件并注意写锁。

- [ ] **Step 2: Manual smoke（导入服务）**

1. 启动导入服务（8000）。
2. 上传并完成至少 1 个小文件（或用已有短 PDF/MD）。
3. 打开概览，确认「已完成」≥ 1。
4. 确认 `data/tasks.db` 已生成。
5. 重启服务，再次打开概览：「已完成」应保持；`GET http://127.0.0.1:8000/stats` 中 `by_status.completed` 与重启前一致。
6. （可选）在任务进行中杀进程，重启后该任务应为 `failed`，error 含「服务重启」。

- [ ] **Step 3: Commit docs（有 git 时）**

```bash
git add docs/技术架构.md docs/项目背景.md
git commit -m "$(cat <<'EOF'
docs: note SQLite persistence for import task status

EOF
)"
```

---

## Spec coverage checklist

| Spec 项 | Task |
|---------|------|
| `task_store.py` | Task 1 |
| `task_utils` 写穿 + 启动加载 + 中断 failed | Task 2 |
| 字段完整（含 done/running/error） | Task 1–2 |
| `data/tasks.db` + 目录自动创建 + `TASK_STORE_PATH` | Task 1 |
| 架构文档更新 | Task 3 |
| 验收：重启后 completed 仍在 | Task 2 测试 + Task 3 冒烟 |
| 验收：delete 同步 | Task 2 `test_clear_task_removes_from_db` |
| 不做 localStorage / 续跑 / 前端改动 | 无对应实现任务 |

## Self-review notes

- 无 TBD；接口名在 Task 1/2 一致。
- `reset_persistence_for_tests` 仅测试用，生产靠模块 import 时 `_bootstrap_from_store()`。
- 若 pytest 未安装：`pip install pytest` 后再跑。
