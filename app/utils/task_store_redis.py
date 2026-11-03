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


def lookup_task(client: Any, task_id: str) -> tuple[str, Optional[Dict[str, Any]]]:
    """区分空 Hash 与 Redis 异常。

    返回 ("found", record)、("missing", None) 或 ("error", None)。
    """
    try:
        h = client.hgetall(task_key(task_id))
        if not h:
            return "missing", None
        return "found", _decode_hash(h)
    except Exception:
        logger.exception("task_store_redis.get_task failed task_id=%s", task_id)
        return "error", None


def get_task(client: Any, task_id: str) -> Optional[Dict[str, Any]]:
    """读任务。Key 不存在时返回 None。Redis 异常时抛出，不能当成缺记录。"""
    kind, rec = lookup_task(client, task_id)
    if kind == "error":
        raise RuntimeError(f"task_store_redis.get_task failed task_id={task_id}")
    return rec


def list_tasks(client: Any) -> List[Dict[str, Any]]:
    try:
        ids = client.zrevrange(index_key(), 0, -1) or []
        out: List[Dict[str, Any]] = []
        for tid in ids:
            kind, rec = lookup_task(client, tid)
            if kind == "found" and rec:
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


def extend_lease_if_present(client: Any, task_id: str, ttl: Optional[int] = None) -> bool:
    """只刷新仍存在的租约 TTL，不把已过期的 key 重新创建出来。"""
    try:
        return bool(client.expire(lease_key(task_id), ttl or get_lease_ttl_sec()))
    except Exception:
        logger.exception("task_store_redis.extend_lease_if_present failed task_id=%s", task_id)
        return False


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
        raise
