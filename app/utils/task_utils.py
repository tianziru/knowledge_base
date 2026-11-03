import logging
import threading
import uuid
from typing import Dict, List, Any, Optional
from datetime import datetime
from .sse_utils import push_to_session
from . import redis_client
from . import task_store
from . import task_store_redis

logger = logging.getLogger(__name__)

# ---------------------------
# 内存态任务追踪（单进程）
# ---------------------------
# key: task_id
# value: 节点名列表（原始英文/节点ID）
_tasks_running_list: Dict[str, List[str]] = {}
_tasks_done_list: Dict[str, List[str]] = {}

# key: task_id
# value: status 字符串（如 pending/processing/completed/failed）
_tasks_status: Dict[str, str] = {}

# key: task_id
# value: 任务结果（例如 query 的 answer）
_tasks_result: Dict[str, Dict[str, str]] = {}

# key: task_id
# value: 任务元信息（文件名、大小、创建时间等）
_tasks_meta: Dict[str, Dict[str, Any]] = {}

# 内存变更与整行写穿共用。持锁后再进入 task_store 的 RLock（先本锁，后 store 锁）。
_state_lock = threading.RLock()

_backend: str = "sqlite"  # "sqlite" | "redis"，与 redis_client.backend_mode() 同步
_worker_id: str = str(uuid.uuid4())
# 本进程经 update_task_status 进入 pending/processing 的任务。只从 Redis 灌入的不算。
_owned_inflight: set[str] = set()
_renew_stop = threading.Event()
_renew_thread: Optional[threading.Thread] = None
_RENEW_POLL_SEC = 0.2
_LEASE_EXPIRE_MSG = "任务租约过期（worker 可能已退出）"

TASK_STATUS_PENDING = "pending"
TASK_STATUS_PROCESSING = "processing"
TASK_STATUS_COMPLETED = "completed"
TASK_STATUS_FAILED = "failed"

# 节点名 -> 中文名映射（用于前端展示）
# 说明：这里的 key 应与 LangGraph 的 add_node("xxx", ...) 中的节点名一致。
_NODE_NAME_TO_CN: Dict[str, str] = {
    "upload_file": "开始上传文件",
    "node_entry": "检查文件",
    "office_to_md": "办公文档转Markdown",
    "node_pdf_to_md": "PDF转Markdown",
    "node_md_img": "Markdown图片处理",
    "node_item_name_recognition": "商品名称识别",
    "node_document_split": "文档切分",
    "node_bge_embedding": "向量生成",
    "node_import_kg": "导入知识图谱",
    "node_import_milvus": "导入向量库",
    "__end__": "处理完成",
    "END": "处理完成",
    # --- Query 流程节点（kb/query_process/main_graph.py）---
    "node_item_name_confirm": "确认查询商品",
    "node_answer_output": "生成答案",
    "node_rerank": "重排序",
    "node_rrf": "倒排融合",
    "node_web_search_mcp": "网络搜索",
    "node_search_embedding": "切片搜索",
    "node_search_embedding_hyde": "切片搜索(假设性文档)",
    "node_multi_search": "多路搜索",
    "node_query_kg": "查询知识图谱",
    "node_join": "多路搜索合并",
}


def _snapshot_task(task_id: str) -> Dict[str, Any]:
    """调用方须已持有 _state_lock。每次写穿刷新 updated_at 并写回内存 meta。"""
    meta = _tasks_meta.get(task_id)
    if meta is None:
        meta = {}
        _tasks_meta[task_id] = meta
    updated_at = datetime.now().isoformat(timespec="seconds")
    meta["updated_at"] = updated_at
    return {
        "task_id": task_id,
        "status": _tasks_status.get(task_id, ""),
        "file_name": meta.get("file_name", ""),
        "file_size": int(meta.get("file_size") or 0),
        "created_at": meta.get("created_at", ""),
        "updated_at": updated_at,
        "done_list": list(_tasks_done_list.get(task_id, [])),
        "running_list": list(_tasks_running_list.get(task_id, [])),
        "error": _tasks_result.get(task_id, {}).get("error", ""),
    }


