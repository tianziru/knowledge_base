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


def test_lookup_distinguishes_missing_and_error(r, monkeypatch):
    assert store.lookup_task(r, "missing") == ("missing", None)
    store.upsert_task(r, _rec("t1"))
    kind, rec = store.lookup_task(r, "t1")
    assert kind == "found"
    assert rec["status"] == "processing"
    store.set_lease(r, "t1", "w1", ttl=30)
    assert store.extend_lease_if_present(r, "t1", ttl=30) is True
    store.clear_lease(r, "t1")
    assert store.extend_lease_if_present(r, "t1", ttl=30) is False
    assert store.has_lease(r, "t1") is False

    def boom(*_args, **_kwargs):
        raise RuntimeError("down")

    monkeypatch.setattr(r, "hgetall", boom)
    assert store.lookup_task(r, "t1")[0] == "error"
    with pytest.raises(RuntimeError):
        store.get_task(r, "t1")


def test_lease_ttl_and_clear(r):
    store.set_lease(r, "t1", "w1", ttl=1)
    assert store.has_lease(r, "t1") is True
    time.sleep(1.1)
    assert store.has_lease(r, "t1") is False
    store.set_lease(r, "t1", "w1", ttl=30)
    store.clear_lease(r, "t1")
    assert store.has_lease(r, "t1") is False
