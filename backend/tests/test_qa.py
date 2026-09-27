import asyncio
import pytest

import qa


def test_empty_question():
    with pytest.raises(ValueError):
        asyncio.run(qa.answer_question("job", ""))


def test_long_question():
    with pytest.raises(ValueError):
        asyncio.run(qa.answer_question("job", "x" * 501))


def test_empty_retrieval_returns_insufficient_evidence(monkeypatch):
    async def no_chunks(*args, **kwargs):
        return []
    monkeypatch.setattr(qa, "hybrid_search", no_chunks)
    result = asyncio.run(qa.answer_question("job", "How does retry work?"))
    assert result == {"answer": "insufficient evidence", "citations": []}


def test_raw_answer_is_rejected_when_uncited(monkeypatch):
    async def one_chunk(*args, **kwargs):
        return [{"path": "a.py", "start_line": 1, "end_line": 5, "content": "retry"}]
    async def raw_answer(*args, **kwargs):
        return {"answer": "raw fallback", "citations": []}
    monkeypatch.setattr(qa, "hybrid_search", one_chunk)
    monkeypatch.setattr(qa, "answer_with_bob", raw_answer)
    result = asyncio.run(qa.answer_question("job", "retry"))
    assert result == {"answer": "insufficient evidence", "citations": []}


def test_timeout(monkeypatch):
    async def one_chunk(*args, **kwargs):
        return [{"path": "a.py", "start_line": 1, "end_line": 5, "content": "retry"}]
    async def slow_answer(*args, **kwargs):
        await asyncio.sleep(0.05)
        return {"answer": "x", "citations": []}
    monkeypatch.setattr(qa, "hybrid_search", one_chunk)
    monkeypatch.setattr(qa, "answer_with_bob", slow_answer)
    original = qa.asyncio.wait_for

    async def short_wait(awaitable, timeout):
        return await original(awaitable, 0.001)

    monkeypatch.setattr(qa.asyncio, "wait_for", short_wait)
    result = asyncio.run(qa.answer_question("job", "retry"))
    assert result["answer"] == "service busy, try again"


def test_uncited_provider_answer_is_not_presented_as_grounded(monkeypatch):
    async def one_chunk(*args, **kwargs):
        return [{"path": "a.py", "start_line": 1, "end_line": 5, "content": "retry"}]
    async def uncited_answer(*args, **kwargs):
        return {"answer": "This definitely works like this.", "citations": []}
    monkeypatch.setattr(qa, "hybrid_search", one_chunk)
    monkeypatch.setattr(qa, "answer_with_bob", uncited_answer)
    result = asyncio.run(qa.answer_question("job", "retry"))
    assert result == {"answer": "insufficient evidence", "citations": []}