def _use_redis() -> bool:
    return redis_client.backend_mode() == "redis"


def _note_owned_task(task_id: str) -> None:
    """调用方已持 _state_lock。只记录本进程写入的 pending/processing。"""
    status = _tasks_status.get(task_id, "")
    if status in (TASK_STATUS_PENDING, TASK_STATUS_PROCESSING):
        _owned_inflight.add(task_id)
    else:
        _owned_inflight.discard(task_id)


def _renew_owned_leases_once() -> None:
    """给本进程仍在进行中的任务续期。不续只灌入的任务，也不复活已消失的租约。"""
    if redis_client.backend_mode() != "redis":
        return
    client = redis_client.get_client()
    if client is None:
        return
    with _state_lock:
        stale = [
            tid
            for tid in _owned_inflight
            if _tasks_status.get(tid) not in (TASK_STATUS_PENDING, TASK_STATUS_PROCESSING)
        ]
        for tid in stale:
            _owned_inflight.discard(tid)
        ids = list(_owned_inflight)
    for tid in ids:
        kind, rec = task_store_redis.lookup_task(client, tid)
        if kind == "error":
            continue
        if kind != "found" or not rec or rec.get("status") not in (
            TASK_STATUS_PENDING,
            TASK_STATUS_PROCESSING,
        ):
            with _state_lock:
                _owned_inflight.discard(tid)
            continue
        with _state_lock:
            if tid not in _owned_inflight:
                continue
            if _tasks_status.get(tid) not in (TASK_STATUS_PENDING, TASK_STATUS_PROCESSING):
                _owned_inflight.discard(tid)
                continue
        task_store_redis.extend_lease_if_present(client, tid)


def _lease_renew_interval() -> float:
    return max(_RENEW_POLL_SEC, redis_client.get_lease_ttl_sec() / 3.0)


def _lease_renew_loop() -> None:
    while not _renew_stop.is_set():
        interval = _lease_renew_interval()
        remaining = interval
        while remaining > 0:
            step = min(_RENEW_POLL_SEC, remaining)
            if _renew_stop.wait(step):
                return
            remaining -= step
            # TTL 变短时立刻按新间隔续期，避免测试或配置把 TTL 降到 1s 后仍睡满旧间隔。
            if _lease_renew_interval() + 1e-6 < interval:
                break
        try:
            _renew_owned_leases_once()
        except Exception:
            logger.exception("periodic lease renew failed")


def _ensure_lease_renew_thread() -> None:
    global _renew_thread
    if _renew_thread is not None and _renew_thread.is_alive():
        return
    _renew_thread = threading.Thread(
        target=_lease_renew_loop,
        name="task-lease-renew",
        daemon=True,
    )
    _renew_thread.start()


def _persist_task_redis(task_id: str) -> None:
    """调用方须已持有 _state_lock。本地 dict 只作写缓冲，权威状态在 Redis。"""
    client = redis_client.get_client()
    if client is None:
        return
    snap = _snapshot_task(task_id)
    snap["owner"] = _worker_id
    task_store_redis.upsert_task(client, snap)
    status = _tasks_status.get(task_id, "")
    if status in (TASK_STATUS_PENDING, TASK_STATUS_PROCESSING):
        task_store_redis.renew_lease(client, task_id, _worker_id)
    else:
        task_store_redis.clear_lease(client, task_id)


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


def _drop_task_memory(task_id: str) -> None:
    """调用方须已持有 _state_lock。只清本进程，不删 Redis。"""
    _tasks_running_list.pop(task_id, None)
    _tasks_done_list.pop(task_id, None)
    _tasks_status.pop(task_id, None)
    _tasks_result.pop(task_id, None)
    _tasks_meta.pop(task_id, None)
    _owned_inflight.discard(task_id)


