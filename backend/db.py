from __future__ import annotations

import json
import logging
from contextlib import contextmanager
from pathlib import Path
from threading import Lock
from typing import Iterable

from config import settings

try:
    from psycopg2 import pool
    from psycopg2.extras import RealDictCursor, execute_values
except Exception:  # pragma: no cover
    pool = None
    RealDictCursor = None
    execute_values = None

logger = logging.getLogger(__name__)
_pool = None
_pool_lock = Lock()


def _require_pool():
    global _pool
    if not settings.database_url:
        raise RuntimeError("DATABASE_URL is not configured")
    if pool is None:
        raise RuntimeError("psycopg2-binary is not installed")
    with _pool_lock:
        if _pool is None:
            _pool = pool.ThreadedConnectionPool(1, 8, dsn=settings.database_url)
    return _pool


@contextmanager
def connection():
    p = _require_pool()
    conn = p.getconn()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        p.putconn(conn)


def check_connection() -> None:
    with connection() as conn, conn.cursor() as cur:
        cur.execute("SELECT 1")
        cur.fetchone()


def init_db() -> None:
    if not settings.database_url:
        logger.warning("DATABASE_URL not configured; running without Postgres persistence")
        return
    schema_path = Path(__file__).with_name("schema.sql")
    with connection() as conn, conn.cursor() as cur:
        cur.execute(schema_path.read_text(encoding="utf-8"))


def create_repo(url: str, job_id: str) -> str:
    with connection() as conn, conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO repositories (id, url)
            VALUES (%s::uuid, %s)
            ON CONFLICT (id) DO UPDATE SET url = EXCLUDED.url
            """,
            (job_id, url),
        )
    return job_id


def get_repo(repo_id: str) -> dict | None:
    with connection() as conn, conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("SELECT * FROM repositories WHERE id = %s::uuid", (repo_id,))
        row = cur.fetchone()
        return dict(row) if row else None


def save_plan(repo_id: str, plan_dict: dict) -> None:
    role = plan_dict.get("role", "Full-Stack")
    repo_context = plan_dict.get("repo_context") or {}
    default_branch = repo_context.get("default_branch") if isinstance(repo_context, dict) else None
    with connection() as conn, conn.cursor() as cur:
        cur.execute("DELETE FROM onboarding_plans WHERE repo_id = %s::uuid", (repo_id,))
        cur.execute(
            "INSERT INTO onboarding_plans (repo_id, role, plan_json) VALUES (%s::uuid, %s, %s::jsonb)",
            (repo_id, role, json.dumps(plan_dict)),
        )
        cur.execute(
            "UPDATE repositories SET default_branch = %s, analyzed_at = now() WHERE id = %s::uuid",
            (default_branch, repo_id),
        )


def get_plan(repo_id: str) -> dict | None:
    with connection() as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT plan_json FROM onboarding_plans WHERE repo_id = %s::uuid ORDER BY created_at DESC LIMIT 1",
            (repo_id,),
        )
        row = cur.fetchone()
        if not row:
            return None
        return row[0] if isinstance(row[0], dict) else json.loads(row[0])


def _vector_literal(embedding: list[float]) -> str:
    return "[" + ",".join(f"{float(v):.8f}" for v in embedding) + "]"


def save_chunks_bulk(repo_id: str, chunks: Iterable[dict], embeddings: Iterable[list[float] | None]) -> None:
    if execute_values is None:
        raise RuntimeError("psycopg2 execute_values is unavailable")
    rows = []
    for chunk, embedding in zip(chunks, embeddings):
        vector = _vector_literal(embedding) if embedding is not None else None
        rows.append((repo_id, chunk["path"], chunk["start_line"], chunk["end_line"], chunk["content"], vector, chunk["content"]))
    if not rows:
        return
    with connection() as conn, conn.cursor() as cur:
        execute_values(
            cur,
            """
            INSERT INTO code_chunks (repo_id, path, start_line, end_line, content, embedding, code_chunks_fts)
            VALUES %s
            """,
            rows,
            template="(%s::uuid, %s, %s, %s, %s, %s::vector, to_tsvector('english', %s))",
            page_size=100,
        )


def clear_chunks(repo_id: str) -> None:
    with connection() as conn, conn.cursor() as cur:
        cur.execute("DELETE FROM code_chunks WHERE repo_id = %s::uuid", (repo_id,))


def search_chunks(repo_id: str, query_embedding: list[float], top_k: int = 10) -> list[dict]:
    if len(query_embedding) != 1536:
        raise ValueError("embedding dimension must be 1536")
    literal = _vector_literal(query_embedding)
    with connection() as conn, conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """
            SELECT id, repo_id, path, start_line, end_line, content,
                   1 - (embedding <=> %s::vector) AS similarity
            FROM code_chunks
            WHERE repo_id = %s::uuid AND embedding IS NOT NULL
            ORDER BY embedding <=> %s::vector
            LIMIT %s
            """,
            (literal, repo_id, literal, top_k),
        )
        return [dict(r) for r in cur.fetchall()]


def search_keyword_chunks(repo_id: str, query: str, top_k: int = 10) -> list[dict]:
    with connection() as conn, conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """
            SELECT id, repo_id, path, start_line, end_line, content,
                   ts_rank_cd(code_chunks_fts, websearch_to_tsquery('english', %s)) AS keyword_score
            FROM code_chunks
            WHERE repo_id = %s::uuid
              AND code_chunks_fts @@ websearch_to_tsquery('english', %s)
            ORDER BY keyword_score DESC
            LIMIT %s
            """,
            (query, repo_id, query, top_k),
        )
        return [dict(r) for r in cur.fetchall()]


def close_pool() -> None:
    global _pool
    if _pool and pool:
        _pool.closeall()
        _pool = None
