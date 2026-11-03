# Redis Task State + SSE Sharing Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在配置 `REDIS_URL` 时用 Redis 作为任务状态权威存储与 SSE Pub/Sub，使多 worker/多实例共享进度与流式推送；未配置或连接失败时回退现有 SQLite + 本地队列。

**Architecture:** 新增 `redis_client` / `task_store_redis`；`task_utils` 按 backend 分支（Redis 读穿、无权威热缓存、lease 懒回收；SQLite 保持热缓存写穿）；`sse_utils` 抽象 Local/Redis 总线。`task_utils` 对外 API 不变。

**Tech Stack:** Python 3.12、redis-py、fakeredis（测试）、现有 pytest / FastAPI SSE、SQLite `task_store`

## Global Constraints

- 有 `REDIS_URL` 且连接成功 → Redis（任务+SSE）；否则 → SQLite + 本地 SSE
- `REDIS_REQUIRED=0`（默认）时连接失败回退 SQLite；`=1` 时启动失败
- Redis 写失败只打日志，不阻断业务主流程
- 不改 `file_import_service` / 各节点业务逻辑 / 前端
- 不做断点续跑、SQLite→Redis 自动迁库、SSE 事件重放
- `done_list` / `running_list` 存原始节点 ID；仅持久化 `error`（不持久 `answer`）
- Redis 模式禁止启动时批量把 pending/processing 标 failed；用 lease 懒检测
- Key 前缀默认 `kb`（`REDIS_KEY_PREFIX`）
- 依赖装入 Conda 环境 `knowledge_base`；不引入 `pyproject.toml` / `uv`
- 本仓库若无 git，所有 Commit 步骤跳过
- Spec：`docs/superpowers/specs/2026-10-30-redis-task-sse-design.md`

---

## File Structure

| 文件 | 职责 |
|------|------|
| `app/utils/redis_client.py` | 解析环境变量、创建/缓存 Redis 连接、ping、测试注入 |
| `app/utils/task_store_redis.py` | Hash/ZSET/lease 的 upsert、delete、get、list、续约、清租约 |
| `app/utils/task_store.py` | 保持现有 SQLite（回退路径） |
| `app/utils/task_utils.py` | backend 选择；Redis 读穿+lease；SQLite 路径不变 |
| `app/utils/sse_utils.py` | LocalQueueBus / RedisPubSubBus；push / generator |
| `tests/test_redis_client.py` | 配置与连接选择 |
| `tests/test_task_store_redis.py` | Redis store + lease |
| `tests/test_task_utils_redis.py` | 多 client 共享、lease 过期、SQLite 回归不受影响 |
| `tests/test_sse_redis.py` | 跨 client Pub/Sub |
| `README.md` / `docs/技术架构.md` / `docs/项目背景.md` | 文档 |

---

### Task 1: `redis_client` + 单元测试

**Files:**
- Create: `app/utils/redis_client.py`
- Create: `tests/test_redis_client.py`

**Interfaces:**
- Produces:
  - `get_redis_url() -> str` — `os.environ.get("REDIS_URL","").strip()`
  - `get_key_prefix() -> str` — 默认 `"kb"`
  - `get_lease_ttl_sec() -> int` — 默认 `30`
  - `redis_required() -> bool` — `REDIS_REQUIRED` in `("1","true","yes")`（大小写不敏感）
  - `set_client_for_tests(client) -> None` / `reset_client_for_tests() -> None`
  - `get_client()` — 返回缓存的 redis 客户端；无 URL 返回 `None`；连接失败时若 `redis_required()` 则 raise，否则返回 `None` 并打日志
  - `ping_client(client) -> bool`

- [ ] **Step 1: 安装依赖（Conda 环境）**

```bash
conda activate knowledge_base
pip install redis fakeredis
python -c "import redis, fakeredis; print(redis.__version__, fakeredis.__version__)"
```

Expected: 打印版本号，无 ImportError

- [ ] **Step 2: Write failing tests**

