import asyncio
import json
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
    sse_utils.remove_sse_queue("s1")
    sse_utils.remove_sse_queue("s2")
    sse_utils.remove_sse_queue("s3")
    sse_utils.remove_sse_queue("local1")


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


def test_redis_push_ignores_missing_and_present_local_queue(shared_redis):
    """Redis 模式下即使没有本地 queue 也 PUBLISH；有本地 queue 也不往 queue 里放。"""
    _a, b = shared_redis
    channel = sse_utils.sse_channel("s3")
    pubsub = b.pubsub(ignore_subscribe_messages=True)
    pubsub.subscribe(channel)
    time.sleep(0.05)

    sse_utils.push_to_session("s3", "progress", {"status": "no-queue"})

    q = sse_utils.create_sse_queue("s3")
    sse_utils.push_to_session("s3", "delta", {"delta": "queued?"})
    assert q.empty()

    events = []
    deadline = time.time() + 2
    while time.time() < deadline and len(events) < 2:
        msg = pubsub.get_message(timeout=0.2)
        if msg and msg.get("type") == "message":
            events.append(json.loads(msg["data"]))
    assert [e["event"] for e in events] == ["progress", "delta"]
    pubsub.unsubscribe(channel)
    pubsub.close()


def test_generator_subscribes_without_local_queue(shared_redis):
    class _Req:
        async def is_disconnected(self):
            return False

    async def _run():
        gen = sse_utils.sse_generator("s2", _Req())
        first = await asyncio.wait_for(gen.__anext__(), timeout=2)
        assert "event: ready" in first
        sse_utils.push_to_session("s2", "progress", {"status": "processing"})
        second = await asyncio.wait_for(gen.__anext__(), timeout=2)
        assert "event: progress" in second
        assert "processing" in second
        await gen.aclose()

    asyncio.run(_run())


def test_local_queue_when_client_is_none():
    redis_client.reset_client_for_tests()
    assert redis_client.get_client() is None
    q = sse_utils.create_sse_queue("local1")
    sse_utils.push_to_session("local1", "progress", {"status": "local"})
    assert q.get_nowait() == {"event": "progress", "data": {"status": "local"}}
    sse_utils.remove_sse_queue("local1")
