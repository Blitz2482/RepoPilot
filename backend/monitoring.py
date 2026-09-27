from __future__ import annotations

import logging
import time
import uuid
from collections import Counter
from typing import Callable

try:
    import sentry_sdk
except Exception:  # pragma: no cover
    sentry_sdk = None

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

from config import settings

logger = logging.getLogger("repopilot")
logger.setLevel(logging.INFO)


class _RequestIDFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        # Child loggers (for example repopilot.cleanup) do not necessarily run
        # inside an HTTP request, so make the formatter safe for both contexts.
        if not hasattr(record, "request_id"):
            record.request_id = "-"
        return True


if not logger.handlers:
    handler = logging.StreamHandler()
    handler.addFilter(_RequestIDFilter())
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s request_id=%(request_id)s %(message)s"))
    logger.addHandler(handler)

_stats = Counter()
_total_request_duration = 0.0
_total_repo_duration = 0.0

if sentry_sdk and settings.sentry_dsn:
    sentry_sdk.init(dsn=settings.sentry_dsn, traces_sample_rate=0.1)


class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable):
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        started = time.perf_counter()
        try:
            response = await call_next(request)
            _stats["requests"] += 1
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Content-Type-Options"] = "nosniff"
            response.headers["X-Frame-Options"] = "DENY"
            response.headers["Referrer-Policy"] = "no-referrer"
            return response
        except Exception as exc:
            _stats["errors"] += 1
            if sentry_sdk:
                sentry_sdk.capture_exception(exc)
            raise
        finally:
            global _total_request_duration
            _total_request_duration += time.perf_counter() - started
            logger.info(
                "%s %s completed",
                request.method,
                request.url.path,
                extra={"request_id": request_id},
            )


def mark_repo_analyzed(duration_seconds: float) -> None:
    _stats["repos_analyzed"] += 1
    global _total_repo_duration
    _total_repo_duration += duration_seconds


def mark_error() -> None:
    _stats["errors"] += 1


def get_metrics() -> dict:
    analyzed = _stats["repos_analyzed"]
    return {
        "repos_analyzed": analyzed,
        "avg_duration_seconds": round(_total_repo_duration / analyzed, 3) if analyzed else 0.0,
        "avg_request_duration_seconds": round(_total_request_duration / _stats["requests"], 3) if _stats["requests"] else 0.0,
        "error_count": _stats["errors"],
        "request_count": _stats["requests"],
    }