```python
# tests/test_redis_client.py
import os

import pytest
import fakeredis

from app.utils import redis_client


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    monkeypatch.delenv("REDIS_URL", raising=False)
    monkeypatch.delenv("REDIS_KEY_PREFIX", raising=False)
    monkeypatch.delenv("TASK_LEASE_TTL_SEC", raising=False)
    monkeypatch.delenv("REDIS_REQUIRED", raising=False)
    redis_client.reset_client_for_tests()
    yield
    redis_client.reset_client_for_tests()


def test_defaults():
    assert redis_client.get_redis_url() == ""
    assert redis_client.get_key_prefix() == "kb"
    assert redis_client.get_lease_ttl_sec() == 30
    assert redis_client.redis_required() is False
    assert redis_client.get_client() is None


def test_prefix_and_ttl(monkeypatch):
    monkeypatch.setenv("REDIS_KEY_PREFIX", "demo")
    monkeypatch.setenv("TASK_LEASE_TTL_SEC", "45")
    assert redis_client.get_key_prefix() == "demo"
    assert redis_client.get_lease_ttl_sec() == 45


def test_inject_fake_client():
    fake = fakeredis.FakeStrictRedis(decode_responses=True)
    redis_client.set_client_for_tests(fake)
    assert redis_client.get_client() is fake
    assert redis_client.ping_client(fake) is True
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `cd /Users/tianziru/Documents/project/knowledge_base && conda run -n knowledge_base pytest tests/test_redis_client.py -v`

Expected: FAIL（模块或符号不存在）

- [ ] **Step 4: Implement `app/utils/redis_client.py`**

```python
from __future__ import annotations

import logging
import os
from typing import Any, Optional

logger = logging.getLogger(__name__)

_client: Optional[Any] = None
_injected: bool = False


def get_redis_url() -> str:
    return os.environ.get("REDIS_URL", "").strip()


def get_key_prefix() -> str:
    return os.environ.get("REDIS_KEY_PREFIX", "kb").strip() or "kb"


def get_lease_ttl_sec() -> int:
    raw = os.environ.get("TASK_LEASE_TTL_SEC", "30").strip() or "30"
    try:
        return max(1, int(raw))
    except ValueError:
        return 30


def redis_required() -> bool:
    return os.environ.get("REDIS_REQUIRED", "0").strip().lower() in ("1", "true", "yes")


def set_client_for_tests(client: Any) -> None:
    global _client, _injected
    _client = client
    _injected = True


def reset_client_for_tests() -> None:
    global _client, _injected
    _client = None
    _injected = False


def ping_client(client: Any) -> bool:
    try:
        return bool(client.ping())
    except Exception:
        logger.exception("redis ping failed")
        return False


def get_client() -> Optional[Any]:
    global _client
    if _injected:
        return _client
    if _client is not None:
        return _client
    url = get_redis_url()
    if not url:
        return None
    try:
        import redis

        client = redis.Redis.from_url(url, decode_responses=True)
        if not ping_client(client):
            raise RuntimeError("redis ping failed")
        _client = client
        return _client
    except Exception:
        logger.exception("redis connect failed url=%s", url)
        if redis_required():
            raise
        return None
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `conda run -n knowledge_base pytest tests/test_redis_client.py -v`

Expected: PASS

- [ ] **Step 6: Commit（若无 git 则跳过）**

```bash
git add app/utils/redis_client.py tests/test_redis_client.py
git commit -m "$(cat <<'EOF'
feat: add redis_client helpers for optional Redis backend

EOF
)"
```

---

### Task 2: `task_store_redis` + lease API

**Files:**
- Create: `app/utils/task_store_redis.py`
- Create: `tests/test_task_store_redis.py`

**Interfaces:**
- Consumes: `redis_client.get_key_prefix`, `get_lease_ttl_sec`, injected client
- Produces:
  - `task_key(task_id) -> str` / `lease_key(task_id) -> str` / `index_key() -> str`
  - `upsert_task(client, record: Dict[str, Any]) -> None` — Hash + ZSET；`done_list`/`running_list` 序列化为 JSON；含可选 `owner`
  - `delete_task(client, task_id: str) -> None` — 删 Hash、ZSET member、lease
  - `get_task(client, task_id: str) -> Optional[Dict[str, Any]]`
  - `list_tasks(client) -> List[Dict[str, Any]]` — 按 ZSET 新到旧
  - `set_lease(client, task_id: str, worker_id: str, ttl: Optional[int] = None) -> None`
  - `renew_lease(client, task_id: str, worker_id: str, ttl: Optional[int] = None) -> None` — 同 set（EX 刷新）
  - `clear_lease(client, task_id: str) -> None`
  - `has_lease(client, task_id: str) -> bool`
  - Record 字段与 SQLite 对齐 + `owner`（缺省 `""`）

