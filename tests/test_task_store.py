import os

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


def _reset_conn() -> None:
    conn = task_store._conn
    task_store._conn = None
    if conn is not None:
        conn.close()


def test_upsert_when_conn_is_none(tmp_path):
    path = str(tmp_path / "tasks.db")
    os.environ["TASK_STORE_PATH"] = path
    _reset_conn()
    assert task_store._conn is None
    try:
        task_store.upsert_task({
            "task_id": "cold",
            "status": "running",
            "file_name": "b.pdf",
            "file_size": 3,
            "created_at": "2026-10-28T11:00:00",
            "updated_at": "2026-10-28T11:00:01",
            "done_list": [],
            "running_list": ["upload_file"],
            "error": "",
        })
        rows = task_store.load_all()
        assert len(rows) == 1
        assert rows[0]["task_id"] == "cold"
        assert rows[0]["running_list"] == ["upload_file"]
    finally:
        os.environ.pop("TASK_STORE_PATH", None)
