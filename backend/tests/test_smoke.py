import os
import pytest
from fastapi.testclient import TestClient

os.environ["DEV_MODE"] = "true"
os.environ["MOCK_BOB"] = "true"

from main import app

client = TestClient(app)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_submit_repo(monkeypatch):
    async def no_background(*args, **kwargs):
        return None
    monkeypatch.setattr("routes._run_background", no_background)
    response = client.post("/api/repos", json={"repo_url": "https://github.com/sindresorhus/ky", "role": "Full-Stack"})
    assert response.status_code == 202
    assert response.json()["job_id"]


def test_invalid_url():
    response = client.post("/api/repos", json={"repo_url": "https://example.com/nope", "role": "QA"})
    assert response.status_code == 400


@pytest.mark.slow
@pytest.mark.skipif(os.getenv("RUN_SLOW") != "1", reason="live GitHub clone test disabled by default")
def test_full_pipeline():
    response = client.post("/api/repos", json={"repo_url": "https://github.com/sindresorhus/ky", "role": "Full-Stack"})
    assert response.status_code == 202
    job_id = response.json()["job_id"]
    import time
    for _ in range(120):
        status = client.get(f"/api/repos/{job_id}").json()
        if status["status"] in {"done", "failed"}:
            break
        time.sleep(1)
    plan = client.get(f"/api/repos/{job_id}/plan")
    assert plan.status_code == 200
    assert len(plan.json()["tour_steps"]) == 8


def test_local_http_end_to_end(monkeypatch, tmp_path):
    from ingest import clone_repo as real_clone
    import ingest

    (tmp_path / "README.md").write_text("# Local Repo\nThis is a demo repository.\n", encoding="utf-8")
    (tmp_path / "main.py").write_text(
        "def main():\n    return retry_request()\n\ndef retry_request():\n    return True\n",
        encoding="utf-8",
    )

    async def fake_clone(repo_url: str, job_id: str) -> str:
        return str(tmp_path)

    monkeypatch.setattr(ingest, "clone_repo", fake_clone)
    response = client.post("/api/repos", json={"repo_url": "https://github.com/example/repo", "role": "Backend"})
    assert response.status_code == 202
    job_id = response.json()["job_id"]

    status = client.get(f"/api/repos/{job_id}")
    assert status.status_code == 200
    assert status.json()["status"] == "done"

    plan = client.get(f"/api/repos/{job_id}/plan")
    assert plan.status_code == 200
    data = plan.json()
    assert len(data["tour_steps"]) == 8
    assert [step["step"] for step in data["tour_steps"]] == list(range(1, 9))

    tour = client.get(f"/api/repos/{job_id}/tour")
    assert tour.status_code == 200
    assert len(tour.json()["tour_steps"]) == 8

    first = data["tour_steps"][0]
    source = client.get(
        f"/api/repos/{job_id}/source",
        params={"path": first["path"], "start": first["start"], "end": first["end"]},
    )
    assert source.status_code == 200
    assert source.json()["content"]

    answer = client.post(f"/api/repos/{job_id}/ask", json={"question": "What function should I inspect first?"})
    assert answer.status_code == 200
    assert "answer" in answer.json()
    assert "citations" in answer.json()