- [ ] **Step 1: Write failing tests**

```python
# tests/test_task_store_redis.py
import json
import time

import fakeredis
import pytest

from app.utils import task_store_redis as store


@pytest.fixture
def r():
    return fakeredis.FakeStrictRedis(decode_responses=True)


def _rec(tid="t1", status="processing", **kw):
    base = {
        "task_id": tid,
        "status": status,
        "file_name": "a.pdf",
        "file_size": 10,
        "created_at": "2026-10-30T10:00:00",
        "updated_at": "2026-10-30T10:01:00",
        "done_list": ["upload_file"],
        "running_list": ["node_entry"],
        "error": "",
        "owner": "w1",
    }
    base.update(kw)
    return base


def test_upsert_get_list_delete(r):
    store.upsert_task(r, _rec("t1"))
    store.upsert_task(r, _rec("t2", created_at="2026-10-30T11:00:00"))
    got = store.get_task(r, "t1")
    assert got["status"] == "processing"
    assert got["done_list"] == ["upload_file"]
    assert got["owner"] == "w1"
    ids = [x["task_id"] for x in store.list_tasks(r)]
    assert ids[0] == "t2"  # 更新时间/创建更新近的在前
    store.delete_task(r, "t1")
    assert store.get_task(r, "t1") is None


def test_lease_ttl_and_clear(r):
    store.set_lease(r, "t1", "w1", ttl=1)
    assert store.has_lease(r, "t1") is True
    time.sleep(1.1)
    assert store.has_lease(r, "t1") is False
    store.set_lease(r, "t1", "w1", ttl=30)
    store.clear_lease(r, "t1")
    assert store.has_lease(r, "t1") is False
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `conda run -n knowledge_base pytest tests/test_task_store_redis.py -v`

Expected: FAIL

- [ ] **Step 3: Implement `app/utils/task_store_redis.py`**

```python
from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from app.utils.redis_client import get_key_prefix, get_lease_ttl_sec

logger = logging.getLogger(__name__)


def task_key(task_id: str) -> str:
    return f"{get_key_prefix()}:task:{task_id}"


def lease_key(task_id: str) -> str:
    return f"{get_key_prefix()}:task:{task_id}:lease"


def index_key() -> str:
    return f"{get_key_prefix()}:tasks:index"


def _created_score(created_at: str) -> float:
    if not created_at:
        return 0.0
    try:
        return datetime.fromisoformat(created_at).timestamp()
    except Exception:
        return 0.0


def _encode_lists(record: Dict[str, Any]) -> Dict[str, str]:
    return {
        "task_id": str(record.get("task_id", "")),
        "status": str(record.get("status", "")),
        "file_name": str(record.get("file_name", "")),
        "file_size": str(int(record.get("file_size") or 0)),
        "created_at": str(record.get("created_at", "")),
        "updated_at": str(record.get("updated_at", "")),
        "done_list": json.dumps(record.get("done_list") or [], ensure_ascii=False),
        "running_list": json.dumps(record.get("running_list") or [], ensure_ascii=False),
        "error": str(record.get("error", "") or ""),
        "owner": str(record.get("owner", "") or ""),
    }


def _decode_hash(h: Dict[str, str]) -> Dict[str, Any]:
    if not h:
        return {}
    return {
        "task_id": h.get("task_id", ""),
        "status": h.get("status", ""),
        "file_name": h.get("file_name", ""),
        "file_size": int(h.get("file_size") or 0),
        "created_at": h.get("created_at", ""),
        "updated_at": h.get("updated_at", ""),
        "done_list": json.loads(h.get("done_list") or "[]"),
        "running_list": json.loads(h.get("running_list") or "[]"),
        "error": h.get("error", "") or "",
        "owner": h.get("owner", "") or "",
    }


