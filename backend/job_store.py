from __future__ import annotations

import asyncio
import json
import logging
import shutil
import time
from dataclasses import dataclass, field
from typing import Any

from config import settings

logger = logging.getLogger(__name__)


@dataclass
class JobRecord:
    job_id: str
    repo_url: str
    role: str
    status: str = "queued"
    progress: int = 0
    node: str | None = None
    latest_message: str = "Queued"
    agents: dict[str, dict[str, Any]] = field(default_factory=dict)
    repo_context: dict[str, Any] | None = None
    plan: dict[str, Any] | None = None
    repo_path: str | None = None
    chunks: list[dict[str, Any]] = field(default_factory=list)
    source_paths: set[str] = field(default_factory=set)
    error: str | None = None
    created_at: float = field(default_factory=time.time)


_jobs: dict[str, JobRecord] = {}
_subscribers: dict[str, set[asyncio.Queue]] = {}
_repo_locks: dict[str, asyncio.Lock] = {}
_lock = asyncio.Lock()
_redis = None


def _redis_channel(job_id: str) -> str:
    return f"repopilot:job:{job_id}"


async def _get_redis():
    global _redis
    if not settings.redis_url:
        return None
    if _redis is None:
        try:
            import redis.asyncio as redis
            _redis = redis.from_url(settings.redis_url, decode_responses=True)
        except Exception as exc:
            logger.warning("Redis setup unavailable: %s", type(exc).__name__)
            _redis = None
    return _redis


async def redis_check() -> bool:
    client = await _get_redis()
    if client is None:
        return not bool(settings.redis_url)
    try:
        return bool(await client.ping())
    except Exception:
        global _redis
        _redis = None
        return False


async def create_job(job_id: str, repo_url: str, role: str) -> JobRecord:
    await cleanup_stale_jobs()
    async with _lock:
        job = JobRecord(job_id=job_id, repo_url=repo_url, role=role)
        _jobs[job_id] = job
        _subscribers.setdefault(job_id, set())
        _repo_locks.setdefault(job_id, asyncio.Lock())
        return job


def get_job(job_id: str) -> JobRecord | None:
    return _jobs.get(job_id)


async def restore_job_from_db(job_id: str) -> JobRecord | None:
    """Restore a completed/interrupted job after an API process restart.

    Runtime job state is intentionally lightweight, while completed onboarding
    plans are durable in PostgreSQL. The bundle's schema does not include a
    job-status table, so unfinished jobs are reported as interrupted rather
    than falsely marked as still running.
    """
    existing = get_job(job_id)
    if existing:
        return existing
    if not settings.database_url:
        return None

    from db import get_plan, get_repo

    try:
        repo = await asyncio.to_thread(get_repo, job_id)
        if not repo:
            return None
        plan = await asyncio.to_thread(get_plan, job_id)
    except Exception as exc:
        logger.warning("Could not restore job %s from database: %s", job_id, type(exc).__name__)
        return None

    repo_url = str(repo.get("url", ""))
    role = str((plan or {}).get("role", "Full-Stack"))
    repo_context = (plan or {}).get("repo_context") if isinstance(plan, dict) else None
    status = "done" if plan else "interrupted"
    progress = 100 if plan else 0
    message = "Onboarding plan restored from database" if plan else "Analysis was interrupted by an API restart"
    job = JobRecord(
        job_id=job_id,
        repo_url=repo_url,
        role=role,
        status=status,
        progress=progress,
        node="emit" if plan else None,
        latest_message=message,
        repo_context=repo_context,
        plan=plan if isinstance(plan, dict) else None,
        created_at=time.time(),
    )
    async with _lock:
        _jobs.setdefault(job_id, job)
        _subscribers.setdefault(job_id, set())
        _repo_locks.setdefault(job_id, asyncio.Lock())
    return _jobs[job_id]


async def get_job_or_restore(job_id: str) -> JobRecord | None:
    job = get_job(job_id)
    return job or await restore_job_from_db(job_id)


async def update_job(job_id: str, **fields: Any) -> JobRecord:
    job = _jobs[job_id]
    for key, value in fields.items():
        setattr(job, key, value)
    return job


def snapshot(job_id: str) -> dict[str, Any] | None:
    job = _jobs.get(job_id)
    if not job:
        return None
    return {
        "job_id": job.job_id,
        "repo_url": job.repo_url,
        "role": job.role,
        "status": job.status,
        "progress": job.progress,
        "node": job.node,
        "latest_message": job.latest_message,
        "agents": job.agents,
        "repo_context": job.repo_context,
        "plan": job.plan,
        "source_paths": sorted(job.source_paths),
        "error": job.error,
    }


async def publish(job_id: str, payload: dict[str, Any]) -> None:
    # In-process subscribers keep the zero-infrastructure developer path fast.
    for queue in list(_subscribers.get(job_id, set())):
        await queue.put(payload)

    # Redis is an optional cross-process bus. A Redis outage never makes the
    # analysis itself fail; local subscribers continue to receive events.
    client = await _get_redis()
    if client is not None:
        try:
            await client.publish(_redis_channel(job_id), json.dumps(payload, default=str))
        except Exception as exc:
            logger.warning("Redis progress publish failed: %s", type(exc).__name__)
            global _redis
            _redis = None


async def subscribe(job_id: str) -> asyncio.Queue:
    queue: asyncio.Queue = asyncio.Queue()
    _subscribers.setdefault(job_id, set()).add(queue)
    return queue


async def unsubscribe(job_id: str, queue: asyncio.Queue) -> None:
    _subscribers.get(job_id, set()).discard(queue)


def repo_lock(job_id: str) -> asyncio.Lock:
    return _repo_locks.setdefault(job_id, asyncio.Lock())


async def set_progress(job_id: str, node: str, status: str, progress: int, message: str, **extra: Any) -> None:
    job = await update_job(
        job_id,
        node=node,
        status=status,
        progress=max(0, min(100, progress)),
        latest_message=message,
        **extra,
    )
    await publish(
        job_id,
        {
            "event": "agent_progress",
            "node": node,
            "status": status,
            "progress": job.progress,
            "latest_message": message,
            "agents": job.agents,
            "error": job.error,
        },
    )


async def cleanup_stale_jobs() -> None:
    cutoff = time.time() - settings.job_retention_hours * 3600
    stale = [
        job_id
        for job_id, job in _jobs.items()
        if job.created_at < cutoff
        and job.status in {"done", "failed", "interrupted"}
        and not _subscribers.get(job_id)
    ]
    for job_id in stale:
        job = _jobs.pop(job_id, None)
        _subscribers.pop(job_id, None)
        _repo_locks.pop(job_id, None)
        if job and job.repo_path:
            try:
                shutil.rmtree(job.repo_path, ignore_errors=True)
            except Exception:
                pass
