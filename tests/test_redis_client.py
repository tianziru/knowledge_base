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
    assert redis_client.backend_mode() == "redis"
    assert redis_client.ping_client(fake) is True


def test_connect_failure_freezes_sqlite_for_task_and_sse(monkeypatch, tmp_path):
    """REDIS_REQUIRED=0 时连接失败只探测一次，任务与 SSE 都固定走 sqlite。"""
    from app.utils import sse_utils

    monkeypatch.setenv("TASK_STORE_PATH", str(tmp_path / "tasks.db"))
    monkeypatch.setenv("REDIS_URL", "redis://127.0.0.1:6391/0")
    monkeypatch.setenv("REDIS_REQUIRED", "0")
    redis_client.reset_client_for_tests()
    calls = {"n": 0}

    def boom(_url):
        calls["n"] += 1
        raise ConnectionError("down")

    monkeypatch.setattr(redis_client, "_connect", boom)
    assert redis_client.select_backend() == "sqlite"
    assert redis_client.backend_mode() == "sqlite"
    assert redis_client.get_client() is None
    assert redis_client.select_backend() == "sqlite"
    assert calls["n"] == 1

    from app.utils import task_utils

    assert task_utils._use_redis() is False
    assert sse_utils._redis_enabled() is False
    q = sse_utils.create_sse_queue("sticky-local")
    sse_utils.push_to_session("sticky-local", "progress", {"status": "local"})
    assert q.get_nowait() == {"event": "progress", "data": {"status": "local"}}
    sse_utils.remove_sse_queue("sticky-local")