def upsert_task(client: Any, record: Dict[str, Any]) -> None:
    try:
        tid = record.get("task_id") or ""
        if not tid:
            return
        mapping = _encode_lists(record)
        pipe = client.pipeline()
        pipe.hset(task_key(tid), mapping=mapping)
        pipe.zadd(index_key(), {tid: _created_score(mapping["created_at"])})
        pipe.execute()
    except Exception:
        logger.exception("task_store_redis.upsert_task failed task_id=%s", record.get("task_id"))


def delete_task(client: Any, task_id: str) -> None:
    try:
        pipe = client.pipeline()
        pipe.delete(task_key(task_id))
        pipe.zrem(index_key(), task_id)
        pipe.delete(lease_key(task_id))
        pipe.execute()
    except Exception:
        logger.exception("task_store_redis.delete_task failed task_id=%s", task_id)


def get_task(client: Any, task_id: str) -> Optional[Dict[str, Any]]:
    try:
        h = client.hgetall(task_key(task_id))
        if not h:
            return None
        return _decode_hash(h)
    except Exception:
        logger.exception("task_store_redis.get_task failed task_id=%s", task_id)
        return None


def list_tasks(client: Any) -> List[Dict[str, Any]]:
    try:
        ids = client.zrevrange(index_key(), 0, -1) or []
        out: List[Dict[str, Any]] = []
        for tid in ids:
            rec = get_task(client, tid)
            if rec:
                out.append(rec)
        return out
    except Exception:
        logger.exception("task_store_redis.list_tasks failed")
        return []


def set_lease(client: Any, task_id: str, worker_id: str, ttl: Optional[int] = None) -> None:
    try:
        client.set(lease_key(task_id), worker_id, ex=ttl or get_lease_ttl_sec())
    except Exception:
        logger.exception("task_store_redis.set_lease failed task_id=%s", task_id)


def renew_lease(client: Any, task_id: str, worker_id: str, ttl: Optional[int] = None) -> None:
    set_lease(client, task_id, worker_id, ttl=ttl)


def clear_lease(client: Any, task_id: str) -> None:
    try:
        client.delete(lease_key(task_id))
    except Exception:
        logger.exception("task_store_redis.clear_lease failed task_id=%s", task_id)


def has_lease(client: Any, task_id: str) -> bool:
    try:
        return bool(client.exists(lease_key(task_id)))
    except Exception:
        logger.exception("task_store_redis.has_lease failed task_id=%s", task_id)
        return False
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `conda run -n knowledge_base pytest tests/test_task_store_redis.py -v`

Expected: PASS

说明：若 `fakeredis` 对 `time.sleep` 后 TTL 不失效，改为 `r.expire(lease_key, 0)` 或 `r.delete` 模拟过期，并在测试注释中说明用手动删 key 代替等待。

- [ ] **Step 5: Commit（若无 git 则跳过）**

```bash
git add app/utils/task_store_redis.py tests/test_task_store_redis.py
git commit -m "$(cat <<'EOF'
feat: add Redis task store with hash index and leases

EOF
)"
```

---

### Task 3: `task_utils` 双后端（Redis 读穿 + lease）

**Files:**
- Modify: `app/utils/task_utils.py`
- Create: `tests/test_task_utils_redis.py`
- Keep green: `tests/test_task_utils_persistence.py`（无 REDIS_URL）

**Interfaces:**
- Consumes: `task_store`（SQLite）、`task_store_redis`、`redis_client.get_client`
- Produces（对外 API 不变）:
  - 新增 `reset_redis_persistence_for_tests(client) -> None` — 清空相关 key、注入 client、设 backend=redis、生成 `worker_id`、**不**批量标 failed
  - 新增内部 `_use_redis() -> bool`
  - Redis 路径：`register_task_meta` / `update_task_status` / `add_running_task` / `add_done_task` / `set_task_result(error)` / `clear_task` 写 Redis；读 API 从 Redis 取；pending/processing 写后 `set_lease`/`renew_lease`；completed/failed 时 `clear_lease`
  - 读路径懒检测：`_reap_if_lease_expired(task_id)` —— 若 status in pending/processing 且 `not has_lease` → 标 failed + error 文案 `任务租约过期（worker 可能已退出）` + 清空 running_list
  - `list_tasks` / `get_task_stats` / `get_task_status` 调用 reap
  - SQLite 路径：现有内存+写穿+`_mark_interrupted_tasks` 不变
  - 模块 import 时：若 `get_client()` 非空则 Redis 模式（不 bootstrap SQLite 中断逻辑）；否则现有 `_bootstrap_from_store()`

