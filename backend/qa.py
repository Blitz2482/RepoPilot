from __future__ import annotations

import asyncio

from bob_client import answer_with_bob
from search import hybrid_search


async def answer_question(job_id: str, question: str, max_chars: int = 500) -> dict:
    question = question.strip()
    if not question:
        raise ValueError("question cannot be empty")
    if len(question) > max_chars:
        raise ValueError(f"question must be {max_chars} characters or fewer")

    chunks = await hybrid_search(job_id, question, top_k=10)
    if not chunks:
        return {"answer": "insufficient evidence", "citations": []}

    try:
        result = await asyncio.wait_for(answer_with_bob(question, chunks), timeout=30)
    except asyncio.TimeoutError:
        return {"answer": "service busy, try again", "citations": []}

    citations = []
    retrieved = [
        (c["path"], int(c["start_line"]), int(c["end_line"]))
        for c in chunks
    ]
    for citation in result.get("citations", []) or []:
        try:
            path = str(citation.get("path", ""))
            start = int(citation.get("start", 0))
            end = int(citation.get("end", 0))
        except (TypeError, ValueError):
            continue
        if start < 1 or end < start:
            continue
        if any(path == p and start >= s and end <= e for p, s, e in retrieved):
            citations.append({"path": path, "start": start, "end": end})
    answer = str(result.get("answer", "insufficient evidence")).strip()
    if not citations:
        return {"answer": "insufficient evidence", "citations": []}
    return {"answer": answer or "insufficient evidence", "citations": citations}
