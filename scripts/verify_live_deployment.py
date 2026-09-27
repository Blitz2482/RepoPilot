from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any


def request_json(
    base_url: str,
    path: str,
    method: str = "GET",
    payload: dict | None = None,
    timeout: int = 20,
) -> tuple[int, Any]:
    url = base_url.rstrip("/") + path
    body = None
    headers = {"Accept": "application/json"}
    if payload is not None:
        body = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            raw = response.read().decode("utf-8", errors="replace")
            return response.status, json.loads(raw) if raw else None
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            data = raw
        return exc.code, data


async def verify_websocket(base_url: str, job_id: str, timeout: int = 30) -> None:
    try:
        import websockets
    except ImportError as exc:  # pragma: no cover - environment-dependent dependency
        raise RuntimeError(
            "websockets is required for live WebSocket verification. "
            "Install it with `pip install websockets` or install `uvicorn[standard]`."
        ) from exc

    parsed = urllib.parse.urlsplit(base_url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise RuntimeError("backend_url must be an absolute HTTP(S) URL")
    ws_scheme = "wss" if parsed.scheme == "https" else "ws"
    ws_url = urllib.parse.urlunsplit((ws_scheme, parsed.netloc, f"/api/repos/{job_id}/stream", "", ""))

    saw_snapshot = False
    saw_terminal = False
    async with websockets.connect(ws_url, open_timeout=10, close_timeout=10, ping_interval=20, ping_timeout=20) as ws:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            remaining = max(1, int(deadline - time.monotonic()))
            raw = await asyncio.wait_for(ws.recv(), timeout=remaining)
            message = json.loads(raw)
            event = message.get("event")
            if event == "snapshot":
                saw_snapshot = True
                continue
            if event == "complete":
                saw_terminal = True
                break
            if event == "error":
                raise RuntimeError(f"live WebSocket returned an error: {message}")
            if event in {"agent_progress", "heartbeat"}:
                continue
            raise RuntimeError(f"unexpected WebSocket event: {message}")

    if not saw_snapshot or not saw_terminal:
        raise RuntimeError(f"WebSocket contract failed: snapshot={saw_snapshot}, terminal={saw_terminal}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify a deployed RepoPilot backend end-to-end.")
    parser.add_argument("backend_url", help="Public HTTP(S) base URL of the deployed FastAPI service")
    parser.add_argument("--repo", required=True, help="Small public GitHub repository used for the live smoke test")
    parser.add_argument("--role", default="Full-Stack", choices=["Backend", "Frontend", "Full-Stack", "Data", "DevOps", "QA"])
    parser.add_argument("--timeout", type=int, default=300)
    parser.add_argument("--ws-timeout", type=int, default=30)
    args = parser.parse_args()

    base = args.backend_url.rstrip("/")
    parsed = urllib.parse.urlsplit(base)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        print("backend_url must be an absolute HTTP(S) URL", file=sys.stderr)
        return 2

    for path in ("/health", "/ready", "/openapi.json", "/metrics"):
        status, payload = request_json(base, path)
        print(f"{path}: HTTP {status}")
        if status != 200:
            print(payload)
            return 1

    status, created = request_json(base, "/api/repos", "POST", {"repo_url": args.repo, "role": args.role})
    if status != 202 or not isinstance(created, dict) or not created.get("job_id"):
        print("Repository submission failed:", status, created)
        return 1

    job_id = str(created["job_id"])
    print("job_id:", job_id)

    # Verify the status endpoint while the actual analysis is still in progress.
    deadline = time.time() + args.timeout
    latest = None
    while time.time() < deadline:
        status, latest = request_json(base, f"/api/repos/{urllib.parse.quote(job_id)}")
        if status != 200:
            print("status request failed:", status, latest)
            return 1
        if latest.get("status") in {"done", "failed", "interrupted"}:
            break
        time.sleep(2)

    if not latest or latest.get("status") != "done":
        print("Analysis did not finish successfully:", latest)
        return 1
    print("job status: done")

    status, plan = request_json(base, f"/api/repos/{job_id}/plan")
    if status != 200 or not isinstance(plan, dict):
        print("Plan endpoint failed:", status, plan)
        return 1
    steps = plan.get("tour_steps") or []
    if len(steps) != 8 or [step.get("step") for step in steps] != list(range(1, 9)):
        print("Tour contract failed:", steps)
        return 1
    if not plan.get("role") or not isinstance(plan.get("key_concepts"), list):
        print("Plan schema contract failed:", plan)
        return 1
    print("plan: exactly 8 ordered tour steps")

    status, tour = request_json(base, f"/api/repos/{job_id}/tour")
    tour_steps = (tour or {}).get("tour_steps", [])
    if status != 200 or len(tour_steps) != 8 or [step.get("step") for step in tour_steps] != list(range(1, 9)):
        print("Tour endpoint failed:", status, tour)
        return 1
    print("tour: 8 ordered steps returned")

    # Validate every displayed citation, not just the first one. This catches a
    # plan/source mismatch before the deployed frontend can hit it.
    for step in steps:
        query = urllib.parse.urlencode({"path": step["path"], "start": step["start"], "end": step["end"]})
        status, source = request_json(base, f"/api/repos/{job_id}/source?{query}")
        if status != 200 or not isinstance(source, dict) or not source.get("content"):
            print("Source endpoint failed for step", step.get("step"), status, source)
            return 1
    print("source: all 8 tour citations loaded")

    status, answer = request_json(base, f"/api/repos/{job_id}/ask", "POST", {"question": "What is the main entry point?"})
    if status != 200 or not isinstance(answer, dict) or "answer" not in answer or "citations" not in answer:
        print("Q&A endpoint failed:", status, answer)
        return 1
    for citation in answer.get("citations", []) or []:
        try:
            query = urllib.parse.urlencode({"path": citation["path"], "start": citation["start"], "end": citation["end"]})
        except (KeyError, TypeError):
            print("Q&A citation shape invalid:", citation)
            return 1
        status, source = request_json(base, f"/api/repos/{job_id}/source?{query}")
        if status != 200 or not isinstance(source, dict) or not source.get("content"):
            print("Q&A citation did not resolve:", citation, status, source)
            return 1
    print("Q&A: answer/citations returned and citations resolve to source")

    try:
        asyncio.run(verify_websocket(base, job_id, timeout=args.ws_timeout))
        print("WebSocket: snapshot + terminal complete received")
    except Exception as exc:
        print("WebSocket verification failed:", exc)
        return 1

    print("Live deployment verification PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