- [ ] **Step 1: Write failing Redis-mode tests**

```python
# tests/test_task_utils_redis.py
import os
import tempfile

import fakeredis
import pytest

# 收集阶段先钉住 SQLite，避免 import 写默认库
_fd, _COLLECT_DB = tempfile.mkstemp(prefix="task-utils-redis-collect-", suffix=".db")
os.close(_fd)
os.environ["TASK_STORE_PATH"] = _COLLECT_DB
os.environ.pop("REDIS_URL", None)

from app.utils import task_utils, redis_client


@pytest.fixture
def redis_mode():
    server = fakeredis.FakeServer()
    client = fakeredis.FakeStrictRedis(server=server, decode_responses=True)
    redis_client.set_client_for_tests(client)
    task_utils.reset_redis_persistence_for_tests(client)
    yield client
    redis_client.reset_client_for_tests()
    # 回到 SQLite 测试安全态
    task_utils.reset_persistence_for_tests(_COLLECT_DB)


def test_shared_across_logical_workers(redis_mode):
    task_utils.register_task_meta("t1", file_name="a.pdf", file_size=3)
    task_utils.update_task_status("t1", task_utils.TASK_STATUS_COMPLETED)
    # 第二「进程」：新 task_utils 读路径同一 FakeServer
    server = redis_mode.connection_pool.connection_kwargs.get("server") or redis_mode.server
    client_b = fakeredis.FakeStrictRedis(server=server, decode_responses=True)
    redis_client.set_client_for_tests(client_b)
    task_utils.reset_redis_persistence_for_tests(client_b)
    assert task_utils.get_task_status("t1") == task_utils.TASK_STATUS_COMPLETED
    assert task_utils.get_task_stats()["by_status"][task_utils.TASK_STATUS_COMPLETED] >= 1


def test_lease_expire_marks_failed(redis_mode, monkeypatch):
    monkeypatch.setenv("TASK_LEASE_TTL_SEC", "1")
    task_utils.register_task_meta("t2", file_name="b.pdf", file_size=1)
    task_utils.update_task_status("t2", task_utils.TASK_STATUS_PROCESSING)
    # 强制删 lease 模拟过期
    from app.utils import task_store_redis as rs
    rs.clear_lease(redis_mode, "t2")
    assert task_utils.get_task_status("t2") == task_utils.TASK_STATUS_FAILED
    assert "租约" in task_utils.get_task_result("t2", "error", "")


def test_redis_bootstrap_does_not_fail_all(redis_mode):
    task_utils.register_task_meta("t3", file_name="c.pdf", file_size=1)
    task_utils.update_task_status("t3", task_utils.TASK_STATUS_PROCESSING)
    task_utils.reset_redis_persistence_for_tests(redis_mode)  # 模拟本 worker 重启，lease 仍在
    # lease 仍存在时不得因「bootstrap」被标 failed
    assert task_utils.get_task_status("t3") == task_utils.TASK_STATUS_PROCESSING
```

说明：若 `FakeStrictRedis` 无 `.server` 属性，fixture 改为显式保存 `FakeServer()` 并在第二 client 复用。

- [ ] **Step 2: Run tests to verify they fail**

Run: `conda run -n knowledge_base pytest tests/test_task_utils_redis.py -v`

Expected: FAIL（`reset_redis_persistence_for_tests` 不存在或行为不符）

- [ ] **Step 3: 改造 `task_utils.py`（最小分支）**

在文件顶部增加：

```python
import uuid
from . import redis_client
from . import task_store_redis

_backend: str = "sqlite"  # "sqlite" | "redis"
_worker_id: str = str(uuid.uuid4())
_LEASE_EXPIRE_MSG = "任务租约过期（worker 可能已退出）"
```

实现要点（保持现有函数签名）：

