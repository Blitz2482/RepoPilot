from __future__ import annotations

import asyncio
import hashlib
import logging
import math
import time
from typing import Sequence

from config import settings
from db import clear_chunks, save_chunks_bulk

logger = logging.getLogger(__name__)
EXPECTED_DIMENSIONS = 1536


def _local_embedding(text: str, dimensions: int = EXPECTED_DIMENSIONS) -> list[float]:
    values = [0.0] * dimensions
    encoded = text.encode("utf-8", errors="ignore")
    for i in range(0, len(encoded), 8):
        digest = hashlib.sha256(encoded[i:i + 8] + i.to_bytes(4, "little")).digest()
        idx = int.from_bytes(digest[:4], "little") % dimensions
        values[idx] += (int.from_bytes(digest[4:8], "little") / 2**32) * 2 - 1
    norm = math.sqrt(sum(v * v for v in values)) or 1.0
    return [v / norm for v in values]


async def _openai_embeddings(texts: Sequence[str]) -> list[list[float]]:
    if not settings.openai_api_key:
        raise RuntimeError("OPENAI_API_KEY is not configured")
    from openai import AsyncOpenAI
    client = AsyncOpenAI(api_key=settings.openai_api_key, timeout=min(settings.node_timeout_seconds, 25), max_retries=0)
    for attempt in range(3):
        try:
            response = await client.embeddings.create(model=settings.embedding_model, input=list(texts))
            vectors = [item.embedding for item in response.data]
            if any(len(vector) != EXPECTED_DIMENSIONS for vector in vectors):
                raise ValueError(f"{settings.embedding_model} returned a vector with unexpected dimension; expected {EXPECTED_DIMENSIONS}")
            return vectors
        except Exception:
            if attempt == 2:
                raise
            await asyncio.sleep(2 ** attempt)
    raise RuntimeError("embedding request failed")


async def embed_text(text: str) -> list[float]:
    if settings.openai_api_key and not settings.local_embeddings:
        return (await _openai_embeddings([text]))[0]
    return _local_embedding(text)


async def embed_chunks(job_id: str, chunks: list[dict]) -> None:
    started = time.perf_counter()
    if settings.database_url:
        await asyncio.to_thread(clear_chunks, job_id)
    for batch_start in range(0, len(chunks), 100):
        batch = chunks[batch_start:batch_start + 100]
        if settings.openai_api_key and not settings.local_embeddings:
            vectors = await _openai_embeddings([c["content"] for c in batch])
        else:
            vectors = [_local_embedding(c["content"]) for c in batch]
        if settings.database_url:
            await asyncio.to_thread(save_chunks_bulk, job_id, batch, vectors)
        logger.info("Embedded %d/%d chunks", min(batch_start + len(batch), len(chunks)), len(chunks))
        if time.perf_counter() - started > 300:
            raise TimeoutError("Embedding pipeline exceeded 5 minutes")
