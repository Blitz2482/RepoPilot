import asyncio
from pathlib import Path

import graph
import ingest
from job_store import get_job


def test_local_full_pipeline(monkeypatch, tmp_path: Path):
    (tmp_path / "README.md").write_text("# Sample\n", encoding="utf-8")
    (tmp_path / "main.py").write_text(
        "def retry_request():\n    return True\n\nclass Service:\n    pass\n",
        encoding="utf-8",
    )

    async def fake_clone(repo_url: str, job_id: str) -> str:
        return str(tmp_path)

    monkeypatch.setattr(ingest, "clone_repo", fake_clone)

    async def run():
        job_id = "11111111-1111-1111-1111-111111111111"
        from job_store import create_job
        await create_job(job_id, "https://github.com/example/repo", "Full-Stack")
        async for _ in graph.run_pipeline(job_id, "https://github.com/example/repo", "Full-Stack"):
            pass
        return get_job(job_id)

    job = asyncio.run(run())
    assert job is not None
    assert job.status == "done"
    assert job.plan is not None
    assert len(job.plan["tour_steps"]) == 8
    assert [step["step"] for step in job.plan["tour_steps"]] == list(range(1, 9))


def test_tour_padding_uses_readme_anchor(monkeypatch, tmp_path: Path):
    (tmp_path / "README.md").write_text("# Sample\n\nHow this repository works.\n", encoding="utf-8")
    (tmp_path / "main.py").write_text("def main():\n    return True\n", encoding="utf-8")
    from synthesis import generate_tour
    async def no_bob_narration(evidence):
        return f"Explain {evidence['path']} {evidence['start']}-{evidence['end']}. This is grounded in the repository evidence."
    monkeypatch.setattr("synthesis.generate_narration", no_bob_narration)
    steps = asyncio.run(generate_tour([], [{"path":"main.py", "content":"def main():\\n    return True", "symbols":[{"name":"main","start_line":1,"end_line":2}]}], str(tmp_path)))
    assert len(steps) == 8
    assert any(step["path"] == "README.md" for step in steps)


def test_tour_rejects_fabricated_source_path(tmp_path: Path):
    (tmp_path / "main.py").write_text("def main():\n    return True\n", encoding="utf-8")
    from synthesis import generate_tour
    async def no_bob_narration(evidence):
        return "Grounded sentence one. Grounded sentence two."
    monkeypatch = __import__("pytest").MonkeyPatch()
    try:
        monkeypatch.setattr("synthesis.generate_narration", no_bob_narration)
        steps = asyncio.run(generate_tour([{"agent": "architecture", "summary": "x", "evidence": [{"path": "missing.py", "start": 1, "end": 10}], "confidence": 0.5}], [{"path":"main.py", "content":"def main():\n    return True\n", "symbols":[{"name":"main","start_line":1,"end_line":2}]}], str(tmp_path)))
        assert len(steps) == 8
        assert all(step["path"] == "main.py" for step in steps)
    finally:
        monkeypatch.undo()


def test_tour_narrations_are_two_sentences(monkeypatch, tmp_path):
    import asyncio
    from synthesis import generate_tour

    (tmp_path / "main.py").write_text("def main():\n    return 1\n", encoding="utf-8")
    async def one_sentence(_item):
        return "Only one sentence."
    monkeypatch.setattr("synthesis.generate_narration", one_sentence)

    findings = [{"agent": "architecture", "summary": "summary", "evidence": [{"path": "main.py", "start": 1, "end": 2, "note": "entry"}], "confidence": 0.8}]
    steps = asyncio.run(generate_tour(findings, parsed_files=[{"path": "main.py", "content": "def main():\n    return 1\n", "symbols": [{"name": "main", "type": "function_definition", "start_line": 1, "end_line": 2}]}], repo_path=str(tmp_path)))
    assert len(steps) == 8
    for step in steps:
        assert step["narration"].count(".") >= 2
        assert "main.py" in step["narration"]


def test_graph_step_retries_twice(monkeypatch):
    import asyncio
    import graph

    asyncio.run(__import__("job_store").create_job("77777777-7777-7777-7777-777777777777", "https://github.com/example/repo", "QA"))
    calls = {"count": 0}
    async def flaky():
        calls["count"] += 1
        if calls["count"] < 3:
            raise RuntimeError("transient")
        return "ok"

    result = asyncio.run(graph._run_step("test", flaky, {"job_id": "77777777-7777-7777-7777-777777777777"}, timeout=1))
    assert result == "ok"
    assert calls["count"] == 3


def test_graph_step_times_out():
    import asyncio
    import graph

    asyncio.run(__import__("job_store").create_job("77777777-7777-7777-7777-777777777778", "https://github.com/example/repo", "QA"))

    async def slow():
        await asyncio.sleep(0.05)
        return "late"

    with __import__("pytest").raises(TimeoutError):
        asyncio.run(graph._run_step("test-timeout", slow, {"job_id": "77777777-7777-7777-7777-777777777778"}, timeout=0.001))