```python
def _use_redis() -> bool:
    return _backend == "redis"


def reset_redis_persistence_for_tests(client) -> None:
    global _backend, _worker_id
    redis_client.set_client_for_tests(client)
    _backend = "redis"
    _worker_id = str(uuid.uuid4())
    _clear_memory()
    # 可选：删掉 prefix 下测试 key；或假定 FakeServer 干净
    # 不调用 _mark_interrupted_tasks


def _reap_if_lease_expired(task_id: str) -> None:
    if not _use_redis() or not task_id:
        return
    client = redis_client.get_client()
    if client is None:
        return
    rec = task_store_redis.get_task(client, task_id)
    if not rec:
        return
    if rec.get("status") not in (TASK_STATUS_PENDING, TASK_STATUS_PROCESSING):
        return
    if task_store_redis.has_lease(client, task_id):
        return
    rec["status"] = TASK_STATUS_FAILED
    rec["running_list"] = []
    rec["error"] = _LEASE_EXPIRE_MSG
    task_store_redis.upsert_task(client, rec)
    task_store_redis.clear_lease(client, task_id)


def _persist_task_redis(task_id: str) -> None:
    client = redis_client.get_client()
    if client is None:
        return
    snap = _snapshot_task(task_id)
    snap["owner"] = _worker_id
    # 若 Redis 无热缓存：应从 Redis get 合并，或维护写时的内存 staging。
    # 推荐实现：Redis 模式下仍用进程内 dict 作「本请求写缓冲」，
    # 但 list/get 以 Redis 为准并在读前 flush；更简单：每次写都 _snapshot 当前内存再 upsert，
    # 且 get_* 先读 Redis 填回内存单条（read-through）。
    task_store_redis.upsert_task(client, snap)
    status = _tasks_status.get(task_id, "")
    if status in (TASK_STATUS_PENDING, TASK_STATUS_PROCESSING):
        task_store_redis.renew_lease(client, task_id, _worker_id)
    else:
        task_store_redis.clear_lease(client, task_id)
```

**推荐读穿策略（写进实现）：**

1. Redis 模式写：更新本地 dict → upsert Redis → renew/clear lease（本地 dict 仅作单进程写缓冲，**不以 list_tasks 聚合本地全部 keys 为准**）。
2. Redis 模式读单个：`get_task` from Redis → 填本地单条 → reap → 返回。
3. Redis 模式 `list_tasks`：`task_store_redis.list_tasks` → 对每条 reap（若 status 变则已写回）→ 组装返回；**不要**用本地 `_tasks_*` 的 key 并集作为全集。

启动选择：

```python
def _select_backend_on_import() -> None:
    global _backend
    client = redis_client.get_client()
    if client is not None:
        _backend = "redis"
        return
    _backend = "sqlite"
    _bootstrap_from_store()


_select_backend_on_import()
```

将 `_persist_task` 改为：

```python
def _persist_task(task_id: str) -> None:
    if not task_id:
        return
    if _use_redis():
        with _state_lock:
            _ensure_task(task_id)
            _persist_task_redis(task_id)
        return
    with _state_lock:
        _ensure_task(task_id)
        task_store.upsert_task(_snapshot_task(task_id))
```

`get_task_status` / `list_tasks` 在 Redis 分支先 `_hydrate_from_redis` + `_reap_if_lease_expired`。

`reset_persistence_for_tests` 末尾设 `_backend = "sqlite"`。

- [ ] **Step 4: Run Redis tests**

Run: `conda run -n knowledge_base pytest tests/test_task_utils_redis.py -v`

Expected: PASS

- [ ] **Step 5: Run SQLite 回归**

Run: `conda run -n knowledge_base pytest tests/test_task_utils_persistence.py tests/test_task_store.py -v`

Expected: PASS（无 REDIS_URL）

- [ ] **Step 6: Commit（若无 git 则跳过）**

```bash
git add app/utils/task_utils.py tests/test_task_utils_redis.py
git commit -m "$(cat <<'EOF'
feat: dual-backend task_utils with Redis read-through and leases

EOF
)"
```

---

### Task 4: SSE Redis Pub/Sub 总线

