from __future__ import annotations

from contextlib import asynccontextmanager
import asyncio

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import ROOT, settings
from db import close_pool, init_db
from monitoring import RequestIDMiddleware, get_metrics
from routes import router

load_dotenv(ROOT / ".env")


async def _cleanup_loop():
    from job_store import cleanup_stale_jobs
    while True:
        await asyncio.sleep(3600)
        try:
            await cleanup_stale_jobs()
        except asyncio.CancelledError:
            raise
        except Exception:
            import logging
            logging.getLogger("repopilot.cleanup").exception("Periodic job cleanup failed")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Database initialization is synchronous (psycopg2); keep it off the event loop.
    # A database outage should be surfaced by /ready and API calls rather than
    # preventing the HTTP process from starting and accepting health checks.
    try:
        await asyncio.to_thread(init_db)
    except Exception:
        if not settings.dev_mode:
            import logging
            logging.getLogger("repopilot.startup").exception("Database initialization failed; service is not ready")
        else:
            raise

    cleanup_task = asyncio.create_task(_cleanup_loop())
    try:
        yield
    finally:
        cleanup_task.cancel()
        await asyncio.gather(cleanup_task, return_exceptions=True)
        close_pool()
    try:
        from job_store import _get_redis
        redis_client = await _get_redis()
        if redis_client is not None:
            await redis_client.aclose()
    except Exception:
        pass


app = FastAPI(title="RepoPilot API", version="2.0.0", lifespan=lifespan)
app.add_middleware(RequestIDMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(router)


@app.get("/health")
async def health():
    # Liveness endpoint: process is alive and able to answer HTTP requests.
    return {"status": "ok", "service": "repopilot-api", "version": app.version}


@app.get("/ready")
async def ready():
    # Readiness deliberately reports configuration/database state without exposing
    # secrets. In DEV_MODE the service may run without external dependencies.
    missing = settings.missing_production_config() if not settings.dev_mode else []
    db_ok = True
    if settings.database_url:
        try:
            from db import check_connection
            await asyncio.to_thread(check_connection)
        except Exception:
            db_ok = False
    ready_state = not missing and db_ok
    redis_ok = await __import__("job_store").redis_check() if settings.redis_url else True
    payload = {"status": "ready" if ready_state and redis_ok else "not_ready", "database": "ok" if db_ok else "unavailable", "redis": "ok" if redis_ok else "unavailable", "missing": missing}
    if (not ready_state or not redis_ok) and not settings.dev_mode:
        from fastapi import HTTPException
        raise HTTPException(status_code=503, detail=payload)
    return payload


@app.get("/metrics")
async def metrics():
    return get_metrics()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