def _hydrate_task_from_redis(task_id: str, *, drop_if_missing: bool = False) -> None:
    """把 Redis 行灌进本进程。

    只有 lookup 确认 key 不存在时才清本地缓冲。Redis 异常保留本地缓冲，
    避免 /status 被看成未注册。写路径不 drop，防止把半行写回去。
    """
    if not _use_redis() or not task_id:
        return
    client = redis_client.get_client()
    if client is None:
        return
    kind, rec = task_store_redis.lookup_task(client, task_id)
    if kind == "error":
        return
    if kind != "found" or not rec:
        if drop_if_missing:
            with _state_lock:
                _drop_task_memory(task_id)
        return
    with _state_lock:
        _load_record_into_memory(rec)


def _hydrate_before_redis_write(task_id: str) -> None:
    """写穿前合并 Redis 已有行，避免冷缓存用空 dict 覆盖整行。"""
    _hydrate_task_from_redis(task_id, drop_if_missing=False)


def _reap_if_lease_expired(task_id: str) -> None:
    if not _use_redis() or not task_id:
        return
    client = redis_client.get_client()
    if client is None:
        return
    kind, rec = task_store_redis.lookup_task(client, task_id)
    if kind != "found" or not rec:
        return
    if rec.get("status") not in (TASK_STATUS_PENDING, TASK_STATUS_PROCESSING):
        return
    try:
        leased = task_store_redis.has_lease(client, task_id)
    except Exception:
        # has_lease 已记录异常。无法判断时跳过回收，不能当成租约过期。
        return
    if leased:
        return
    rec["status"] = TASK_STATUS_FAILED
    rec["running_list"] = []
    rec["error"] = _LEASE_EXPIRE_MSG
    task_store_redis.upsert_task(client, rec)
    task_store_redis.clear_lease(client, task_id)
    with _state_lock:
        _load_record_into_memory(rec)
        _owned_inflight.discard(task_id)


def _prepare_redis_read(task_id: str) -> None:
    if not _use_redis():
        return
    _hydrate_task_from_redis(task_id, drop_if_missing=True)
    _reap_if_lease_expired(task_id)


def _clear_memory() -> None:
    _tasks_running_list.clear()
    _tasks_done_list.clear()
    _tasks_status.clear()
    _tasks_result.clear()
    _tasks_meta.clear()
    _owned_inflight.clear()


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
    else:
        _tasks_result[tid].pop("error", None)


def _mark_interrupted_tasks() -> None:
    with _state_lock:
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
    global _backend
    redis_client.set_backend_mode_for_tests("sqlite")
    with _state_lock:
        _backend = "sqlite"
        _clear_memory()
        task_store.init_db(db_path)
        for rec in task_store.load_all():
            _load_record_into_memory(rec)
        _mark_interrupted_tasks()


def reset_redis_persistence_for_tests(client) -> None:
    """测试专用：注入 Redis client，切到 redis 后端并清空本进程内存。

    不删除 Redis 里已有任务与租约，也不批量把 pending/processing 标为 failed。
    """
    global _backend, _worker_id
    redis_client.set_client_for_tests(client)
    with _state_lock:
        _backend = "redis"
        _worker_id = str(uuid.uuid4())
        _clear_memory()


def _ensure_task(task_id: str) -> None:
    """确保 task_id 对应的数据结构已初始化。"""
    if task_id not in _tasks_running_list:
        _tasks_running_list[task_id] = []
    if task_id not in _tasks_done_list:
        _tasks_done_list[task_id] = []
    if task_id not in _tasks_result:
        _tasks_result[task_id] = {}
    if task_id not in _tasks_meta:
        _tasks_meta[task_id] = {}


def register_task_meta(
    task_id: str,
    file_name: str = "",
    file_size: int = 0,
    extra: Optional[Dict[str, Any]] = None,
) -> None:
    """注册/更新任务元信息，供任务列表与刷新恢复使用。"""
    with _state_lock:
        _hydrate_before_redis_write(task_id)
        _ensure_task(task_id)
        meta = _tasks_meta[task_id]
        if "created_at" not in meta:
            meta["created_at"] = datetime.now().isoformat(timespec="seconds")
        meta["file_name"] = file_name or meta.get("file_name", "")
        meta["file_size"] = file_size or meta.get("file_size", 0)
        meta["updated_at"] = datetime.now().isoformat(timespec="seconds")
        if extra:
            meta.update(extra)
        _persist_task(task_id)


