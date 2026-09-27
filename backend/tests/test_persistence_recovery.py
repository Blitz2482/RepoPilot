import asyncio
import dataclasses


def test_completed_job_can_be_restored_from_database(monkeypatch):
    import db
    import job_store

    job_id = "55555555-5555-5555-5555-555555555555"
    persisted_plan = {
        "role": "Backend",
        "repo_context": {
            "repo_url": "https://github.com/example/repo",
            "default_branch": "main",
            "languages": ["Python"],
            "file_count": 4,
        },
        "architecture_summary": {
            "overview": "Stored plan",
            "modules": ["backend"],
            "entry_points": ["main.py"],
            "data_flow": "main.py -> service",
        },
        "key_concepts": ["service"],
        "tour_steps": [
            {"step": i, "title": f"Step {i}", "path": "main.py", "start": 1, "end": 1, "narration": "Grounded step."}
            for i in range(1, 9)
        ],
    }

    monkeypatch.setattr(job_store, "settings", dataclasses.replace(job_store.settings, database_url="postgres://test"))
    monkeypatch.setattr(db, "get_repo", lambda _repo_id: {"id": job_id, "url": "https://github.com/example/repo"})
    monkeypatch.setattr(db, "get_plan", lambda _repo_id: persisted_plan)

    restored = asyncio.run(job_store.restore_job_from_db(job_id))
    assert restored is not None
    assert restored.status == "done"
    assert restored.progress == 100
    assert restored.plan == persisted_plan


def test_missing_persisted_plan_is_reported_as_interrupted(monkeypatch):
    import db
    import job_store

    job_id = "66666666-6666-6666-6666-666666666666"
    monkeypatch.setattr(job_store, "settings", dataclasses.replace(job_store.settings, database_url="postgres://test"))
    monkeypatch.setattr(db, "get_repo", lambda _repo_id: {"id": job_id, "url": "https://github.com/example/repo"})
    monkeypatch.setattr(db, "get_plan", lambda _repo_id: None)

    restored = asyncio.run(job_store.restore_job_from_db(job_id))
    assert restored is not None
    assert restored.status == "interrupted"
    assert restored.progress == 0


def test_cleanup_does_not_remove_active_job(monkeypatch, tmp_path):
    import time
    import job_store
    from job_store import JobRecord
    old_retention = job_store.settings.job_retention_hours
    job_store.settings = dataclasses.replace(job_store.settings, job_retention_hours=1)
    job_id = "88888888-8888-8888-8888-888888888888"
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "main.py").write_text("print(1)\n", encoding="utf-8")
    job_store._jobs[job_id] = JobRecord(job_id=job_id, repo_url="https://github.com/example/repo", role="QA", status="running", created_at=time.time() - 7200, repo_path=str(repo))
    try:
        asyncio.run(job_store.cleanup_stale_jobs())
        assert repo.exists()
        assert job_id in job_store._jobs
    finally:
        job_store._jobs.pop(job_id, None)
        job_store._subscribers.pop(job_id, None)
        job_store._repo_locks.pop(job_id, None)
        job_store.settings = dataclasses.replace(job_store.settings, job_retention_hours=old_retention)
