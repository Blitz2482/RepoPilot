from ingest import validate_github_url
import pytest


def test_valid_github_url():
    assert validate_github_url("https://github.com/sindresorhus/ky") == "https://github.com/sindresorhus/ky"


def test_reject_non_github():
    with pytest.raises(ValueError):
        validate_github_url("https://example.com/org/repo")


def test_clone_timeout_uses_configured_limit(monkeypatch, tmp_path):
    import dataclasses
    import ingest
    from config import settings

    monkeypatch.setattr(ingest, "CLONE_ROOT", tmp_path)
    monkeypatch.setattr(ingest, "settings", dataclasses.replace(settings, clone_timeout_seconds=7))
    seen = {}

    def fake_run(*args, **kwargs):
        seen.update(kwargs)
        raise __import__("subprocess").TimeoutExpired(args[0], kwargs["timeout"])

    monkeypatch.setattr(ingest.subprocess, "run", fake_run)
    with pytest.raises(TimeoutError, match="7 seconds"):
        ingest.clone_repo_sync("https://github.com/example/repo", "55555555-5555-5555-5555-555555555555")
    assert seen["timeout"] == 7
