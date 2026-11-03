from __future__ import annotations

import logging
import os
from typing import Any, Optional

logger = logging.getLogger(__name__)

_client: Optional[Any] = None
_injected: bool = False
# 首次 select_backend() 之后固定为 "redis" 或 "sqlite"，进程内不再重试连接。
_backend_mode: Optional[str] = None


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
    """注入 client，并把本进程后端钉在 Redis（client 为 None 时钉在 sqlite）。"""
    global _client, _injected, _backend_mode
    _client = client
    _injected = True
    _backend_mode = "redis" if client is not None else "sqlite"


def set_backend_mode_for_tests(mode: str) -> None:
    """测试专用：不探测 Redis，直接钉住后端。"""
    global _backend_mode
    if mode not in ("redis", "sqlite"):
        raise ValueError(mode)
    _backend_mode = mode


def reset_client_for_tests() -> None:
    """清掉 client 与已钉住的后端，让下一次 select_backend() 重新选择。"""
    global _client, _injected, _backend_mode
    _client = None
    _injected = False
    _backend_mode = None


def ping_client(client: Any) -> bool:
    try:
        return bool(client.ping())
    except Exception:
        logger.exception("redis ping failed")
        return False


def _connect(url: str) -> Any:
    import redis

    client = redis.Redis.from_url(url, decode_responses=True)
    if not ping_client(client):
        raise RuntimeError("redis ping failed")
    return client


def select_backend() -> str:
    """为本进程选定 redis 或 sqlite，只决定一次。

    无 URL，或连接失败且 REDIS_REQUIRED=0：固定 sqlite，之后不再探测。
    REDIS_REQUIRED=1 且连接失败：抛出异常，不把失败记成 sqlite。
    """
    global _backend_mode, _client
    if _backend_mode is not None:
        return _backend_mode
    if _injected:
        _backend_mode = "redis" if _client is not None else "sqlite"
        return _backend_mode
    url = get_redis_url()
    if not url:
        _backend_mode = "sqlite"
        return _backend_mode
    try:
        _client = _connect(url)
    except Exception:
        logger.exception("redis connect failed url=%s", url)
        if redis_required():
            raise
        _client = None
        _backend_mode = "sqlite"
        return _backend_mode
    _backend_mode = "redis"
    return _backend_mode


def backend_mode() -> str:
    """返回本进程已选定的后端：\"redis\" 或 \"sqlite\"。"""
    if _backend_mode is None:
        return select_backend()
    return _backend_mode


def get_client() -> Optional[Any]:
    """共享连接。后端已定为 sqlite 时返回 None，且不会再次连接。"""
    if _backend_mode is None:
        select_backend()
    if _backend_mode != "redis":
        return None
    return _client
