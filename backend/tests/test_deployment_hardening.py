import asyncio
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from bob_client import generate_narration
from config import settings
from ingest import list_displayable_files
from main import app
from models import RepoCreateRequest


def test_role_validation():
    with pytest.raises(Exception):
        RepoCreateRequest(repo_url="https://github.com/example/repo", role="NotARole")


def test_displayable_files_includes_readme_and_code(tmp_path: Path):
    (tmp_path / "README.md").write_text("# Repo", encoding="utf-8")
    (tmp_path / "main.py").write_text("print(1)", encoding="utf-8")
    (tmp_path / "image.bin").write_bytes(b"\x00\x01")
    paths = list_displayable_files(str(tmp_path))
    assert paths == {"README.md", "main.py"}


def test_ready_dev_mode():
    client = TestClient(app)
    response = client.get("/ready")
    assert response.status_code == 200
    assert response.json()["status"] == "ready"


def test_source_path_is_restricted_to_parsed_files():
    client = TestClient(app)
    from job_store import create_job, get_job
    job_id = "44444444-4444-4444-4444-444444444444"
    asyncio.run(create_job(job_id, "https://github.com/example/repo", "QA"))
    record = get_job(job_id)
    tmp = Path(__file__).parent / "_source_fixture.py"
    try:
        tmp.write_text("secret = 1\n", encoding="utf-8")
        record.repo_path = str(tmp.parent)
        record.source_paths = {"_source_fixture.py"}
        good = client.get(f"/api/repos/{job_id}/source", params={"path":"_source_fixture.py", "start":1, "end":1})
        assert good.status_code == 200
        bad = client.get(f"/api/repos/{job_id}/source", params={"path":"../README.md", "start":1, "end":1})
        assert bad.status_code == 400
    finally:
        tmp.unlink(missing_ok=True)


def test_narration_uses_mock_without_provider(tmp_path: Path):
    (tmp_path / "main.py").write_text("def main():\n    return 1\n", encoding="utf-8")
    result = asyncio.run(generate_narration({"path":"main.py", "start":1, "end":2}))
    assert "main.py" in result


def test_bob_missing_primary_uses_configured_fallback(monkeypatch):
    import dataclasses
    import bob_client
    fallback_settings = dataclasses.replace(settings, mock_bob=False, bob_api_key=None, openai_api_key="fallback-test-key")
    monkeypatch.setattr(bob_client, "settings", fallback_settings)

    async def fake_openai(prompt: str, json_mode: bool = True):
        return '{"summary":"fallback", "evidence":[], "confidence":0.5}'

    monkeypatch.setattr(bob_client, "_call_openai", fake_openai)
    result = asyncio.run(bob_client._call_bob("test prompt"))
    assert "fallback" in result


def test_invalid_job_id_is_rejected():
    client = TestClient(app)
    response = client.get("/api/repos/not-a-uuid")
    assert response.status_code == 400


def test_production_cors_rejects_wildcard(monkeypatch):
    import dataclasses
    import config
    unsafe = dataclasses.replace(config.settings, dev_mode=False, cors_origins="*")
    with pytest.raises(RuntimeError):
        unsafe.validate_safety()


def test_production_bob_endpoint_validation():
    import dataclasses
    unsafe = dataclasses.replace(settings, dev_mode=False, bob_base_url="not-a-url", bob_endpoint="agent/run")
    with pytest.raises(RuntimeError):
        unsafe.validate_safety()


def test_github_token_requires_private_repo_switch(monkeypatch):
    import dataclasses
    import ingest

    calls = []

    class Proc:
        returncode = 0
        stderr = ""
        stdout = ""

    def fake_run(cmd, **kwargs):
        calls.append(kwargs.get("env", {}))
        return Proc()

    monkeypatch.setattr(ingest.subprocess, "run", fake_run)
    monkeypatch.setattr(ingest, "_directory_size_mb", lambda _path: 0.0)
    monkeypatch.setattr(ingest.shutil, "rmtree", lambda *_args, **_kwargs: None)

    ingest.settings = dataclasses.replace(ingest.settings, github_token="token", allow_private_repos=False)
    ingest.clone_repo_sync("https://github.com/example/repo", "55555555-5555-5555-5555-555555555555")
    assert "GIT_CONFIG_COUNT" not in calls[-1]

    ingest.settings = dataclasses.replace(ingest.settings, allow_private_repos=True)
    ingest.clone_repo_sync("https://github.com/example/repo", "66666666-6666-6666-6666-666666666666")
    assert calls[-1].get("GIT_CONFIG_COUNT") == "1"



def test_production_requires_bob_endpoint(monkeypatch):
    import dataclasses
    prod = dataclasses.replace(
        settings, dev_mode=False, database_url="postgres://db", bob_api_key="bob",
        bob_base_url="https://example.invalid", bob_endpoint="", openai_api_key="openai",
        local_embeddings=False, mock_bob=False, cors_origins="https://example.com",
    )
    assert "BOB_ENDPOINT" in prod.missing_production_config()


def test_production_bob_base_url_requires_https():
    import dataclasses
    unsafe = dataclasses.replace(settings, dev_mode=False, bob_base_url="http://example.invalid", bob_endpoint="/agent/run")
    with pytest.raises(RuntimeError):
        unsafe.validate_safety()


def test_production_ready_endpoint_passes_dependency_gate(monkeypatch):
    import dataclasses
    import main

    prod = dataclasses.replace(
        settings,
        dev_mode=False,
        database_url="postgresql://example.invalid/db",
        bob_api_key="bob-test",
        bob_base_url="https://bob.example.com",
        bob_endpoint="/agent/run",
        openai_api_key="openai-test",
        local_embeddings=False,
        mock_bob=False,
        cors_origins="https://frontend.example.com",
    )
    monkeypatch.setattr(main, "settings", prod)
    monkeypatch.setattr(main, "init_db", lambda: None)
    monkeypatch.setattr(main, "close_pool", lambda: None)
    monkeypatch.setattr("db.settings", prod)
    monkeypatch.setattr("db.check_connection", lambda: None)

    response = TestClient(main.app).get("/ready")
    assert response.status_code == 200
    assert response.json()["status"] == "ready"
    assert response.json()["missing"] == []


def test_logging_filter_handles_non_request_records():
    import logging
    from monitoring import _RequestIDFilter

    record = logging.LogRecord("repopilot.cleanup", logging.INFO, __file__, 1, "cleanup", (), None)
    assert _RequestIDFilter().filter(record) is True
    assert record.request_id == "-"


def test_metrics_separates_repo_and_request_duration(monkeypatch):
    import monitoring
    monkeypatch.setattr(monitoring, "_stats", __import__("collections").Counter({"repos_analyzed": 2, "requests": 4, "errors": 1}))
    monkeypatch.setattr(monitoring, "_total_repo_duration", 8.0)
    monkeypatch.setattr(monitoring, "_total_request_duration", 2.0)
    result = monitoring.get_metrics()
    assert result["avg_duration_seconds"] == 4.0
    assert result["avg_request_duration_seconds"] == 0.5


def test_cors_origin_normalization():
    import dataclasses
    import config
    normalized = dataclasses.replace(config.settings, cors_origins="https://frontend.example.com/").allowed_origins
    assert normalized == ["https://frontend.example.com"]
