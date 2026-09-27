import asyncio
from pathlib import Path

import graph
import ingest
from job_store import create_job, get_job
from qa import answer_question


def test_offline_three_repository_qa(monkeypatch, tmp_path: Path):
    repos = {
        "python": tmp_path / "python_repo",
        "typescript": tmp_path / "ts_repo",
        "mixed": tmp_path / "mixed_repo",
    }
    (repos["python"] / "README.md").parent.mkdir(parents=True)
    (repos["python"] / "README.md").write_text("# Python repo\n", encoding="utf-8")
    (repos["python"] / "main.py").write_text(
        "def main():\n    return retry()\n\ndef retry():\n    return True\n",
        encoding="utf-8",
    )

    repos["typescript"].mkdir(parents=True)
    (repos["typescript"] / "README.md").write_text("# TypeScript repo\n", encoding="utf-8")
    (repos["typescript"] / "index.ts").write_text(
        "export function start(): boolean {\n  return true;\n}\n",
        encoding="utf-8",
    )

    repos["mixed"].mkdir(parents=True)
    (repos["mixed"] / "README.md").write_text("# Mixed repo\n", encoding="utf-8")
    (repos["mixed"] / "app.py").write_text(
        "class Service:\n    def run(self):\n        return True\n",
        encoding="utf-8",
    )
    (repos["mixed"] / "component.tsx").write_text(
        "export function Component() {\n  return null;\n}\n",
        encoding="utf-8",
    )

    async def fake_clone(repo_url: str, job_id: str) -> str:
        key = repo_url.rsplit("/", 1)[-1]
        return str(repos[key])

    monkeypatch.setattr(ingest, "clone_repo", fake_clone)

    async def run():
        questions = {"python": "retry", "typescript": "start", "mixed": "Service"}
        for i, key in enumerate(repos, 1):
            job_id = f"{i:08d}-0000-0000-0000-000000000001"
            url = f"https://github.com/example/{key}"
            await create_job(job_id, url, "Full-Stack")
            async for _ in graph.run_pipeline(job_id, url, "Full-Stack"):
                pass
            job = get_job(job_id)
            assert job is not None and job.status == "done"
            assert job.plan is not None and len(job.plan["tour_steps"]) == 8
            answer = await answer_question(job_id, questions[key], max_chars=500)
            assert answer["answer"]
            assert answer["citations"]

    asyncio.run(run())