**Files:**
- Modify: `app/utils/sse_utils.py`
- Create: `tests/test_sse_redis.py`

**Interfaces:**
- Consumes: `redis_client.get_client` / `get_key_prefix`
- Produces:
  - `sse_channel(session_id) -> str` → `{prefix}:sse:{session_id}`
  - `push_to_session(session_id, event, data)` — Redis 模式 `PUBLISH` JSON；Local 模式保持 queue
  - `sse_generator` — Redis 模式 SUBSCRIBE 循环；Local 不变
  - `set_sse_backend_for_tests("local"|"redis")`（可选，或跟随 `redis_client.get_client()`）
  - 对外函数名不变：`create_sse_queue` / `get_sse_queue` / `remove_sse_queue` 在 Redis 模式下可变为 no-op 或仅登记「本进程有人在听」（不作为 publish 前提）

- [ ] **Step 1: Write failing test**

```python
# tests/test_sse_redis.py
import json
import threading
import time

import fakeredis
import pytest

from app.utils import redis_client, sse_utils


@pytest.fixture
def shared_redis():
    server = fakeredis.FakeServer()
    a = fakeredis.FakeStrictRedis(server=server, decode_responses=True)
    b = fakeredis.FakeStrictRedis(server=server, decode_responses=True)
    redis_client.set_client_for_tests(a)
    yield a, b
    redis_client.reset_client_for_tests()


def test_pubsub_cross_client(shared_redis):
    a, b = shared_redis
    channel = sse_utils.sse_channel("s1")
    pubsub = b.pubsub(ignore_subscribe_messages=True)
    pubsub.subscribe(channel)
    # 等订阅就绪
    time.sleep(0.05)
    sse_utils.push_to_session("s1", "progress", {"status": "processing"})
    msg = None
    deadline = time.time() + 2
    while time.time() < deadline:
        msg = pubsub.get_message(timeout=0.2)
        if msg and msg.get("type") == "message":
            break
    assert msg is not None
    payload = json.loads(msg["data"])
    assert payload["event"] == "progress"
    assert payload["data"]["status"] == "processing"
    pubsub.unsubscribe(channel)
    pubsub.close()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `conda run -n knowledge_base pytest tests/test_sse_redis.py -v`

Expected: FAIL

- [ ] **Step 3: 改造 `sse_utils.py`**

在现有文件上增加（保留 Local 路径）：

```python
import logging
from app.utils import redis_client

logger = logging.getLogger(__name__)


def sse_channel(session_id: str) -> str:
    return f"{redis_client.get_key_prefix()}:sse:{session_id}"


def _redis_enabled() -> bool:
    return redis_client.get_client() is not None


def push_to_session(session_id: str, event: str, data: Dict[str, Any]):
    if _redis_enabled():
        try:
            client = redis_client.get_client()
            payload = json.dumps({"event": event, "data": data}, ensure_ascii=False)
            client.publish(sse_channel(session_id), payload)
        except Exception:
            logger.exception("sse redis publish failed session_id=%s", session_id)
        return
    stream_queue = get_sse_queue(session_id)
    if stream_queue:
        stream_queue.put({"event": event, "data": data})
    else:
        print(f"[SSE] Warning: No queue found for session {session_id} when pushing {event}")
```

`sse_generator` Redis 分支（概念代码，保持 async + disconnected 检查）：

```python
async def sse_generator(session_id: str, request: Request):
    if not _redis_enabled():
        # 现有 Local 实现整段保留
        ...
        return

    client = redis_client.get_client()
    pubsub = client.pubsub(ignore_subscribe_messages=True)
    channel = sse_channel(session_id)
    pubsub.subscribe(channel)
    loop = asyncio.get_running_loop()
    try:
        yield _sse_pack("ready", {})
        while True:
            if await request.is_disconnected():
                break
            msg = await loop.run_in_executor(
                None, lambda: pubsub.get_message(timeout=1.0)
            )
            if not msg or msg.get("type") != "message":
                continue
            payload = json.loads(msg["data"])
            event = payload.get("event")
            data = payload.get("data")
            if event == SSEEvent.CLOSE or event == "__close__":
                break
            yield _sse_pack(event, data)
    finally:
        try:
            pubsub.unsubscribe(channel)
            pubsub.close()
        except Exception:
            logger.exception("sse redis unsubscribe failed session_id=%s", session_id)