def get_task_meta(task_id: str) -> Dict[str, Any]:
    _prepare_redis_read(task_id)
    if not _use_redis():
        _ensure_task(task_id)
    return dict(_tasks_meta.get(task_id, {}))


def _summary_from_record(rec: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "task_id": rec.get("task_id", ""),
        "file_name": rec.get("file_name", ""),
        "file_size": rec.get("file_size", 0),
        "created_at": rec.get("created_at", ""),
        "updated_at": rec.get("updated_at", ""),
        "status": rec.get("status") or TASK_STATUS_PENDING,
        "done_list": [_to_cn(n) for n in (rec.get("done_list") or [])],
        "running_list": [_to_cn(n) for n in (rec.get("running_list") or [])],
        "error": rec.get("error") or "",
    }


def _list_tasks_from_redis() -> List[Dict[str, Any]]:
    """全集来自 Redis 索引，不用本进程内存 key 的并集。"""
    client = redis_client.get_client()
    if client is None:
        return []
    items: List[Dict[str, Any]] = []
    for rec in task_store_redis.list_tasks(client):
        tid = rec.get("task_id") or ""
        if not tid:
            continue
        _reap_if_lease_expired(tid)
        kind, fresh = task_store_redis.lookup_task(client, tid)
        if kind != "found" or not fresh:
            fresh = rec
        with _state_lock:
            _load_record_into_memory(fresh)
        items.append(_summary_from_record(fresh))
    items.sort(key=lambda x: x.get("created_at") or "", reverse=True)
    return items


def list_tasks() -> List[Dict[str, Any]]:
    """返回全部任务摘要（新任务在前）。"""
    if _use_redis():
        return _list_tasks_from_redis()
    task_ids = set(_tasks_status.keys()) | set(_tasks_meta.keys()) | set(_tasks_done_list.keys()) | set(_tasks_running_list.keys())
    items: List[Dict[str, Any]] = []
    for task_id in task_ids:
        meta = get_task_meta(task_id)
        items.append({
            "task_id": task_id,
            "file_name": meta.get("file_name", ""),
            "file_size": meta.get("file_size", 0),
            "created_at": meta.get("created_at", ""),
            "updated_at": meta.get("updated_at", ""),
            "status": get_task_status(task_id) or TASK_STATUS_PENDING,
            "done_list": get_done_task_list(task_id),
            "running_list": get_running_task_list(task_id),
            "error": get_task_result(task_id, "error", ""),
        })
    items.sort(key=lambda x: x.get("created_at") or "", reverse=True)
    return items


def get_task_stats() -> Dict[str, Any]:
    """聚合任务统计，供后台概览使用。"""
    tasks = list_tasks()
    today = datetime.now().strftime("%Y-%m-%d")
    by_status: Dict[str, int] = {
        TASK_STATUS_PENDING: 0,
        TASK_STATUS_PROCESSING: 0,
        TASK_STATUS_COMPLETED: 0,
        TASK_STATUS_FAILED: 0,
    }
    today_count = 0
    for t in tasks:
        status = t.get("status") or TASK_STATUS_PENDING
        by_status[status] = by_status.get(status, 0) + 1
        created = str(t.get("created_at") or "")
        if created.startswith(today):
            today_count += 1
    return {
        "total": len(tasks),
        "today": today_count,
        "by_status": by_status,
        "recent": tasks[:8],
    }


def _to_cn(node_name: str) -> str:
    """将节点名转换为中文展示名；若无映射则返回原名。"""
    return _NODE_NAME_TO_CN.get(node_name, node_name)


def add_running_task(task_id: str, node_name: str, is_stream: bool = False) -> None:
    """
    添加“正在运行”的节点任务。

    参数：
    - task_id: 任务ID
    - node_name: 节点名称(节点ID)
    """
    with _state_lock:
        _hydrate_before_redis_write(task_id)
        _ensure_task(task_id)
        running = _tasks_running_list[task_id]
        # 避免重复追加
        if node_name not in running:
            running.append(node_name)
        _persist_task(task_id)
    if is_stream:
        task_push_queue(task_id)


