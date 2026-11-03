import json
import queue
import asyncio
import logging
from typing import Dict, Any, Optional, AsyncGenerator
from fastapi import Request

from app.utils import redis_client

logger = logging.getLogger(__name__)


class SSEEvent:
    READY = "ready"         # 连接建立
    PROGRESS = "progress"   # 任务节点进度
    DELTA = "delta"         # LLM 流式输出增量
    FINAL = "final"         # 最终完整答案
    ERROR = "error"         # 错误信息
    CLOSE = "__close__"     # 关闭连接信号


# 全局 SSE 会话队列存储
# Key: session_id, Value: queue.Queue
_session_stream: Dict[str, queue.Queue] = {}

def get_sse_queue(session_id: str) -> Optional["queue.Queue"]:
    """获取指定 session 的队列"""
    return _session_stream.get(session_id)

def create_sse_queue(session_id: str) -> "queue.Queue":
    """创建并注册一个新的 SSE 队列"""
    print(f"[SSE] Creating queue for session: {session_id}")
    q = queue.Queue()
    _session_stream[session_id] = q
    return q

def remove_sse_queue(session_id: str):
    """移除指定 session 的队列"""
    print(f"[SSE] Removing queue for session: {session_id}")
    _session_stream.pop(session_id, None)

def _sse_pack(event: str, data: Dict[str, Any]) -> str:
    """打包 SSE 消息格式"""
    payload = json.dumps(data, ensure_ascii=False)
    # print(f"[SSE] Packing event: {event}, payload: {payload[:50]}...")
    return f"event: {event}\ndata: {payload}\n\n"

def sse_channel(session_id: str) -> str:
    return f"{redis_client.get_key_prefix()}:sse:{session_id}"


def _redis_enabled() -> bool:
    """与 task_utils 共用 redis_client 的一次性后端选择，不再单独探测 Redis。"""
    return redis_client.backend_mode() == "redis"


def push_to_session(session_id: str, event: str, data: Dict[str, Any]):
    """
    通过 session_id 推送事件。Redis 可用时 PUBLISH，否则写入本进程队列。
    """
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
        # print(f"[SSE] Pushing to session {session_id}: {event}")
        stream_queue.put({"event": event, "data": data})
    else:
        print(f"[SSE] Warning: No queue found for session {session_id} when pushing {event}")

async def _sse_generator_redis(session_id: str, request: Request):
    """Redis Pub/Sub 订阅循环。不依赖本进程队列。"""
    print(f"[SSE] Generator started (redis) for session: {session_id}")
    client = redis_client.get_client()
    pubsub = client.pubsub(ignore_subscribe_messages=True)
    channel = sse_channel(session_id)
    pubsub.subscribe(channel)
    loop = asyncio.get_running_loop()
    try:
        yield _sse_pack("ready", {})
        while True:
            if await request.is_disconnected():
                print(f"[SSE] Client disconnected: {session_id}")
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
    except (asyncio.CancelledError, ConnectionResetError, BrokenPipeError):
        print(f"[SSE] Client disconnected (Cancelled/Reset/Pipe): {session_id}")
        return
    except Exception as e:
        print(f"[SSE] Exception in generator for {session_id}: {e}")
    finally:
        print(f"[SSE] Generator finished (redis) for {session_id}")
        try:
            pubsub.unsubscribe(channel)
            pubsub.close()
        except Exception:
            logger.exception("sse redis unsubscribe failed session_id=%s", session_id)
        remove_sse_queue(session_id)

async def sse_generator(session_id: str, request: Request):
    """
    SSE 生成器，用于 FastAPI 的 StreamingResponse
    """
    if _redis_enabled():
        async for chunk in _sse_generator_redis(session_id, request):
            yield chunk
        return

    print(f"[SSE] Generator started for session: {session_id}")
    stream_queue = get_sse_queue(session_id)
    if stream_queue is None:
        # 如果没有对应的队列，直接结束
        print(f"[SSE] Error: Queue not found for session {session_id}. Available sessions: {list(_session_stream.keys())}")
        return

    loop = asyncio.get_running_loop()
    try:
        # 发送连接建立信号
        print(f"[SSE] Sending ready signal for {session_id}")
        yield _sse_pack("ready", {})

        while True:
            # 若客户端断开，尽快退出
            if await request.is_disconnected():
                print(f"[SSE] Client disconnected: {session_id}")
                print("-----------------------断开连接--------------------")
                break

            try:
                # 使用 run_in_executor 避免阻塞 async 事件循环
                msg = await loop.run_in_executor(None, stream_queue.get, True, 1.0)
            except queue.Empty:
                # print(f"[SSE] Queue empty for {session_id}, waiting...")
                continue

            event = msg.get("event")
            data = msg.get("data")
            
            # print(f"[SSE] Yielding event {event} for {session_id}")

            # 特殊关闭事件
            if event == "__close__":
                print(f"[SSE] Closing signal received for {session_id}")
                break

            yield _sse_pack(event, data)
    except (asyncio.CancelledError, ConnectionResetError, BrokenPipeError):
        print(f"[SSE] Client disconnected (Cancelled/Reset/Pipe): {session_id}")
        # 生成器被取消/对端断开：静默退出
        return
    except Exception as e:
        print(f"[SSE] Exception in generator for {session_id}: {e}")
    finally:
        print(f"[SSE] Generator finished for {session_id}")
        # 清理资源
        remove_sse_queue(session_id)