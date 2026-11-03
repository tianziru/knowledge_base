import os
import tempfile
import threading

# 模块导入即 bootstrap。必须先把库指到一次性文件，收集阶段才不会写 data/tasks.db。
_fd, _COLLECT_DB = tempfile.mkstemp(prefix="task-utils-collect-", suffix=".db")
os.close(_fd)
os.environ["TASK_STORE_PATH"] = _COLLECT_DB

import pytest

from app.utils import task_utils


@pytest.fixture
def fresh_store(tmp_path):
    path = str(tmp_path / "tasks.db")
    os.environ["TASK_STORE_PATH"] = path
    task_utils.reset_persistence_for_tests(path)
    yield path
    # 连接留在本次 tmp 库；环境变量回到收集阶段的一次性文件，避免回落到 data/tasks.db。
    os.environ["TASK_STORE_PATH"] = _COLLECT_DB


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


def test_concurrent_node_updates_survive_reload(fresh_store):
    task_utils.register_task_meta("t-conc", file_name="d.pdf", file_size=1)
    n = 40
    barrier = threading.Barrier(2)
    errors = []

    def add_running():
        try:
            barrier.wait(timeout=5)
            for i in range(n):
                task_utils.add_running_task("t-conc", f"run-{i}")
        except Exception as exc:
            errors.append(exc)

    def add_done():
        try:
            barrier.wait(timeout=5)
            for i in range(n):
                task_utils.add_done_task("t-conc", f"done-{i}")
        except Exception as exc:
            errors.append(exc)

    threads = [
        threading.Thread(target=add_running),
        threading.Thread(target=add_done),
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=30)

    assert errors == []
    assert not any(thread.is_alive() for thread in threads)

    task_utils.reset_persistence_for_tests(fresh_store)
    assert set(task_utils.get_running_task_list("t-conc")) == {f"run-{i}" for i in range(n)}
    assert set(task_utils.get_done_task_list("t-conc")) == {f"done-{i}" for i in range(n)}
    assert task_utils.get_task_meta("t-conc").get("updated_at")
