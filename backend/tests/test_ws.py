import asyncio
import os

from fastapi.testclient import TestClient

os.environ.setdefault("DEV_MODE", "true")
os.environ.setdefault("MOCK_BOB", "true")

from main import app
from job_store import create_job


def test_websocket_sends_snapshot():
    client = TestClient(app)
    job_id = "33333333-3333-3333-3333-333333333333"
    import asyncio
    asyncio.run(create_job(job_id, "https://github.com/example/repo", "QA"))
    with client.websocket_connect(f"/api/repos/{job_id}/stream") as ws:
        message = ws.receive_json()
        assert message["event"] == "snapshot"
        assert message["job"]["job_id"] == job_id


class _IdlePubSub:
    async def get_message(self, **kwargs):
        return None


def test_redis_idle_does_not_look_like_outage():
    from ws import _redis_wait_for_message
    result = asyncio.run(_redis_wait_for_message(_IdlePubSub(), timeout=0.01))
    assert result["kind"] == "heartbeat"
