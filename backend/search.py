from __future__ import annotations

from collections import defaultdict

from bob_client import answer_with_bob
from config import settings
from db import search_chunks as db_vector_search, search_keyword_chunks as db_keyword_search
from embedder import embed_text


async def search_chunks(job_id: str, query_embedding: list[float], top_k: int = 10) -> list[dict]:
    if not settings.database_url:
        return []
    rows = db_vector_search(job_id, query_embedding, top_k=max(top_k * 2, top_k))
    return [row for row in rows if float(row.get("similarity", 0.0)) > 0.3][:top_k]


def _rrf(rank: int, k: int = 60) -> float:
    return 1.0 / (k + rank)


async def hybrid_search(job_id: str, query: str, top_k: int = 10) -> list[dict]:
    if not settings.database_url:
        # Local/demo mode keeps the same retrieval contract without requiring Postgres.
        from job_store import get_job
        import re
        job = get_job(job_id)
        if not job:
            return []
        q_terms = {t.lower() for t in re.findall(r"[a-zA-Z_][a-zA-Z0-9_]+", query)}
        scored = []
        for chunk in job.chunks:
            body_terms = {t.lower() for t in re.findall(r"[a-zA-Z_][a-zA-Z0-9_]+", chunk.get("content", ""))}
            overlap = len(q_terms & body_terms)
            if overlap:
                scored.append({**chunk, "rrf_score": float(overlap)})
        return sorted(scored, key=lambda r: r["rrf_score"], reverse=True)[:top_k]
    vector = await embed_text(query)
    vector_rows = await search_chunks(job_id, vector, top_k=top_k * 2)
    keyword_rows = db_keyword_search(job_id, query, top_k=top_k * 2)
    merged: dict[int, dict] = {}
    scores = defaultdict(float)
    for rank, row in enumerate(vector_rows, 1):
        key = int(row["id"])
        merged[key] = row
        scores[key] += _rrf(rank)
    for rank, row in enumerate(keyword_rows, 1):
        key = int(row["id"])
        merged[key] = {**merged.get(key, {}), **row}
        scores[key] += _rrf(rank)
    ordered = sorted(merged.values(), key=lambda row: scores[int(row["id"])], reverse=True)
    for row in ordered:
        row["rrf_score"] = scores[int(row["id"])]
    return ordered[:top_k]


async def rerank(query: str, chunks: list[dict]) -> list[dict]:
    top = chunks[:10]
    if not top or settings.mock_bob:
        return top[:5]
    result = await answer_with_bob(
        f"Rerank these chunks for the question: {query}",
        [{**c, "content": c.get("content", "")[:5000]} for c in top],
    )
    cited = {(c["path"], c["start"] , c["end"]) for c in result.get("citations", [])}
    ranked = [c for c in top if (c.get("path"), c.get("start_line"), c.get("end_line")) in cited]
    ranked.extend(c for c in top if c not in ranked)
    return ranked[:5]