```

注意：查询服务里若仍调用 `create_sse_queue` 再跑图，Redis 模式下 `create_sse_queue` 可继续创建本地 queue 作兼容，但 **push 必须走 publish**，generator 必须走 subscribe，二者不以本地 queue 互通。

- [ ] **Step 4: 检查 query/import 中 create_sse_queue 调用点**

Run: `rg -n "create_sse_queue|sse_generator|push_to_session" app/`

若 `query_service` 在 stream 前 `create_sse_queue`：保留调用无妨；确认 stream 端走 `sse_generator` 即可。

- [ ] **Step 5: Run SSE + 全量相关测试**

Run: `conda run -n knowledge_base pytest tests/test_sse_redis.py tests/test_task_utils_redis.py tests/test_task_utils_persistence.py tests/test_redis_client.py tests/test_task_store_redis.py -v`

Expected: 全部 PASS

- [ ] **Step 6: Commit（若无 git 则跳过）**

```bash
git add app/utils/sse_utils.py tests/test_sse_redis.py
git commit -m "$(cat <<'EOF'
feat: Redis Pub/Sub backend for cross-worker SSE

EOF
)"
```

---

### Task 5: 文档与配置说明

**Files:**
- Modify: `README.md`
- Modify: `docs/技术架构.md`（§运行时拓扑、数据架构、已知限制、utils 表）
- Modify: `docs/项目背景.md`（任务状态相关段落）
- Modify: `.env`（仅追加注释示例行；**不要提交真实密码**）。若担心本地密钥，可只在 README 写示例，不改 `.env`。

- [ ] **Step 1: 更新 README**

替换「任务进度保存在导入服务进程内存中，重启后会丢失」为：

```markdown
- 任务状态默认写入 SQLite（`data/tasks.db`）；配置 `REDIS_URL` 后改用 Redis，供多实例共享任务进度与 SSE。
- 本机 Redis 示例：`docker run -d --name kb-redis -p 6379:6379 redis:7-alpine`
- 相关变量：`REDIS_URL`、`REDIS_KEY_PREFIX`（默认 `kb`）、`TASK_LEASE_TTL_SEC`（默认 `30`）、`REDIS_REQUIRED`（默认 `0`）
```

在「配置说明」增加上述变量一行表。

- [ ] **Step 2: 更新 `docs/技术架构.md`**

将「仅 SQLite + 热缓存、多 worker 不共享」改为：

- 默认 SQLite + 热缓存；可选 Redis 权威存储 + Pub/Sub SSE
- Redis 下用 lease 回收孤儿任务；禁止启动全局标 failed
- utils 表增加 `redis_client.py`、`task_store_redis.py`；更新 `task_utils` / `sse_utils` 描述

- [ ] **Step 3: 更新 `docs/项目背景.md`** 对应段落，与架构一致。

- [ ] **Step 4: 人工核对 spec 成功标准**

对照 `docs/superpowers/specs/2026-10-30-redis-task-sse-design.md`「测试成功标准」1–5，确认 Task 1–4 测试已覆盖。

- [ ] **Step 5: Commit（若无 git 则跳过）**

```bash
git add README.md docs/技术架构.md docs/项目背景.md
git commit -m "$(cat <<'EOF'
docs: document optional Redis task/SSE backend

EOF
)"
```

---

## Spec coverage（自检）

| Spec 项 | Task |
|---------|------|
| 双后端 REDIS_URL / SQLite 回退 | 1, 3 |
| Hash + ZSET + owner | 2 |
| Redis 无权威热缓存 / 读穿 | 3 |
| lease 心跳与懒检测、禁止启动批量 failed | 2, 3 |
| SSE Pub/Sub | 4 |
| 配置变量与 Docker 示例 | 1, 5 |
| 测试标准 1–5 | 3, 4 |
| README / 架构 / 背景文档 | 5 |
| 不做 resume / 迁库 / answer 持久化 | Global Constraints |

## Placeholder scan

无 TBD/TODO；Commit 步骤在无 git 时显式跳过。
