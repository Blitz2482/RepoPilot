from __future__ import annotations

import asyncio
import time
from urllib.parse import urlparse

from fastapi import WebSocket, WebSocketDisconnect

from config import settings
from job_store import _get_redis, _redis_channel, get_job_or_restore, snapshot, subscribe, unsubscribe, redis_check


async def _redis_wait_for_message(pubsub, timeout: float = 30.0):
    """Wait for one Redis pub/sub message without confusing an idle timeout with an outage.

    redis-py returns None when get_message() simply has no message during its
    polling window. That is a normal idle state and must not force a fallback
    to the process-local queue.
    """
    deadline = time.monotonic() + timeout
    try:
        while time.monotonic() < deadline:
            message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
            if message and message.get("type") == "message":
                return {"kind": "message", "data": message.get("data")}
        return {"kind": "heartbeat", "data": None}
    except Exception:
        # The caller switches back to the in-process queue. The client can also
        # reconnect later, so a transient Redis outage does not crash the socket.
        return {"kind": "outage", "data": None}


def _origin_allowed(origin: str | None) -> bool:
    if not origin:
        return True
    try:
        parsed = urlparse(origin)
        normalized = f"{parsed.scheme}://{parsed.netloc}"
    except Exception:
        return False
    return normalized in settings.allowed_origins


async def stream_job(ws: WebSocket, job_id: str) -> None:
    origin = ws.headers.get("origin")
    if not _origin_allowed(origin) and not settings.dev_mode:
        await ws.close(code=1008, reason="Origin not allowed")
        return

    await ws.accept()
    job = await get_job_or_restore(job_id)
    if not job:
        await ws.send_json({"event": "error", "message": "job not found"})
        await ws.close(code=1008)
        return

    redis_mode = bool(settings.redis_url and await redis_check())
    queue = None if redis_mode else await subscribe(job_id)
    pubsub = None
    if redis_mode:
        client = await _get_redis()
        try:
            pubsub = client.pubsub()
            await pubsub.subscribe(_redis_channel(job_id))
        except Exception:
            pubsub = None
            redis_mode = False
            queue = await subscribe(job_id)

    try:
        snap = snapshot(job_id)
        await ws.send_json({"event": "snapshot", "job": snap})
        if job.status == "done":
            await ws.send_json({"event": "complete", "job_id": job_id, "progress": 100})
            return
        if job.status == "interrupted":
            await ws.send_json({"event": "error", "job_id": job_id, "message": "Analysis was interrupted by a server restart; please resubmit the repository."})
            return

        while True:
            try:
                if redis_mode and pubsub is not None:
                    result = await _redis_wait_for_message(pubsub, timeout=30.0)
                    if result["kind"] == "outage":
                        # Redis may have disappeared after the initial readiness
                        # check. Continue from the local queue in this process.
                        redis_mode = False
                        if queue is None:
                            queue = await subscribe(job_id)
                        continue
                    if result["kind"] == "heartbeat":
                        await ws.send_json({"event": "heartbeat"})
                        continue
                    import json
                    payload = json.loads(result["data"])
                else:
                    payload = await asyncio.wait_for(queue.get(), timeout=30)  # type: ignore[union-attr]

                await ws.send_json(payload)
                if payload.get("event") in {"complete", "error"}:
                    break
            except asyncio.TimeoutError:
                await ws.send_json({"event": "heartbeat"})
    except WebSocketDisconnect:
        pass
    finally:
        if queue is not None:
            await unsubscribe(job_id, queue)
        if pubsub is not None:
            try:
                await pubsub.unsubscribe(_redis_channel(job_id))
                await pubsub.close()
            except Exception:
                pass
        try:
            await ws.close()
        except Exception:
            pass
