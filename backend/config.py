from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int, minimum: int = 1) -> int:
    value = os.getenv(name)
    if value is None or not value.strip():
        return default
    try:
        parsed = int(value)
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer") from exc
    if parsed < minimum:
        raise ValueError(f"{name} must be >= {minimum}")
    return parsed


@dataclass(frozen=True)
class Settings:
    database_url: str | None = os.getenv("DATABASE_URL") or None
    bob_api_key: str | None = os.getenv("BOB_API_KEY") or None
    bob_base_url: str = os.getenv("BOB_BASE_URL", "").strip()
    bob_endpoint: str = os.getenv("BOB_ENDPOINT", "").strip()
    github_token: str | None = os.getenv("GITHUB_TOKEN") or None
    allow_private_repos: bool = _env_bool("ALLOW_PRIVATE_REPOS", False)
    openai_api_key: str | None = os.getenv("OPENAI_API_KEY") or None
    openai_model: str = os.getenv("OPENAI_MODEL", "gpt-4o").strip()
    embedding_model: str = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small").strip()
    local_embeddings: bool = _env_bool("LOCAL_EMBEDDINGS", True)
    mock_bob: bool = _env_bool("MOCK_BOB", True)
    dev_mode: bool = _env_bool("DEV_MODE", True)
    sentry_dsn: str | None = os.getenv("SENTRY_DSN") or None
    redis_url: str | None = os.getenv("REDIS_URL") or None
    cors_origins: str = os.getenv("CORS_ORIGINS", "http://localhost:3000")
    max_repo_mb: int = _env_int("MAX_REPO_MB", 100)
    max_parsed_file_mb: int = _env_int("MAX_PARSED_FILE_MB", 5)
    max_source_file_mb: int = _env_int("MAX_SOURCE_FILE_MB", 2)
    clone_timeout_seconds: int = _env_int("CLONE_TIMEOUT_SECONDS", 60)
    node_timeout_seconds: int = _env_int("NODE_TIMEOUT_SECONDS", 120)
    pipeline_timeout_seconds: int = _env_int("PIPELINE_TIMEOUT_SECONDS", 300)
    max_concurrent_jobs: int = _env_int("MAX_CONCURRENT_JOBS", 2)
    max_question_chars: int = _env_int("MAX_QUESTION_CHARS", 500)
    source_max_lines: int = _env_int("SOURCE_MAX_LINES", 400)
    job_retention_hours: int = _env_int("JOB_RETENTION_HOURS", 24)
    bob_log_exchanges: bool = _env_bool("BOB_LOG_EXCHANGES", False)

    @property
    def allowed_origins(self) -> list[str]:
        return [x.strip().rstrip("/") for x in self.cors_origins.split(",") if x.strip()]

    def missing_production_config(self) -> list[str]:
        missing: list[str] = []
        if not self.database_url:
            missing.append("DATABASE_URL")
        if not self.bob_api_key:
            missing.append("BOB_API_KEY")
        if not self.bob_base_url:
            missing.append("BOB_BASE_URL")
        if not self.bob_endpoint:
            missing.append("BOB_ENDPOINT")
        if not self.openai_api_key:
            missing.append("OPENAI_API_KEY")
        if self.local_embeddings:
            missing.append("LOCAL_EMBEDDINGS=false")
        if self.mock_bob:
            missing.append("MOCK_BOB=false")
        if self.allow_private_repos and not self.github_token:
            missing.append("GITHUB_TOKEN (required when ALLOW_PRIVATE_REPOS=true)")
        return missing

    def validate_safety(self) -> None:
        if not self.dev_mode:
            if not self.allowed_origins or "*" in self.allowed_origins:
                raise RuntimeError("CORS_ORIGINS must contain explicit origins when DEV_MODE=false")
            from urllib.parse import urlparse
            for origin in self.allowed_origins:
                parsed = urlparse(origin)
                if parsed.scheme not in {"http", "https"} or not parsed.netloc or parsed.path not in {"", "/"} or parsed.query or parsed.fragment:
                    raise RuntimeError("CORS_ORIGINS entries must be absolute http(s) origins")
            if self.bob_log_exchanges:
                raise RuntimeError("BOB_LOG_EXCHANGES must be false in production")
            if self.allow_private_repos and not self.github_token:
                raise RuntimeError("GITHUB_TOKEN is required when ALLOW_PRIVATE_REPOS=true")
            from urllib.parse import urlparse
            if self.bob_base_url:
                parsed_bob = urlparse(self.bob_base_url)
                if parsed_bob.scheme != "https" or not parsed_bob.netloc or parsed_bob.query or parsed_bob.fragment:
                    raise RuntimeError("BOB_BASE_URL must be an HTTPS URL without a query or fragment in production")
            if self.bob_endpoint and not self.bob_endpoint.startswith("/"):
                raise RuntimeError("BOB_ENDPOINT must start with '/'")


settings = Settings()
settings.validate_safety()
