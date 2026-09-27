from __future__ import annotations

import asyncio
import logging
import posixpath
import uuid
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query, WebSocket

from config import settings
from ingest import clone_repo, list_displayable_files, validate_github_url
from models import OnboardingPlan, QAResponse, QuestionRequest, RepoCreateRequest, RepoCreateResponse, SourceResponse
from qa import answer_question
from ws import stream_job

router = APIRouter(prefix="/api")
logger = logging.getLogger("repopilot.api")
_pipeline_slots = asyncio.Semaphore(settings.max_concurrent_jobs)


_CODE_EXTENSIONS = {
    ".py", ".ts", ".tsx", ".js", ".jsx", ".java", ".go", ".rs", ".rb", ".php", ".cs", ".c", ".cc", ".cpp", ".h", ".hpp",
    ".md", ".json", ".yaml", ".yml", ".toml", ".ini", ".cfg", ".txt", ".sql", ".html", ".css", ".scss", ".sh",
}


def _validate_job_id(job_id: str) -> str:
    try:
        return str(uuid.UUID(job_id))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="invalid repository job id") from exc


async def _repo_or_404(job_id: str):
    job_id = _validate_job_id(job_id)
    from job_store import get_job_or_restore
    job = await get_job_or_restore(job_id)
    if job:
        return job
    raise HTTPException(status_code=404, detail="repository job not found")


async def _persist_repo(job_id: str, repo_url: str) -> None:
    if settings.database_url:
        from db import create_repo
        await asyncio.to_thread(create_repo, repo_url, job_id)


async def _run_background(job_id: str, repo_url: str, role: str) -> None:
    from graph import run_pipeline
    async with _pipeline_slots:
        try:
            async for _ in run_pipeline(job_id, repo_url, role):
                pass
        except Exception:
            logger.exception("background pipeline failed job_id=%s", job_id)


@router.post("/repos", response_model=RepoCreateResponse, status_code=202)
async def create_repository(request: RepoCreateRequest, background_tasks: BackgroundTasks):
    try:
        repo_url = validate_github_url(request.repo_url)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    job_id = str(uuid.uuid4())
    from job_store import create_job
    await create_job(job_id, repo_url, request.role)
    try:
        await _persist_repo(job_id, repo_url)
    except Exception as exc:
        logger.exception("database persistence failed job_id=%s", job_id)
        if not settings.dev_mode:
            raise HTTPException(status_code=503, detail="Database is unavailable") from exc

    background_tasks.add_task(_run_background, job_id, repo_url, request.role)
    return RepoCreateResponse(job_id=job_id, status="queued")


@router.get("/repos/{job_id}")
async def get_repository(job_id: str):
    job = await _repo_or_404(job_id)
    from job_store import snapshot
    return snapshot(job.job_id)


async def _load_plan(job_id: str) -> OnboardingPlan | None:
    from job_store import get_job_or_restore
    job = await get_job_or_restore(job_id)
    if job and job.plan:
        return OnboardingPlan(**job.plan)
    if settings.database_url:
        from db import get_plan as db_get_plan
        plan = await asyncio.to_thread(db_get_plan, job_id)
        if plan:
            return OnboardingPlan(**plan)
    return None


@router.get("/repos/{job_id}/plan", response_model=OnboardingPlan)
async def get_plan(job_id: str):
    await _repo_or_404(job_id)
    plan = await _load_plan(job_id)
    if plan:
        return plan
    raise HTTPException(status_code=409, detail="onboarding plan not ready")


@router.get("/repos/{job_id}/tour")
async def get_tour(job_id: str):
    await _repo_or_404(job_id)
    plan = await _load_plan(job_id)
    if plan:
        return {"tour_steps": [step.model_dump() for step in plan.tour_steps]}
    raise HTTPException(status_code=409, detail="code tour not ready")


def _safe_source_path(path: str) -> str:
    normalized = posixpath.normpath(path.replace("\\", "/")).lstrip("/")
    if normalized in {"", "."} or normalized.startswith("../") or normalized == "..":
        raise HTTPException(status_code=400, detail="invalid source path")
    return normalized


async def _ensure_repo_path(job) -> None:
    if job.repo_path:
        return
    from job_store import repo_lock, update_job
    async with repo_lock(job.job_id):
        if job.repo_path:
            return
        path = await clone_repo(job.repo_url, job.job_id)
        await update_job(job.job_id, repo_path=path, source_paths=list_displayable_files(path))


@router.get("/repos/{job_id}/source", response_model=SourceResponse)
async def get_source(
    job_id: str,
    path: str = Query(..., min_length=1, max_length=500),
    start: int = Query(1, ge=1),
    end: int = Query(1, ge=1),
):
    job = await _repo_or_404(job_id)
    safe_path = _safe_source_path(path)
    if Path(safe_path).suffix.lower() not in _CODE_EXTENSIONS:
        raise HTTPException(status_code=400, detail="source file type is not supported")

    # A restored completed job may not have its ephemeral clone anymore. Re-clone
    # on first source request instead of forcing the user to re-run analysis.
    if not job.repo_path:
        if job.status not in {"done", "interrupted"}:
            raise HTTPException(status_code=409, detail="repository not ingested")
        try:
            await _ensure_repo_path(job)
        except Exception as exc:
            logger.exception("source re-clone failed job_id=%s", job.job_id)
            raise HTTPException(status_code=502, detail="repository source is temporarily unavailable") from exc

    if job.source_paths and safe_path not in job.source_paths:
        raise HTTPException(status_code=404, detail="source file was not available in the analyzed repository")
    if not job.repo_path:
        raise HTTPException(status_code=409, detail="repository not ingested")

    base = Path(job.repo_path).resolve()
    target = (base / safe_path).resolve()
    if base not in target.parents or not target.is_file() or target.is_symlink():
        raise HTTPException(status_code=404, detail="source file not found")
    if target.stat().st_size > settings.max_source_file_mb * 1024 * 1024:
        raise HTTPException(status_code=413, detail="source file is too large to display")
    lines = target.read_text(encoding="utf-8", errors="replace").splitlines()
    bounded_end = min(end, start + settings.source_max_lines - 1, len(lines))
    if start > bounded_end:
        raise HTTPException(status_code=400, detail="invalid line range")
    return SourceResponse(path=safe_path, start=start, end=bounded_end, content="\n".join(lines[start - 1:bounded_end]))


@router.post("/repos/{job_id}/ask", response_model=QAResponse)
async def ask(job_id: str, request: QuestionRequest):
    await _repo_or_404(job_id)
    try:
        result = await answer_question(job_id, request.question, max_chars=settings.max_question_chars)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Q&A failed job_id=%s", job_id)
        raise HTTPException(status_code=502, detail="Repository Q&A service is temporarily unavailable") from exc
    return QAResponse(**result)


@router.websocket("/repos/{job_id}/stream")
async def websocket_stream(ws: WebSocket, job_id: str):
    try:
        normalized = _validate_job_id(job_id)
    except HTTPException:
        await ws.close(code=1008, reason="Invalid job id")
        return
    await stream_job(ws, normalized)
