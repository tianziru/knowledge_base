# tests/test_task_utils_redis.py
import os
import tempfile
import time

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


def _switch_process(redis_mode):
    """同一 FakeServer 上的新 client，只清本进程内存。"""
    server = redis_mode.connection_pool.connection_kwargs.get("server") or redis_mode.server
    client_b = fakeredis.FakeStrictRedis(server=server, decode_responses=True)
    redis_client.set_client_for_tests(client_b)
    task_utils.reset_redis_persistence_for_tests(client_b)
    return client_b


def test_cold_cache_write_keeps_redis_fields(redis_mode):
    """进程 B 未读就写，不得用空内存覆盖 Redis 里已有字段。"""
    from app.utils import task_store_redis as rs

    task_utils.register_task_meta("t-cold", file_name="keep.pdf", file_size=9)
    task_utils.add_done_task("t-cold", "upload_file")
    task_utils.add_running_task("t-cold", "node_entry")
    task_utils.update_task_status("t-cold", task_utils.TASK_STATUS_PROCESSING)
    task_utils.set_task_result("t-cold", "error", "partial")
    created = task_utils.get_task_meta("t-cold")["created_at"]
    assert created

    client_b = _switch_process(redis_mode)
    task_utils.add_running_task("t-cold", "node_pdf_to_md")

    rec = rs.get_task(client_b, "t-cold")
    assert rec["file_name"] == "keep.pdf"
    assert rec["created_at"] == created
    assert rec["done_list"] == ["upload_file"]
    assert rec["running_list"] == ["node_entry", "node_pdf_to_md"]
    assert rec["error"] == "partial"
    assert rec["file_size"] == 9


def test_missing_redis_record_drops_stale_local(redis_mode):
    from app.utils import task_store_redis as rs

    task_utils.register_task_meta("gone", file_name="z.pdf", file_size=1)
    task_utils.update_task_status("gone", task_utils.TASK_STATUS_COMPLETED)
    task_utils.add_done_task("gone", "upload_file")
    task_utils.set_task_result("gone", "error", "boom")
    rs.delete_task(redis_mode, "gone")

    assert task_utils.get_task_status("gone") == ""
    assert task_utils.get_task_meta("gone") == {}
    assert task_utils.get_done_task_list("gone") == []
    assert task_utils.get_running_task_list("gone") == []
    assert task_utils.get_task_result("gone", "error", "") == ""


def test_lease_check_error_does_not_reap(redis_mode, monkeypatch):
    from app.utils import task_store_redis as rs

    task_utils.register_task_meta("t-lease", file_name="e.pdf", file_size=1)
    task_utils.update_task_status("t-lease", task_utils.TASK_STATUS_PROCESSING)
    task_utils.add_running_task("t-lease", "node_entry")

    def boom(*_args, **_kwargs):
        raise RuntimeError("lease backend down")

    monkeypatch.setattr(redis_mode, "exists", boom)
    assert task_utils.get_task_status("t-lease") == task_utils.TASK_STATUS_PROCESSING
    rec = rs.get_task(redis_mode, "t-lease")
    assert rec["status"] == task_utils.TASK_STATUS_PROCESSING
    assert rec["running_list"] == ["node_entry"]
    assert "租约" not in (rec["error"] or "")


def test_periodic_lease_renew_without_writes(redis_mode, monkeypatch):
    """无进度写穿时，持有方仍应按 TTL/3 续期，睡过 TTL 后状态还是 processing。"""
    from app.utils import task_store_redis as rs

    monkeypatch.setenv("TASK_LEASE_TTL_SEC", "1")
    task_utils.register_task_meta("t-renew", file_name="r.pdf", file_size=1)
    task_utils.update_task_status("t-renew", task_utils.TASK_STATUS_PROCESSING)
    assert "t-renew" in task_utils._owned_inflight
    time.sleep(1.5)
    assert rs.has_lease(redis_mode, "t-renew") is True
    assert task_utils.get_task_status("t-renew") == task_utils.TASK_STATUS_PROCESSING


def test_hydrated_task_is_not_renewed(redis_mode, monkeypatch):
    """新 worker 只读到他机任务时不续租，睡过 TTL 后应被标失败。"""
    monkeypatch.setenv("TASK_LEASE_TTL_SEC", "1")
    task_utils.register_task_meta("t-other", file_name="o.pdf", file_size=1)
    task_utils.update_task_status("t-other", task_utils.TASK_STATUS_PROCESSING)
    task_utils.reset_redis_persistence_for_tests(redis_mode)
    assert "t-other" not in task_utils._owned_inflight
    time.sleep(1.5)
    assert task_utils.get_task_status("t-other") == task_utils.TASK_STATUS_FAILED


def test_redis_get_error_keeps_local_buffer(redis_mode, monkeypatch):
    task_utils.register_task_meta("t-err", file_name="e.pdf", file_size=4)
    task_utils.update_task_status("t-err", task_utils.TASK_STATUS_PROCESSING)
    task_utils.add_running_task("t-err", "node_entry")

    def boom(*_args, **_kwargs):
        raise RuntimeError("hgetall down")

    monkeypatch.setattr(redis_mode, "hgetall", boom)
    assert task_utils.task_exists("t-err") is True
    assert task_utils.get_task_status("t-err") == task_utils.TASK_STATUS_PROCESSING
    assert task_utils.get_task_meta("t-err").get("file_name") == "e.pdf"
    assert task_utils.get_running_task_list("t-err") == ["检查文件"]