def add_done_task(task_id: str, node_name: str, is_stream: bool = False) -> None:
    """
    添加“已完成”的节点任务。

    注意：添加已完成任务时，会把同名的“正在运行”任务删除。

    参数：
    - task_id: 任务ID
    - node_name: 节点名称(节点ID)
    """
    with _state_lock:
        _hydrate_before_redis_write(task_id)
        _ensure_task(task_id)

        # 1) 从 running 中移除同名节点（可能出现重复，移除所有）
        running = _tasks_running_list[task_id]
        _tasks_running_list[task_id] = [n for n in running if n != node_name]

        # 2) 追加到 done（保持完成顺序），避免重复
        done = _tasks_done_list[task_id]
        if node_name not in done:
            done.append(node_name)

        _persist_task(task_id)
    if is_stream:
        task_push_queue(task_id)


def set_task_result(task_id: str, key: str, value: str) -> None:
    """
    存储任务结果字段（如 answer / error）。
    """
    with _state_lock:
        _hydrate_before_redis_write(task_id)
        _ensure_task(task_id)
        _tasks_result[task_id][key] = value
        if key == "error":
            _persist_task(task_id)


def get_task_result(task_id: str, key: str, default: str = "") -> str:
    """
    获取任务结果字段（如 answer / error）。
    """
    _prepare_redis_read(task_id)
    if not _use_redis():
        _ensure_task(task_id)
    return _tasks_result.get(task_id, {}).get(key, default)


def get_task_status(task_id: str) -> str:
    """
    获取当前任务状态。

    参数：
    - task_id: 任务ID

    返回：
    - str: 状态名称；如果未设置过则返回空字符串
    """
    _prepare_redis_read(task_id)
    return _tasks_status.get(task_id, "")


def _local_task_known(task_id: str) -> bool:
    return (
        task_id in _tasks_status
        or task_id in _tasks_meta
        or task_id in _tasks_done_list
        or task_id in _tasks_running_list
        or task_id in _tasks_result
    )


def task_exists(task_id: str) -> bool:
    """判断任务是否已注册（避免前端轮询旧 task_id 时创建幽灵任务）。"""
    if _use_redis():
        client = redis_client.get_client()
        if client is None:
            return _local_task_known(task_id)
        kind, rec = task_store_redis.lookup_task(client, task_id)
        if kind == "error":
            return _local_task_known(task_id)
        return rec is not None
    return _local_task_known(task_id)


def get_done_task_list(task_id: str) -> List[str]:
    """
    获取已完成节点列表（中文展示）。
    """
    _prepare_redis_read(task_id)
    done = _tasks_done_list.get(task_id, [])
    return [_to_cn(n) for n in done]


def get_running_task_list(task_id: str) -> List[str]:
    """
    获取正在运行节点列表（中文展示）。
    """
    _prepare_redis_read(task_id)
    running = _tasks_running_list.get(task_id, [])
    return [_to_cn(n) for n in running]


def update_task_status(task_id: str, status_name: str, push_queue: bool = False) -> None:
    """
    更新任务状态。

    参数：
    - task_id: 任务ID
    - status_name: 状态名称（字符串）
    """
    with _state_lock:
        _hydrate_before_redis_write(task_id)
        _tasks_status[task_id] = status_name
        _note_owned_task(task_id)
        _persist_task(task_id)
    if push_queue:
        task_push_queue(task_id)


def task_push_queue(task_id: str):
    push_to_session(task_id, "progress", {
        "status": get_task_status(task_id),
        "done_list": get_done_task_list(task_id),
        "running_list": get_running_task_list(task_id),
    })


#
def clear_task(task_id: str):
    with _state_lock:
        _drop_task_memory(task_id)
        if _use_redis():
            client = redis_client.get_client()
            if client is not None:
                task_store_redis.delete_task(client, task_id)
        else:
            task_store.delete_task(task_id)


def _select_backend_on_import() -> None:
    global _backend
    _backend = redis_client.select_backend()
    if _backend != "redis":
        _bootstrap_from_store()


_select_backend_on_import()
_ensure_lease_renew_thread()